"""
Tests for module2_competitive: models, dedup, analyzer, reporter.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.module2_competitive.deduplicator import AdDeduplicator
from src.module2_competitive.models import (
    CompetitiveReport,
    CreativePattern,
    NativeAd,
)
from src.module2_competitive.reporter import IntelReporter


def make_ad(
    headline: str = "Test Headline",
    source: str = "dailymail",
    niche: str = "brain-health",
    fingerprint: str | None = None,
) -> NativeAd:
    """Factory for test NativeAd instances."""
    fp = fingerprint or headline[:8].replace(" ", "")
    return NativeAd(
        headline=headline,
        landing_url="https://example.com",
        source_site=source,
        niche=niche,
        fingerprint=fp,
    )


class TestNativeAdModel:
    """Tests for NativeAd Pydantic model."""

    def test_required_fields(self) -> None:
        ad = make_ad()
        assert ad.headline == "Test Headline"
        assert ad.source_site == "dailymail"
        assert ad.niche == "brain-health"

    def test_fingerprint_assigned(self) -> None:
        ad = make_ad(fingerprint="abc123")
        assert ad.fingerprint == "abc123"

    def test_captured_at_defaults_to_now(self) -> None:
        ad = make_ad()
        assert isinstance(ad.captured_at, datetime)

    def test_optional_fields(self) -> None:
        ad = make_ad()
        assert ad.image_url is None
        assert ad.ad_network is None
        assert ad.position is None


class TestCreativePatternModel:
    """Tests for CreativePattern Pydantic model."""

    def test_pattern_creation(self) -> None:
        pattern = CreativePattern(
            pattern_type="hook",
            value="doctor reveals",
            frequency=10,
            niche="brain-health",
        )
        assert pattern.value == "doctor reveals"
        assert pattern.frequency == 10
        assert pattern.pattern_type == "hook"

    def test_pattern_with_examples(self) -> None:
        pattern = CreativePattern(
            pattern_type="hook",
            value="doctor reveals",
            frequency=10,
            example_headlines=["Dr. Smith Reveals", "Doctor Uncovers"],
            niche="brain-health",
        )
        assert len(pattern.example_headlines) == 2


class TestAdDeduplicator:
    """Tests for AdDeduplicator class."""

    def test_deduplicates_by_fingerprint(self) -> None:
        ads = [
            make_ad("Ad A", fingerprint="fp1"),
            make_ad("Ad B", fingerprint="fp2"),
            make_ad("Ad A duplicate", fingerprint="fp1"),
        ]
        dedup = AdDeduplicator()
        result = dedup.deduplicate(ads)
        assert len(result) == 2
        assert result[0].fingerprint == "fp1"
        assert result[1].fingerprint == "fp2"

    def test_empty_input(self) -> None:
        dedup = AdDeduplicator()
        result = dedup.deduplicate([])
        assert result == []

    def test_cache_persistence(self) -> None:
        ads = [make_ad("Ad A", fingerprint="fp1")]
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            dedup = AdDeduplicator(cache_path=cache_path)
            dedup.deduplicate(ads)
            dedup.save_cache(ads)
            assert cache_path.exists()

            dedup2 = AdDeduplicator(cache_path=cache_path)
            result = dedup2.deduplicate(ads)
            assert len(result) == 0

    def test_incremental_dedup(self) -> None:
        ads1 = [make_ad("Ad A", fingerprint="fp1")]
        ads2 = [make_ad("Ad B", fingerprint="fp2"), make_ad("Ad A", fingerprint="fp1")]

        dedup = AdDeduplicator()
        result1 = dedup.deduplicate(ads1)
        assert len(result1) == 1

        result2 = dedup.deduplicate(ads2)
        assert len(result2) == 1
        assert result2[0].fingerprint == "fp2"


class TestIntelReporter:
    """Tests for IntelReporter class."""

    @pytest.fixture
    def sample_report(self) -> CompetitiveReport:
        return CompetitiveReport(
            niche="brain-health",
            ads_analyzed=50,
            sources=["dailymail", "msn"],
            top_hooks=[
                CreativePattern(
                    pattern_type="hook",
                    value="doctor reveals",
                    frequency=12,
                    example_headlines=["Iowa Doctor Reveals Memory Trick"],
                    niche="brain-health",
                )
            ],
            top_emotional_triggers=[],
            top_image_archetypes=[],
            top_power_words=[],
            recommended_angles=["angle 1", "angle 2"],
        )

    def test_markdown_contains_niche(self, sample_report: CompetitiveReport) -> None:
        md = IntelReporter.to_markdown(sample_report)
        assert "brain-health" in md

    def test_markdown_contains_hooks(self, sample_report: CompetitiveReport) -> None:
        md = IntelReporter.to_markdown(sample_report)
        assert "doctor reveals" in md

    def test_markdown_contains_ad_count(self, sample_report: CompetitiveReport) -> None:
        md = IntelReporter.to_markdown(sample_report)
        assert "50" in md

    def test_markdown_contains_recommended_angles(self, sample_report: CompetitiveReport) -> None:
        md = IntelReporter.to_markdown(sample_report)
        assert "angle 1" in md
        assert "angle 2" in md

    def test_save_creates_file(self, sample_report: CompetitiveReport) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = IntelReporter.save(sample_report, Path(tmp))
            assert path.exists()
            content = path.read_text()
            assert "brain-health" in content
            assert "doctor reveals" in content


class TestPatternAnalyzerParsing:
    """Test Claude response parsing without hitting the API."""

    def test_parse_valid_claude_response(self) -> None:
        from src.module2_competitive.analyzer import PatternAnalyzer

        mock_json = json.dumps(
            {
                "top_hooks": [
                    {
                        "value": "doctor reveals",
                        "frequency": 10,
                        "example_headlines": ["Iowa Doctor Reveals Trick"],
                    }
                ],
                "top_emotional_triggers": [
                    {"value": "fear of decline", "frequency": 8, "example_headlines": []}
                ],
                "top_image_archetypes": [
                    {"value": "doctor stock photo", "frequency": 6, "example_headlines": []}
                ],
                "top_power_words": [
                    {"value": "reveals", "frequency": 15, "example_headlines": []}
                    for _ in range(10)
                ],
                "saturation_warnings": ["doctor reveals used 10+ times"],
                "recommended_angles": ["Fresh angle for brain-health"],
            }
        )

        analyzer = PatternAnalyzer.__new__(PatternAnalyzer)
        ads = [make_ad()]
        report = analyzer._parse_response(mock_json, ads, "brain-health", ads)

        assert report.niche == "brain-health"
        assert len(report.top_hooks) == 1
        assert report.top_hooks[0].value == "doctor reveals"
        assert len(report.saturation_warnings) == 1

    def test_parse_invalid_json_returns_empty_report(self) -> None:
        from src.module2_competitive.analyzer import PatternAnalyzer

        analyzer = PatternAnalyzer.__new__(PatternAnalyzer)
        ads = [make_ad()]
        report = analyzer._parse_response("not json {{}", ads, "brain-health", ads)

        assert report.niche == "brain-health"
        assert report.top_hooks == []
        assert "not json" in report.raw_claude_output

    def test_parse_missing_optional_fields(self) -> None:
        from src.module2_competitive.analyzer import PatternAnalyzer

        mock_json = json.dumps(
            {
                "top_hooks": [
                    {
                        "value": "hook1",
                        "frequency": 5,
                        "example_headlines": [],
                    }
                ],
                "top_emotional_triggers": [],
                "top_image_archetypes": [],
                "top_power_words": [],
                "saturation_warnings": [],
                "recommended_angles": [],
            }
        )

        analyzer = PatternAnalyzer.__new__(PatternAnalyzer)
        ads = [make_ad()]
        report = analyzer._parse_response(mock_json, ads, "brain-health", ads)

        assert report.niche == "brain-health"
        assert len(report.top_hooks) == 1
        assert report.saturation_warnings == []
        assert report.recommended_angles == []


class TestCompetitiveReportModel:
    """Tests for CompetitiveReport Pydantic model."""

    def test_report_creation(self) -> None:
        report = CompetitiveReport(
            niche="brain-health",
            ads_analyzed=100,
            sources=["dailymail", "msn"],
        )
        assert report.niche == "brain-health"
        assert report.ads_analyzed == 100
        assert len(report.sources) == 2

    def test_report_defaults(self) -> None:
        report = CompetitiveReport(
            niche="brain-health",
            ads_analyzed=50,
            sources=["dailymail"],
        )
        assert isinstance(report.generated_at, datetime)
        assert report.top_hooks == []
        assert report.saturation_warnings == []
        assert report.recommended_angles == []
