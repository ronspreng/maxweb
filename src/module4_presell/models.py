"""Data models for pre-sell advertorial pages."""

from datetime import datetime
from pydantic import BaseModel, Field


class PresellPage(BaseModel):
    """Generated advertorial pre-sell page."""

    offer_name: str = Field(..., description="Name of the offer")
    offer_url: str = Field(..., description="CTA URL (MaxWeb affiliate link)")
    niche: str = Field(..., description="Niche (brain-health, lung-health, mens-health)")
    headline: str = Field(..., min_length=5, max_length=150, description="Main headline")
    subheadline: str = Field(..., min_length=5, max_length=200, description="Subheadline (agitate problem)")
    body_html: str = Field(..., description="HTML-formatted body text (multiple <p> tags)")
    cta_text: str = Field(..., min_length=3, max_length=50, description="CTA button text")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    source_report_niche: str | None = Field(None, description="Niche of Module 2 report used")

    class Config:
        json_schema_extra = {
            "example": {
                "offer_name": "Brain Boost Pro",
                "offer_url": "https://maxweb.com/offer/brain-boost",
                "niche": "brain-health",
                "headline": "Doctor Reveals: The Secret Brain Supplement Major Pharma Doesn't Want You to Know",
                "subheadline": "One simple formula finally solves the brain fog epidemic plaguing millions",
                "body_html": "<p>For years...</p><p>Recent studies show...</p>",
                "cta_text": "Get Your Supply Today",
                "source_report_niche": "brain-health"
            }
        }
