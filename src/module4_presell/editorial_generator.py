"""Generate editorial health articles using Claude API."""

import json
import logging
import os
import re
from datetime import datetime

from anthropic import Anthropic

from .models import PresellPage

logger = logging.getLogger(__name__)


class EditorialGenerator:
    """Generate editorial health articles from keywords using Claude."""

    def __init__(self, api_key: str = None):
        """Initialize with Anthropic API key."""
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = Anthropic(api_key=api_key)

    def generate(self, keywords: list[str], niche: str) -> PresellPage:
        """
        Generate an editorial article from keywords.

        Args:
            keywords: List of keywords (e.g. ["brain fog", "memory loss", "aging"])
            niche: Health niche/category (e.g. "Brain Health/Memory", "Diabetes", "Men's Health")

        Returns:
            PresellPage object with generated article
        """
        keywords_str = ", ".join(keywords)
        logger.info(f"[editorial] Generating article: keywords={keywords_str}, niche={niche}")

        system_prompt = """You are an expert health editorial writer. Create informative, well-researched health articles that educate readers without making medical claims. Your articles should be authoritative, cite evidence-based information, and help readers understand health topics deeply. Do NOT write advertorial content or sales pitches—write pure editorial/educational content.

Output ONLY valid JSON, no markdown fences or extra text."""

        user_prompt = f"""Generate a health editorial article on these keywords: {keywords_str}

Niche: {niche}
Target length: 600-800 words
Format: HTML with <h1>, <h2>, <h3>, <ul>, <ol>, <p>, <blockquote> tags

Output JSON with these fields:
{{
  "title": "Compelling article headline",
  "subheadline": "Engaging subheadline that adds context",
  "body_html": "<h1>Title</h1><p>Intro...</p><h2>Section</h2><p>Content...</p>..."
}}

Requirements:
- Title: 60-80 characters, catchy but informative
- Subheadline: 100-150 characters, supporting the title
- Body: Rich HTML with multiple sections (h2/h3), bullet points, paragraphs
- Educational tone, no sales pitch
- Evidence-based claims with expert authority
- Natural flow and high readability"""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            content = response.content[0].text.strip()

            # Strip markdown code fences if present
            content = re.sub(r"^```json\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

            article_data = json.loads(content)
            logger.info(f"[editorial] Generated: {article_data['title']}")

            # Remove h1 tag from body_html since headline is displayed separately by site builder
            body_html = article_data["body_html"]
            body_html = re.sub(r'<h1[^>]*>.*?</h1>', '', body_html, count=1, flags=re.IGNORECASE | re.DOTALL)
            # Also remove any intro paragraph that might be duplicated
            body_html = re.sub(r'^\s*<p><em>.*?</em></p>\s*', '', body_html, flags=re.IGNORECASE)
            body_html = body_html.lstrip()

            # Create PresellPage object (offer_url="" since no affiliate link for editorial)
            page = PresellPage(
                offer_name=article_data["title"],
                offer_url="",
                niche=niche,
                headline=article_data["title"],
                subheadline=article_data["subheadline"],
                body_html=body_html,
                cta_text="Continue Reading",
                source_report_niche=None,
            )

            return page

        except json.JSONDecodeError as e:
            logger.error(f"[editorial] JSON parse error: {e}")
            raise ValueError(f"Claude response was not valid JSON: {content[:200]}")
        except Exception as e:
            logger.error(f"[editorial] Generation error: {e}")
            raise
