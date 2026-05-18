"""Data models for pre-sell advertorial pages."""

from datetime import datetime
from typing import Any, Optional
import os
from pydantic import BaseModel, Field


class PresellPage(BaseModel):
    """Generated advertorial pre-sell page."""

    offer_name: str = Field(..., description="Name of the offer")
    offer_url: str = Field(default_factory=lambda: os.environ.get("CLICKHUB_CTA_URL", "https://petalvane.com/click"), description="CTA base URL — defaultet naar env CLICKHUB_CTA_URL (ClickHub click-out). JS in template hangt ?clickid=<value> eraan bij runtime. Override via parameter alleen als je een specifieke offer een eigen URL geeft.")
    niche: str = Field(..., description="Health niche/category (e.g. 'brain-health', 'Diabetes', 'Men\'s Health')")
    headline: str = Field(..., min_length=5, max_length=150, description="Main headline")
    subheadline: str = Field(..., min_length=5, max_length=200, description="Subheadline (agitate problem)")
    body_html: str = Field(..., description="HTML-formatted body text (multiple <p> tags)")
    cta_text: str = Field(..., min_length=3, max_length=50, description="CTA button text")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    source_report_niche: str | None = Field(None, description="Niche of Module 2 report used")
    search_keywords: list[str] | None = Field(None, description="Keywords for ad scraping (auto-extracted from niche if not set)")
    compliance_violations: list[dict[str, Any]] = Field(default_factory=list, description="MGID + FTC compliance violations found")
    is_compliant: bool = Field(default=False, description="Whether page passes all compliance checks")

    class Config:
        json_schema_extra = {
            "example": {
                "offer_name": "Brain Boost Pro",
                "offer_url": "https://petalvane.com/click",  # ClickHub click-out, niet MaxWeb-link!
                "niche": "brain-health",
                "headline": "Doctor Reveals: The Secret Brain Supplement Major Pharma Doesn't Want You to Know",
                "subheadline": "One simple formula finally solves the brain fog epidemic plaguing millions",
                "body_html": "<p>For years...</p><p>Recent studies show...</p>",
                "cta_text": "Get Your Supply Today",
                "source_report_niche": "brain-health"
            }
        }
