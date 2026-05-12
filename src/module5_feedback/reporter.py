"""Generate campaign analysis reports."""

from datetime import datetime
from .models import CampaignAnalysis, CampaignRecommendation


class CampaignReporter:
    """Generate human-readable campaign reports."""

    @staticmethod
    def generate_markdown(
        analysis: CampaignAnalysis,
        recommendations: list[CampaignRecommendation],
    ) -> str:
        """Generate markdown report."""
        report = f"""# Campaign Analysis: {analysis.offer_name}

**Period:** {analysis.date_range}
**Generated:** {analysis.analyzed_at.strftime('%Y-%m-%d %H:%M UTC')}

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Clicks | {analysis.total_clicks:,} |
| Conversions | {analysis.total_conversions:,} |
| Revenue | ${analysis.total_revenue:,.2f} |
| Spend | ${analysis.total_spend:,.2f} |
| **Overall ROI** | **{analysis.overall_roi:.1f}%** |
| **CPA** | **${analysis.overall_cpa:.2f}** |
| **Conversion Rate** | **{analysis.overall_conversion_rate:.2f}%** |

## Best Performers

"""
        # Top 3 by ROI
        top_roi = sorted(analysis.sub_ids, key=lambda x: x.roi, reverse=True)[:3]
        for i, sub_id in enumerate(top_roi, 1):
            report += f"{i}. **{sub_id.sub_id}** - ROI: {sub_id.roi:.1f}% | Clicks: {sub_id.clicks} | Conv: {sub_id.conversions}\n"

        report += f"\n## Recommendations\n\n"

        if recommendations:
            by_action = {}
            for rec in recommendations:
                if rec.action not in by_action:
                    by_action[rec.action] = []
                by_action[rec.action].append(rec)

            for action in ["scale", "optimize", "kill", "maintain"]:
                if action in by_action:
                    report += f"### 🎯 {action.upper()}\n\n"
                    for rec in by_action[action]:
                        report += f"- **{rec.sub_id}**: {rec.reason}\n"
                    report += "\n"
        else:
            report += "No actionable recommendations at this time. Need more data.\n"

        report += f"\n## All Sub-IDs\n\n"
        report += "| Sub-ID | Clicks | Conv | Revenue | Spend | ROI | CPA | EPC |\n"
        report += "|--------|--------|------|---------|-------|-----|-----|-----|\n"

        for sub_id in sorted(analysis.sub_ids, key=lambda x: x.roi, reverse=True):
            report += f"| {sub_id.sub_id} | {sub_id.clicks} | {sub_id.conversions} | ${sub_id.revenue:.2f} | ${sub_id.spend:.2f} | {sub_id.roi:.1f}% | ${sub_id.cpa:.2f} | ${sub_id.epc:.2f} |\n"

        return report

    @staticmethod
    def generate_summary(analysis: CampaignAnalysis) -> str:
        """Generate brief summary."""
        status = "✅ PROFITABLE" if analysis.overall_roi > 0 else "❌ LOSING MONEY"
        return f"""
**{analysis.offer_name}** - {status}

ROI: {analysis.overall_roi:.1f}% | Revenue: ${analysis.total_revenue:,.2f} | Spend: ${analysis.total_spend:,.2f} | CPA: ${analysis.overall_cpa:.2f}

Next: Check recommendations for which variants to scale or kill.
        """
