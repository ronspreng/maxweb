"""
Import offers from CSV and other sources.
"""

import csv
import logging
from pathlib import Path
from typing import Optional

from .models import Offer

logger = logging.getLogger(__name__)


class CSVImporter:
    """Import offers from MaxWeb CSV export."""

    @staticmethod
    def import_csv(filepath: str | Path) -> list[Offer]:
        """
        Import offers from CSV file.

        Expected columns (case-insensitive):
        - id / offer_id
        - name / offer_name
        - category
        - payout / commission
        - epc / earnings_per_click
        - refund_rate / refund
        - competition (low|medium|high)
        - age_days / days_active
        - geo (comma-separated, e.g. "US,US-TX")
        - network (default: maxweb)

        Args:
            filepath: Path to CSV file.

        Returns:
            List of Offer objects.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        offers = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("CSV file is empty")

                # Normalize field names to lowercase
                fieldnames = {fn.lower(): fn for fn in reader.fieldnames}

                for row_idx, row in enumerate(reader, start=2):
                    # Normalize row keys
                    normalized_row = {k.lower(): v for k, v in row.items()}

                    try:
                        offer = CSVImporter._parse_row(normalized_row)
                        offers.append(offer)
                    except ValueError as e:
                        logger.warning(
                            f"Skipped row {row_idx}: {e}"
                        )

            logger.info(f"Imported {len(offers)} offers from {filepath}")
            return offers

        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {e}")

    @staticmethod
    def _parse_row(row: dict[str, str]) -> Offer:
        """
        Parse a single CSV row into an Offer object.

        Args:
            row: Normalized dictionary (lowercase keys).

        Returns:
            Offer object.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        # Extract required fields (with fallbacks for column name variants)
        # MaxWeb uses account_id, also check for id / offer_id
        offer_id = row.get("account_id") or row.get("id") or row.get("offer_id")
        name = row.get("name") or row.get("offer_name")

        if not offer_id or not name:
            raise ValueError("Missing required fields: id and/or name")

        # Parse payout (MaxWeb: avg_payout, fallback: payout, commission)
        payout_str = row.get("avg_payout") or row.get("payout") or row.get("commission")
        try:
            payout = float(payout_str) if payout_str else 0.0
        except ValueError:
            raise ValueError(f"Invalid payout value: {payout_str}")

        # Parse EPC (MaxWeb: epc_alltime, fallback: epc, earnings_per_click)
        epc_str = row.get("epc_alltime") or row.get("epc") or row.get("earnings_per_click")
        try:
            epc = float(epc_str) if epc_str else 0.0
        except ValueError:
            raise ValueError(f"Invalid EPC value: {epc_str}")

        # Parse refund rate (MaxWeb: refundrate_alltime, fallback: refund_rate, refund)
        refund_str = row.get("refundrate_alltime") or row.get("refund_rate") or row.get("refund")
        try:
            refund_rate = float(refund_str) if refund_str else 0.0
        except ValueError:
            raise ValueError(f"Invalid refund rate: {refund_str}")

        # Competition (default: medium)
        competition = (
            row.get("competition", "medium").lower().strip()
        )
        if competition not in ["low", "medium", "high"]:
            competition = "medium"

        # Age in days (default: 180)
        age_str = row.get("age_days") or row.get("days_active")
        try:
            age_days = int(age_str) if age_str else 180
        except ValueError:
            age_days = 180

        # Geo (default: US)
        geo_str = row.get("geo", "US").strip()
        geo = [g.strip() for g in geo_str.split(",") if g.strip()]
        if not geo:
            geo = ["US"]

        # Network (default: maxweb)
        network = row.get("network", "maxweb").strip()

        # Category (optional, default: general)
        category = row.get("category", "general").strip()

        return Offer(
            id=offer_id.strip(),
            name=name.strip(),
            category=category,
            payout=payout,
            epc=epc,
            refund_rate=refund_rate,
            competition=competition,
            age_days=age_days,
            geo=geo,
            network=network,
        )
