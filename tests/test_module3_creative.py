"""
Tests for module3_creative: models, generator.
"""

import pytest
from datetime import datetime

from src.module3_creative.models import NativeAdCreative, CreativeSet
from src.module3_creative.generator import CreativeGenerator


class TestNativeAdCreative:
    """Tests for NativeAdCreative Pydantic model."""

    def test_valid_creative(self) -> None:
        creative = NativeAdCreative(
            headline="Brain Fog? Read This First",
            description="Scientists reveal the surprising cause of brain fog. Simple solution inside.",
            hook_type="fear"
        )
        assert creative.headline == "Brain Fog? Read This First"
        assert len(creative.headline) <= 60
        assert len(creative.description) <= 150
        assert creative.hook_type == "fear"

    def test_headline_max_length(self) -> None:
        with pytest.raises(ValueError):
            NativeAdCreative(
                headline="X" * 61,  # Exceeds 60 char limit
                description="Valid description text here.",
                hook_type="curiosity"
            )

    def test_description_max_length(self) -> None:
        with pytest.raises(ValueError):
            NativeAdCreative(
                headline="Valid Headline",
                description="X" * 151,  # Exceeds 150 char limit
                hook_type="curiosity"
            )

    def test_headline_min_length(self) -> None:
        with pytest.raises(ValueError):
            NativeAdCreative(
                headline="X",  # Too short
                description="Valid description text here.",
                hook_type="curiosity"
            )

    def test_description_min_length(self) -> None:
        with pytest.raises(ValueError):
            NativeAdCreative(
                headline="Valid Headline",
                description="Short",  # Too short
                hook_type="curiosity"
            )

    def test_valid_hook_types(self) -> None:
        for hook_type in ["curiosity", "fear", "authority", "social_proof", "story"]:
            creative = NativeAdCreative(
                headline="Test Headline Here",
                description="Test description for hook type validation.",
                hook_type=hook_type
            )
            assert creative.hook_type == hook_type


class TestCreativeSet:
    """Tests for CreativeSet model."""

    def test_creative_set_with_multiple_creatives(self) -> None:
        creatives = [
            NativeAdCreative(
                headline=f"Headline {i}",
                description=f"Description text variant {i} with enough content.",
                hook_type=["curiosity", "fear", "authority", "social_proof", "story"][i % 5]
            )
            for i in range(8)
        ]

        creative_set = CreativeSet(
            offer_name="Brain Boost Pro",
            niche="brain-health",
            creatives=creatives,
            report_used=False
        )

        assert creative_set.offer_name == "Brain Boost Pro"
        assert creative_set.niche == "brain-health"
        assert len(creative_set.creatives) == 8
        assert creative_set.report_used is False
        assert isinstance(creative_set.generated_at, datetime)

    def test_creative_set_requires_creatives(self) -> None:
        with pytest.raises(ValueError):
            CreativeSet(
                offer_name="Brain Boost Pro",
                niche="brain-health",
                creatives=[],  # Empty list not allowed
                report_used=False
            )

    def test_creative_set_with_report_used(self) -> None:
        creative = NativeAdCreative(
            headline="Test Headline Here",
            description="Test description for report usage.",
            hook_type="curiosity"
        )

        creative_set = CreativeSet(
            offer_name="Test Product",
            niche="brain-health",
            creatives=[creative],
            report_used=True
        )

        assert creative_set.report_used is True


class TestCreativeGenerator:
    """Tests for CreativeGenerator class."""

    def test_generator_initialization(self) -> None:
        # Should initialize without errors if API key is set
        try:
            generator = CreativeGenerator()
            assert generator.client is not None
        except RuntimeError as e:
            pytest.skip(f"API key not set: {e}")

    def test_generator_requires_api_key(self, monkeypatch) -> None:
        # Test that missing API key raises RuntimeError
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
            CreativeGenerator()

    def test_build_context_without_report(self) -> None:
        try:
            generator = CreativeGenerator()
        except RuntimeError:
            pytest.skip("API key not set")

        context = generator._build_context(None, "brain-health")
        assert "No competitive patterns available" in context
        assert "general best practices" in context

    def test_build_context_with_report(self) -> None:
        try:
            generator = CreativeGenerator()
        except RuntimeError:
            pytest.skip("API key not set")

        # Try to load an actual report
        from src.module4_presell.generator import AdvertorialGenerator
        report = AdvertorialGenerator.load_report("brain-health")

        if report:
            context = generator._build_context(report, "brain-health")
            assert "Winning patterns" in context
            assert "Top hooks" in context
            assert "Power words" in context
        else:
            pytest.skip("No brain-health report found in output/reports")
