"""
Tests for module1_offers: offer ranking logic.
"""

import tempfile
from pathlib import Path

import pytest

from src.module1_offers.importer import CSVImporter
from src.module1_offers.models import Offer, FitScore
from src.module1_offers.ranker import OfferRanker


class TestOfferRanker:
    """Test offer ranking algorithm."""

    @pytest.fixture
    def ranker(self) -> OfferRanker:
        return OfferRanker(budget_usd=1500.0)

    @pytest.fixture
    def sample_offer(self) -> Offer:
        return Offer(
            id="test-001",
            name="Test Offer",
            category="nutra",
            payout=100.0,
            epc=1.50,
            refund_rate=10.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )

    def test_score_high_payout(self, ranker: OfferRanker) -> None:
        """High payout (>$80) should score 1.0."""
        offer = Offer(
            id="high-payout",
            name="High Payout Offer",
            category="nutra",
            payout=150.0,
            epc=1.0,
            refund_rate=10.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.payout_score == 1.0

    def test_score_medium_payout(self, ranker: OfferRanker) -> None:
        """Medium payout ($50-80) should score 0.5."""
        offer = Offer(
            id="med-payout",
            name="Medium Payout Offer",
            category="nutra",
            payout=65.0,
            epc=1.0,
            refund_rate=10.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.payout_score == 0.5

    def test_score_low_payout(self, ranker: OfferRanker) -> None:
        """Low payout (<$50) should score 0.0."""
        offer = Offer(
            id="low-payout",
            name="Low Payout Offer",
            category="nutra",
            payout=30.0,
            epc=1.0,
            refund_rate=10.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.payout_score == 0.0

    def test_score_low_refund(self, ranker: OfferRanker) -> None:
        """Refund rate <15% should score 1.0."""
        offer = Offer(
            id="low-refund",
            name="Low Refund Offer",
            category="nutra",
            payout=100.0,
            epc=1.0,
            refund_rate=12.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.refund_score == 1.0

    def test_score_high_refund(self, ranker: OfferRanker) -> None:
        """Refund rate >25% should score 0.0."""
        offer = Offer(
            id="high-refund",
            name="High Refund Offer",
            category="nutra",
            payout=100.0,
            epc=1.0,
            refund_rate=30.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.refund_score == 0.0

    def test_score_sweet_spot_age(self, ranker: OfferRanker) -> None:
        """6-12mo old offers (180-365 days) should score 1.0."""
        offer = Offer(
            id="sweet-age",
            name="Sweet Age Offer",
            category="nutra",
            payout=100.0,
            epc=1.0,
            refund_rate=10.0,
            competition="medium",
            age_days=270,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.age_stability_score == 1.0

    def test_score_very_new_offer(self, ranker: OfferRanker) -> None:
        """Very new offers (<30 days) should score 0.4."""
        offer = Offer(
            id="very-new",
            name="Very New Offer",
            category="nutra",
            payout=100.0,
            epc=1.0,
            refund_rate=10.0,
            competition="medium",
            age_days=14,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.age_stability_score == 0.4

    def test_score_low_competition(self, ranker: OfferRanker) -> None:
        """Low competition should score 1.0."""
        offer = Offer(
            id="low-comp",
            name="Low Competition Offer",
            category="nutra",
            payout=100.0,
            epc=1.0,
            refund_rate=10.0,
            competition="low",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.competition_score == 1.0

    def test_score_us_geo(self, ranker: OfferRanker) -> None:
        """US geo should score 1.0."""
        offer = Offer(
            id="us-geo",
            name="US Geo Offer",
            category="nutra",
            payout=100.0,
            epc=1.0,
            refund_rate=10.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        )
        score = ranker.score_offer(offer)
        assert score.geo_match_score == 1.0

    def test_rank_multiple_offers(self, ranker: OfferRanker) -> None:
        """Multiple offers should be ranked by overall_score."""
        offers = [
            Offer(
                id="offer-1",
                name="Offer 1",
                category="nutra",
                payout=100.0,
                epc=1.0,
                refund_rate=10.0,
                competition="medium",
                age_days=180,
                geo=["US"],
            ),
            Offer(
                id="offer-2",
                name="Offer 2",
                category="nutra",
                payout=150.0,
                epc=2.0,
                refund_rate=5.0,
                competition="low",
                age_days=270,
                geo=["US"],
            ),
            Offer(
                id="offer-3",
                name="Offer 3",
                category="nutra",
                payout=50.0,
                epc=0.5,
                refund_rate=30.0,
                competition="high",
                age_days=30,
                geo=["US"],
            ),
        ]

        ranked = ranker.rank_offers(offers)

        assert len(ranked) == 3
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3
        # Offer 2 should be #1 (best score)
        assert ranked[0].offer.id == "offer-2"
        # Offer 3 should be #3 (worst score)
        assert ranked[2].offer.id == "offer-3"


class TestCSVImporter:
    """Test CSV import functionality."""

    def test_import_valid_csv(self) -> None:
        """Valid CSV should import correctly."""
        csv_content = """id,name,category,payout,epc,refund_rate,competition,age_days,geo
gluco-001,GlucoSavior,nutra,120.0,1.80,12.5,medium,210,US
cardio-002,CardioBoost,nutra,95.0,1.20,18.0,high,450,US"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            filepath = f.name

        try:
            offers = CSVImporter.import_csv(filepath)
            assert len(offers) == 2
            assert offers[0].id == "gluco-001"
            assert offers[0].payout == 120.0
            assert offers[1].id == "cardio-002"
        finally:
            Path(filepath).unlink()

    def test_import_missing_file(self) -> None:
        """Missing CSV file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CSVImporter.import_csv("/nonexistent/offers.csv")

    def test_import_missing_required_fields(self) -> None:
        """CSV missing id or name should skip row."""
        csv_content = """id,name,payout,epc
offer-1,Valid Offer,100.0,1.5
,Missing ID,100.0,1.5"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            filepath = f.name

        try:
            offers = CSVImporter.import_csv(filepath)
            # Should only import valid row
            assert len(offers) >= 1
            assert offers[0].id == "offer-1"
        finally:
            Path(filepath).unlink()

    def test_import_case_insensitive_headers(self) -> None:
        """Headers should be case-insensitive."""
        csv_content = """ID,NAME,Category,PAYOUT,EPC,Refund_Rate,Competition,Age_Days,GEO
test-001,Test Offer,nutra,100.0,1.5,10.0,medium,180,US"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            filepath = f.name

        try:
            offers = CSVImporter.import_csv(filepath)
            assert len(offers) == 1
            assert offers[0].id == "test-001"
            assert offers[0].name == "Test Offer"
        finally:
            Path(filepath).unlink()
