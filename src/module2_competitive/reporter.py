"""
Report generator for competitive intelligence results (Markdown + JSON).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from .models import CompetitiveReport

logger = logging.getLogger(__name__)


class IntelReporter:
    """Renders a CompetitiveReport to Markdown."""

    @staticmethod
    def to_markdown(report: CompetitiveReport) -> str:
        """Generate Markdown content from CompetitiveReport."""
        def clean_text(text: str) -> str:
            """Remove all problematic Unicode characters, keep only ASCII + basic UTF-8."""
            if not text:
                return text
            # Replace common fancy characters
            replacements = {
                "—": " - ",
                "–": "-",
                "…": "...",
                """: '"',
                """: '"',
                "'": "'",
                "'": "'",
                "•": "-",
                "→": "->",
                "←": "<-",
                "↑": "up",
                "↓": "down",
            }
            for fancy, ascii_eq in replacements.items():
                text = text.replace(fancy, ascii_eq)
            # Remove any remaining non-ASCII characters
            text = text.encode("ascii", "ignore").decode("ascii")
            return text.strip()

        date_str = report.generated_at.strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"# Competitive Intelligence Report — {report.niche}",
            f"\n**Generated:** {date_str}",
            f"**Ads Analyzed:** {report.ads_analyzed}",
            f"**Sources:** {', '.join(report.sources)}\n",
            "---\n",
            "## Top 5 Hook Patterns\n",
        ]

        for i, p in enumerate(report.top_hooks[:5], 1):
            lines.append(f"### {i}. \"{clean_text(p.value)}\" (seen ~{p.frequency}x)")
            for ex in p.example_headlines[:2]:
                lines.append(f'> "{clean_text(ex)}"')
            lines.append("")

        lines.append("## Top 5 Emotional Triggers\n")
        for i, p in enumerate(report.top_emotional_triggers[:5], 1):
            lines.append(f"{i}. **{clean_text(p.value)}** - ~{p.frequency}x")
        lines.append("")

        lines.append("## Top 5 Image Archetypes\n")
        for i, p in enumerate(report.top_image_archetypes[:5], 1):
            lines.append(f"{i}. **{clean_text(p.value)}** - ~{p.frequency}x")
        lines.append("")

        lines.append("## Top 10 Power Words\n")
        words = [f"`{p.value}`" for p in report.top_power_words[:10]]
        lines.append(", ".join(words))
        lines.append("")

        if report.saturation_warnings:
            lines.append("## Saturation Warnings (Avoid or Subvert)\n")
            for w in report.saturation_warnings:
                lines.append(f"- {clean_text(w)}")
            lines.append("")

        if report.recommended_angles:
            lines.append("## Recommended Fresh Angles\n")
            for i, angle in enumerate(report.recommended_angles, 1):
                lines.append(f"{i}. {clean_text(angle)}")
            lines.append("")

        # Final cleanup: remove any remaining problematic characters
        result = "\n".join(lines)
        result = result.encode("ascii", "ignore").decode("ascii")
        return result

    @staticmethod
    def to_json(report: CompetitiveReport) -> str:
        """Generate JSON content from CompetitiveReport."""
        data = {
            "niche": report.niche,
            "generated_at": report.generated_at.isoformat(),
            "ads_analyzed": report.ads_analyzed,
            "sources": report.sources,
            "top_hooks": [
                {
                    "value": p.value,
                    "frequency": p.frequency,
                    "example_headlines": p.example_headlines,
                }
                for p in report.top_hooks
            ],
            "top_emotional_triggers": [
                {
                    "value": p.value,
                    "frequency": p.frequency,
                }
                for p in report.top_emotional_triggers
            ],
            "top_image_archetypes": [
                {
                    "value": p.value,
                    "frequency": p.frequency,
                }
                for p in report.top_image_archetypes
            ],
            "top_power_words": [
                {
                    "value": p.value,
                    "frequency": p.frequency,
                }
                for p in report.top_power_words
            ],
            "saturation_warnings": report.saturation_warnings,
            "recommended_angles": report.recommended_angles,
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def save(report: CompetitiveReport, output_dir: Path) -> Path:
        """Save CompetitiveReport to both Markdown and JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Save Markdown
        md_filename = f"competitive_intel_{date_str}_{report.niche}.md"
        md_path = output_dir / md_filename
        md_content = IntelReporter.to_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"Markdown report saved to {md_path}")

        # Save JSON
        json_filename = f"competitive_intel_{date_str}_{report.niche}.json"
        json_path = output_dir / json_filename
        json_content = IntelReporter.to_json(report)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        logger.info(f"JSON report saved to {json_path}")

        return md_path
