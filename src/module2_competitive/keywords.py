"""Keyword extraction utilities for niches/categories."""

import re


def extract_keywords(niche: str) -> list[str]:
    """
    Extract search keywords from a niche/category string.

    Examples:
        "Brain Health/Memory" → ["brain", "health", "memory"]
        "Men's Health" → ["men", "health"]
        "Joint Supplement" → ["joint", "supplement"]

    Args:
        niche: Niche or category string (e.g. from MaxWeb)

    Returns:
        List of lowercase keywords
    """
    # Remove special characters and split
    cleaned = re.sub(r'[/\-\']', ' ', niche.lower())
    # Split on whitespace
    words = cleaned.split()
    # Filter short words (< 3 chars) except specific ones
    keywords = [
        w for w in words
        if len(w) >= 3 or w in ['men', 'gut', 'cbd']
    ]
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for k in keywords:
        if k not in seen:
            result.append(k)
            seen.add(k)
    return result
