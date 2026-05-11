"""
Data models for Module 2: Competitive Intelligence.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class NativeAd(BaseModel):
    """A single native ad captured from a publisher site."""

    headline: str = Field(..., description="Ad headline text (what users see)")
    image_url: Optional[str] = Field(None, description="Thumbnail image URL")
    landing_url: str = Field(..., description="Destination URL (affiliate or presell)")
    source_site: str = Field(..., description="Publisher site (e.g. dailymail, msn)")
    niche: str = Field(..., description="Target niche slug (e.g. brain-health)")
    ad_network: Optional[str] = Field(
        None, description="Detected network: taboola|outbrain|revcontent|mgid|unknown"
    )
    position: Optional[int] = Field(None, description="Position on page (0-indexed)")
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    fingerprint: str = Field(..., description="SHA256 of headline+domain for dedup")

    class Config:
        json_schema_extra = {
            "example": {
                "headline": "Iowa Doctor Reveals 60-Second Morning Memory Trick",
                "image_url": "https://cdn.taboola.com/xyz.jpg",
                "landing_url": "https://go.example.com/brain-boost",
                "source_site": "dailymail",
                "niche": "brain-health",
                "ad_network": "taboola",
                "position": 3,
                "fingerprint": "a3f5c2...",
            }
        }


class CreativePattern(BaseModel):
    """A recurring pattern identified across multiple native ads."""

    pattern_type: Literal["hook", "emotional_trigger", "image_archetype", "power_word"] = Field(
        ..., description="Type of pattern"
    )
    value: str = Field(..., description="The pattern itself (e.g. 'doctor reveals')")
    frequency: int = Field(..., ge=1, description="How many ads contain this pattern")
    example_headlines: list[str] = Field(
        default_factory=list, description="Up to 3 example headlines"
    )
    niche: str = Field(..., description="Niche this pattern was found in")

    class Config:
        json_schema_extra = {
            "example": {
                "pattern_type": "hook",
                "value": "doctor reveals",
                "frequency": 12,
                "example_headlines": [
                    "Iowa Doctor Reveals 60-Second Memory Trick",
                    "Texas Doctor Reveals Lung Trick Doctors Hate",
                ],
                "niche": "brain-health",
            }
        }


class CompetitiveReport(BaseModel):
    """Full competitive intelligence report for a single niche."""

    niche: str = Field(..., description="Niche slug (brain-health, lung-health, mens-health)")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    ads_analyzed: int = Field(..., description="Total unique ads fed to analyzer")
    sources: list[str] = Field(..., description="Sites scraped")

    top_hooks: list[CreativePattern] = Field(
        default_factory=list, description="Top 5 hook patterns"
    )
    top_emotional_triggers: list[CreativePattern] = Field(
        default_factory=list, description="Top 5 emotional triggers"
    )
    top_image_archetypes: list[CreativePattern] = Field(
        default_factory=list, description="Top 5 image archetypes"
    )
    top_power_words: list[CreativePattern] = Field(
        default_factory=list, description="Top 10 high-frequency power words"
    )
    saturation_warnings: list[str] = Field(
        default_factory=list,
        description="Patterns seen 5+ times (likely saturated)",
    )
    recommended_angles: list[str] = Field(
        default_factory=list,
        description="Claude-recommended fresh angles for this niche",
    )
    raw_claude_output: str = Field(
        default="", description="Full Claude API response for debugging"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "niche": "brain-health",
                "ads_analyzed": 67,
                "sources": ["dailymail", "msn", "yahoo"],
            }
        }
