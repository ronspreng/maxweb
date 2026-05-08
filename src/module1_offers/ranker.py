"""
Offer ranking algorithm based on fit-score.
"""

import logging
from typing import Optional

from .models import Offer, FitScore, RankedOffer

logger = logging.getLogger(__name__)


class OfferRanker:
    """Ranks MaxWeb offers by fit-score for solo native ads operators."""

    def __init__(self, budget_usd: float = 1500.0):
        """
        Initialize ranker.

        Args:
            budget_usd: Campaign budget (used for context, not algorithm).
        """
        self.budget = budget_usd

    def score_offer(self, offer: Offer) -> FitScore:
        """
        Calculate fit-score for a single offer using weighted formula.

        Formula weights:
        - payout_score: 25% (payout is primary driver)
        - epc_score: 25% (earnings per click = conversion quality)
        - refund_score: 20% (refunds destroy margins)
        - competition_score: 15% (new/underspent > saturated)
        - age_stability_score: 10% (6-12mo old = proven winner)
        - geo_match_score: 5% (US focus)
        """

        # 1. Payout score: >$80 = 1.0, $50-80 = 0.5, <$50 = 0.0
        if offer.payout >= 80:
            payout_score = 1.0
        elif offer.payout >= 50:
            payout_score = 0.5
        else:
            payout_score = 0.0

        # 2. EPC score: >$1.50 EPC = 1.0, <$0.50 = 0.0, linear in between
        epc_score = max(0.0, min(1.0, (offer.epc - 0.5) / 1.0))

        # 3. Refund score: <15% = 1.0, 15-25% = 0.5, >25% = 0.0
        if offer.refund_rate < 15:
            refund_score = 1.0
        elif offer.refund_rate <= 25:
            refund_score = 0.5
        else:
            refund_score = 0.0

        # 4. Competition score: newer or low-spend = higher
        # Map "low" -> 1.0, "medium" -> 0.5, "high" -> 0.1
        competition_map = {"low": 1.0, "medium": 0.5, "high": 0.1}
        competition_score = competition_map.get(offer.competition, 0.5)

        # 5. Age stability: 6-12mo old = 1.0, outside = lower
        # <30 days = new = 0.5 (unproven)
        # >24mo = very old = 0.6 (possibly saturated)
        # 180-365 days = sweet spot = 1.0
        if 180 <= offer.age_days <= 365:
            age_stability_score = 1.0
        elif 30 <= offer.age_days < 180:
            age_stability_score = 0.7
        elif offer.age_days >= 365:
            age_stability_score = 0.6
        else:  # <30 days
            age_stability_score = 0.4

        # 6. Geo match: US = 1.0, other = 0.0
        geo_match_score = 1.0 if "US" in offer.geo else 0.0

        # Weighted sum
        overall_score = (
            payout_score * 0.25
            + epc_score * 0.25
            + refund_score * 0.20
            + competition_score * 0.15
            + age_stability_score * 0.10
            + geo_match_score * 0.05
        )

        # Build rationale
        rationale = self._build_rationale(
            offer,
            payout_score,
            epc_score,
            refund_score,
            competition_score,
            age_stability_score,
            geo_match_score,
        )

        return FitScore(
            offer_id=offer.id,
            payout_score=round(payout_score, 3),
            epc_score=round(epc_score, 3),
            refund_score=round(refund_score, 3),
            competition_score=round(competition_score, 3),
            age_stability_score=round(age_stability_score, 3),
            geo_match_score=round(geo_match_score, 3),
            overall_score=round(overall_score, 3),
            rationale=rationale,
        )

    def rank_offers(self, offers: list[Offer]) -> list[RankedOffer]:
        """
        Rank all offers and return sorted by fit-score (highest first).

        Args:
            offers: List of offers to rank.

        Returns:
            List of RankedOffer sorted by overall_score descending.
        """
        scored = []
        for offer in offers:
            score = self.score_offer(offer)
            scored.append(RankedOffer(rank=0, offer=offer, score=score))

        # Sort by overall_score descending
        scored.sort(key=lambda x: x.score.overall_score, reverse=True)

        # Assign ranks
        for i, item in enumerate(scored, start=1):
            item.rank = i

        logger.info(f"Ranked {len(scored)} offers")
        return scored

    def _build_rationale(
        self,
        offer: Offer,
        payout_score: float,
        epc_score: float,
        refund_score: float,
        competition_score: float,
        age_stability_score: float,
        geo_match_score: float,
    ) -> str:
        """Generate a brief rationale for the score."""
        parts = []

        if payout_score >= 0.8:
            parts.append(f"Strong payout (${offer.payout})")
        elif payout_score >= 0.5:
            parts.append(f"Moderate payout (${offer.payout})")

        if epc_score >= 0.7:
            parts.append(f"High EPC ${offer.epc}")

        if refund_score >= 0.8:
            parts.append(f"Low refund risk ({offer.refund_rate:.1f}%)")
        elif refund_score < 0.3:
            parts.append(f"High refund risk ({offer.refund_rate:.1f}%)")

        if competition_score >= 0.7:
            parts.append(f"Low competition ({offer.competition})")

        if 180 <= offer.age_days <= 365:
            parts.append("Stable offer (6-12mo old)")

        return ", ".join(parts) if parts else "Mixed signals"
