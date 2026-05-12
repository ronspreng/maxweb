"""Data models for campaign metrics and analytics."""
from datetime import datetime
from pydantic import BaseModel, Field


class SubIdMetrics(BaseModel):
    """Metrics for a single Sub-ID (campaign variant)."""
    sub_id: str
    network: str  # mgid, taboola, etc
    geo: str      # US-TX, US-CA, etc
    device: str   # desktop, mobile, tablet
    daypart: str  # morning, afternoon, evening, night
    ad_id: str    # h047, h048, etc
    landing_id: str  # lp01, lp02, etc
    
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    spend: float = 0.0
    
    @property
    def ctr(self) -> float:
        """Click-through rate."""
        return (self.conversions / self.clicks * 100) if self.clicks > 0 else 0.0
    
    @property
    def cpa(self) -> float:
        """Cost per acquisition."""
        return (self.spend / self.conversions) if self.conversions > 0 else 0.0
    
    @property
    def roi(self) -> float:
        """Return on investment (%)."""
        return ((self.revenue - self.spend) / self.spend * 100) if self.spend > 0 else 0.0
    
    @property
    def epc(self) -> float:
        """Earnings per click."""
        return (self.revenue / self.clicks) if self.clicks > 0 else 0.0


class CampaignAnalysis(BaseModel):
    """Analysis of a complete campaign."""
    offer_name: str
    offer_id: str
    date_range: str  # "2026-05-01 to 2026-05-11"
    total_clicks: int = 0
    total_conversions: int = 0
    total_revenue: float = 0.0
    total_spend: float = 0.0
    
    sub_ids: list[SubIdMetrics] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def overall_roi(self) -> float:
        """Overall campaign ROI (%)."""
        if self.total_spend == 0:
            return 0.0
        return ((self.total_revenue - self.total_spend) / self.total_spend * 100)
    
    @property
    def overall_cpa(self) -> float:
        """Overall CPA."""
        return (self.total_spend / self.total_conversions) if self.total_conversions > 0 else 0.0
    
    @property
    def overall_conversion_rate(self) -> float:
        """Overall conversion rate (%)."""
        return (self.total_conversions / self.total_clicks * 100) if self.total_clicks > 0 else 0.0


class CampaignRecommendation(BaseModel):
    """Recommendation for campaign optimization."""
    sub_id: str
    action: str  # "scale", "kill", "optimize", "maintain"
    reason: str
    metric: str  # "ROI", "CPA", "CTR"
    current_value: float
    target_value: float = None
