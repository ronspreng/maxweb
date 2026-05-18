"""Data models for native ad creatives."""
from datetime import datetime
from pydantic import BaseModel, Field


class NativeAdCreative(BaseModel):
    """Single native ad creative (headline + description + image prompt)."""
    headline: str = Field(..., max_length=60, description="Max 60 chars (MGID/Taboola)")
    description: str = Field(..., max_length=150, description="Max 150 chars")
    hook_type: str = Field(..., description="curiosity|fear|authority|social_proof|story")
    image_prompt: str = Field(..., description="Detailed AI image generation prompt (600x500px, DALL-E/Midjourney compatible)")
    image_url: str | None = Field(default=None, description="URL of generated image (DALL-E CDN, 24h validity) or local path after batch-gen")


class CreativeSet(BaseModel):
    """Set of 8-10 creative variations for an offer."""
    offer_name: str
    niche: str
    creatives: list[NativeAdCreative]
    generated_at: datetime = Field(default_factory=datetime.now)
    report_used: bool = Field(default=False, description="Was Module 2 report used?")
