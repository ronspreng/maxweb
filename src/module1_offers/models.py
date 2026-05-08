"""
Data models for MaxWeb offers and scoring.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Offer(BaseModel):
    """A MaxWeb affiliate offer."""

    id: str
    name: str
    category: str
    payout: float = Field(..., description="Commission per sale in USD")
    epc: float = Field(
        ..., description="Earnings Per Click (calculated or provided)"
    )
    refund_rate: float = Field(
        ..., description="Refund rate as percentage (0-100)"
    )
    competition: str = Field(
        default="medium", description="low|medium|high - relative competition"
    )
    age_days: int = Field(
        default=180, description="Days the offer has been active"
    )
    geo: list[str] = Field(
        default=["US"], description="Geographic markets (e.g. ['US', 'US-TX'])"
    )
    network: str = Field(default="maxweb", description="Affiliate network")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "gluco-savior-001",
                "name": "GlucoSavior Blood Sugar Support",
                "category": "nutra_health",
                "payout": 120.0,
                "epc": 1.80,
                "refund_rate": 12.5,
                "competition": "medium",
                "age_days": 210,
                "geo": ["US"],
                "network": "maxweb",
            }
        }


class FitScore(BaseModel):
    """Scoring breakdown for an offer."""

    offer_id: str
    payout_score: float = Field(..., ge=0.0, le=1.0)
    epc_score: float = Field(..., ge=0.0, le=1.0)
    refund_score: float = Field(..., ge=0.0, le=1.0)
    competition_score: float = Field(..., ge=0.0, le=1.0)
    age_stability_score: float = Field(..., ge=0.0, le=1.0)
    geo_match_score: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., description="Why this offer scores this way")

    class Config:
        json_schema_extra = {
            "example": {
                "offer_id": "gluco-savior-001",
                "payout_score": 1.0,
                "epc_score": 0.9,
                "refund_score": 1.0,
                "competition_score": 0.7,
                "age_stability_score": 0.8,
                "geo_match_score": 1.0,
                "overall_score": 0.89,
                "rationale": "Strong payout + EPC, low refund risk, stable offer",
            }
        }


class RankedOffer(BaseModel):
    """An offer with its calculated fit score."""

    rank: int
    offer: Offer
    score: FitScore
