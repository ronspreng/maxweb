"""Data models for native ad creative variations."""

from datetime import datetime
from pydantic import BaseModel, Field


class NativeAdCreative(BaseModel):
    """Single native ad creative (headline + description)."""

    headline: str = Field(..., min_length=5, max_length=60, description="Headline for native ad (MGID/Taboola limit: 60 chars)")
    description: str = Field(..., min_length=10, max_length=150, description="Description text (platform limit: 150 chars)")
    hook_type: str = Field(..., description="Hook category: curiosity, fear, authority, social_proof, story")

    class Config:
        json_schema_extra = {
            "example": {
                "headline": "This One Trick Doctors Don't Want You to Know",
                "description": "A simple morning routine that's transforming brain health. See the results inside.",
                "hook_type": "curiosity"
            }
        }


class CreativeSet(BaseModel):
    """Set of multiple creative variations for A/B testing."""

    offer_name: str = Field(..., description="Name of the offer")
    niche: str = Field(..., description="Target niche")
    creatives: list[NativeAdCreative] = Field(..., min_items=1, description="List of generated creatives (typically 8)")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_used: bool = Field(False, description="Whether Module 2 competitive report was used")

    class Config:
        json_schema_extra = {
            "example": {
                "offer_name": "Brain Boost Pro",
                "niche": "brain-health",
                "creatives": [
                    {
                        "headline": "This One Trick Doctors Don't Want You to Know",
                        "description": "A simple morning routine that's transforming brain health.",
                        "hook_type": "curiosity"
                    },
                    {
                        "headline": "Brain Fog? Read This Before It's Too Late",
                        "description": "Scientists discovered the real cause of brain fog. Shocking results.",
                        "hook_type": "fear"
                    }
                ],
                "report_used": True
            }
        }
