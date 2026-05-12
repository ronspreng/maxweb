"""Analyze campaign metrics and generate recommendations."""

import logging
from .models import CampaignAnalysis, CampaignRecommendation, SubIdMetrics

logger = logging.getLogger(__name__)


class CampaignAnalyzer:
    """Analyze campaigns and generate optimization recommendations."""

    def __init__(self, roi_target: float = 20.0, cpa_threshold: float = None):
        """
        Initialize analyzer.

        Args:
            roi_target: Target ROI % for scaling (default 20%)
            cpa_threshold: Max acceptable CPA (if None, calculate from average)
        """
        self.roi_target = roi_target
        self.cpa_threshold = cpa_threshold

    def analyze(self, campaign: CampaignAnalysis) -> list[CampaignRecommendation]:
        """Generate recommendations for each Sub-ID."""
        recommendations = []

        if not campaign or not campaign.sub_ids:
            return recommendations

        # Calculate benchmarks
        avg_roi = sum(sid.roi for sid in campaign.sub_ids) / len(campaign.sub_ids) if campaign.sub_ids else 0
        avg_cpa = campaign.overall_cpa if campaign.overall_cpa > 0 else None

        for sub_id in campaign.sub_ids:
            rec = self._recommend_action(sub_id, avg_roi, avg_cpa)
            if rec:
                recommendations.append(rec)

        logger.info(f"[analyzer] Generated {len(recommendations)} recommendations")
        return recommendations

    def _recommend_action(
        self,
        sub_id: SubIdMetrics,
        avg_roi: float,
        avg_cpa: float = None,
    ) -> CampaignRecommendation:
        """Generate recommendation for single Sub-ID."""

        # Need minimum data to make decisions
        if sub_id.clicks < 50:
            return None

        # KILL: ROI < -50% after 200+ clicks = losing money
        if sub_id.clicks >= 200 and sub_id.roi < -50:
            return CampaignRecommendation(
                sub_id=sub_id.sub_id,
                action="kill",
                reason="Severe negative ROI despite significant traffic",
                metric="ROI",
                current_value=sub_id.roi,
                target_value=0.0
            )

        # SCALE: ROI > 20% and above average = winner
        if sub_id.roi > self.roi_target and sub_id.roi > avg_roi:
            return CampaignRecommendation(
                sub_id=sub_id.sub_id,
                action="scale",
                reason=f"Strong ROI ({sub_id.roi:.1f}%) - increase budget 2-3x",
                metric="ROI",
                current_value=sub_id.roi,
                target_value=self.roi_target
            )

        # OPTIMIZE: ROI 0-20% = promising but needs work
        if 0 < sub_id.roi < self.roi_target:
            return CampaignRecommendation(
                sub_id=sub_id.sub_id,
                action="optimize",
                reason="Positive ROI but below target - test headlines or landing pages",
                metric="ROI",
                current_value=sub_id.roi,
                target_value=self.roi_target
            )

        # MAINTAIN: ROI near average and stable
        if abs(sub_id.roi - avg_roi) < 5:
            return CampaignRecommendation(
                sub_id=sub_id.sub_id,
                action="maintain",
                reason="Stable performance - monitor for changes",
                metric="ROI",
                current_value=sub_id.roi,
                target_value=avg_roi
            )

        return None
