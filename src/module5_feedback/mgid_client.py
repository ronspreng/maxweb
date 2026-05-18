"""MGID REST API client.

Wrapper rond MGID's REST API voor:
- Campagne-stats per dag
- Per-click breakdown met sourceId (widget) en teaserId
- Teaser block/unblock (voor auto-blacklist in latere stappen)

Auth via MGID_API_KEY in .env. Client-ID via MGID_CLIENT_ID (auto-discovery
indien niet gezet — duurt 1 extra API-call).

Docs: https://help.mgid.com/api-advertisers
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)


BASE_URL = "https://api.mgid.com/v1"


@dataclass
class CampaignStat:
    """Daily campaign statistics (uit /campaigns-stat endpoint)."""

    campaign_id: str
    name: Optional[str] = None
    imps: int = 0
    clicks: int = 0
    spent: float = 0.0
    avcpc: float = 0.0
    conversions: int = 0
    revenue: float = 0.0
    profit: float = 0.0
    epc: float = 0.0
    roas: float = 0.0

    @property
    def roi(self) -> float:
        """ROI als percentage. ROI = (revenue - spent) / spent × 100."""
        if self.spent <= 0:
            return 0.0
        return ((self.revenue - self.spent) / self.spent) * 100


@dataclass
class ClickRow:
    """Eén click in de byClicksDetailed-output."""

    time: str
    ip: str
    referer: str
    teaser_id: str
    source_id: str
    source: str
    informer_uid: str
    country: str
    region: str
    price: float


@dataclass
class WidgetStat:
    """Aggregated stats voor één widget (source_id) binnen een campagne."""

    source_id: str
    source: str = ""  # human-readable name
    clicks: int = 0
    spend: float = 0.0
    teasers_used: set = field(default_factory=set)

    @property
    def avg_cpc(self) -> float:
        return self.spend / self.clicks if self.clicks > 0 else 0.0


@dataclass
class TeaserStat:
    """Aggregated stats voor één teaser binnen een campagne."""

    teaser_id: str
    clicks: int = 0
    spend: float = 0.0
    widgets_seen: set = field(default_factory=set)

    @property
    def avg_cpc(self) -> float:
        return self.spend / self.clicks if self.clicks > 0 else 0.0


class MGIDClient:
    """Wrapper rond MGID REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        timeout: int = 30,
    ):
        key = (api_key or os.environ.get("MGID_API_KEY", "")).strip()
        if not key:
            raise RuntimeError(
                "MGID_API_KEY niet gezet. Voeg toe aan .env. "
                "Vraag aan je MGID account-manager indien geen key."
            )
        self._api_key = key
        self._client_id = (client_id or os.environ.get("MGID_CLIENT_ID", "")).strip() or None
        self.timeout = timeout

    @property
    def client_id(self) -> str:
        """Lazy client-ID discovery — uit env of via API."""
        if not self._client_id:
            self._client_id = self._discover_client_id()
        return self._client_id

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def _get(self, path: str, params: dict | None = None, retries: int = 2) -> dict:
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, headers=self._headers(), params=params or {}, timeout=self.timeout)
                if r.status_code == 429:
                    # Rate-limited — exponential backoff
                    wait = 2 ** attempt
                    logger.warning(f"MGID 429, retry in {wait}s")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as exc:
                if attempt < retries:
                    logger.warning(f"MGID GET {url} attempt {attempt+1} failed: {exc}")
                    time.sleep(1.5)
                else:
                    raise RuntimeError(f"MGID API GET {path} failed: {exc}") from exc
        return {}

    def _discover_client_id(self) -> str:
        """Probeer client-ID via een lichte API-call te ontdekken.

        MGID heeft geen formele 'whoami' endpoint, maar campaigns-stat zonder
        clientId in path geeft soms een hint. Beter: zet MGID_CLIENT_ID in .env.
        """
        raise RuntimeError(
            "MGID_CLIENT_ID niet gezet en kan niet auto-detect. "
            "Zet 'm in .env. Te vinden in MGID dashboard URL "
            "(bijv. /clients/12345 → clientId=12345)."
        )

    # ===== Campaign stats =====

    def get_campaigns_stats(self, date_interval: str = "yesterday") -> list[CampaignStat]:
        """Daily-level stats voor alle campagnes.

        Args:
            date_interval: een van: today, yesterday, thisWeek, lastWeek,
                thisMonth, lastMonth, lastSeven, last30Days, all.

        Returns:
            Lijst met CampaignStat (één per campagne).
        """
        path = f"/goodhits/clients/{self.client_id}/campaigns-stat"
        data = self._get(path, params={"dateInterval": date_interval})
        if not isinstance(data, dict):
            logger.warning(f"Unexpected campaigns-stat response: {type(data)}")
            return []

        stats = []
        for cid, row in data.items():
            if not isinstance(row, dict):
                continue
            stats.append(CampaignStat(
                campaign_id=str(cid),
                imps=int(row.get("imps", 0) or 0),
                clicks=int(row.get("clicks", 0) or 0),
                spent=float(row.get("spent", 0) or 0),
                avcpc=float(row.get("avcpc", 0) or 0),
                conversions=int(row.get("buy", 0) or 0),
                revenue=float(row.get("revenue", 0) or 0),
                profit=float(row.get("profit", 0) or 0),
                epc=float(row.get("epc", 0) or 0),
            ))
        logger.info(f"[mgid] {len(stats)} campagne-stats opgehaald ({date_interval})")
        return stats

    # ===== Per-click detail (= widget + teaser breakdown) =====

    def get_campaign_clicks_detail(self, campaign_id: str, date: str) -> list[ClickRow]:
        """Per-click data voor één campagne op één dag.

        Returns lijst van ClickRow objects met sourceId (widget) en teaserId.

        Args:
            campaign_id: MGID campaign-ID
            date: YYYY-MM-DD
        """
        path = f"/goodhits/campaigns/{campaign_id}/statistics"
        data = self._get(path, params={"type": "byClicksDetailed", "date": date})
        stats = data.get("statistics", {}) if isinstance(data, dict) else {}
        accepted = stats.get("acceptedClicks", []) or []
        clicks = []
        for row in accepted:
            if not isinstance(row, dict):
                continue
            clicks.append(ClickRow(
                time=row.get("time", ""),
                ip=row.get("ip", ""),
                referer=row.get("referer", ""),
                teaser_id=str(row.get("teaserId", "")),
                source_id=str(row.get("sourceId", "")),
                source=row.get("source", ""),
                informer_uid=row.get("informerUid", ""),
                country=row.get("country", ""),
                region=row.get("region", ""),
                price=float(row.get("price", 0) or 0),
            ))
        logger.info(f"[mgid] {len(clicks)} clicks geladen voor campaign {campaign_id} op {date}")
        return clicks

    def aggregate_widgets(self, clicks: list[ClickRow]) -> dict[str, WidgetStat]:
        """Aggregeer ClickRows naar WidgetStat per source_id."""
        widgets: dict[str, WidgetStat] = {}
        for c in clicks:
            if c.source_id not in widgets:
                widgets[c.source_id] = WidgetStat(source_id=c.source_id, source=c.source)
            w = widgets[c.source_id]
            w.clicks += 1
            w.spend += c.price
            if c.teaser_id:
                w.teasers_used.add(c.teaser_id)
        return widgets

    def aggregate_teasers(self, clicks: list[ClickRow]) -> dict[str, TeaserStat]:
        """Aggregeer ClickRows naar TeaserStat per teaser_id."""
        teasers: dict[str, TeaserStat] = {}
        for c in clicks:
            if not c.teaser_id:
                continue
            if c.teaser_id not in teasers:
                teasers[c.teaser_id] = TeaserStat(teaser_id=c.teaser_id)
            t = teasers[c.teaser_id]
            t.clicks += 1
            t.spend += c.price
            if c.source_id:
                t.widgets_seen.add(c.source_id)
        return teasers
