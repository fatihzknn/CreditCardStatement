"""Tests for merchant normalization."""

from app.services.merchant import normalize_merchant


def test_amazon_variants():
    """Amazon variants normalize to Amazon."""
    for raw in ["AMZN EU S.a.r.L.", "Amazon Marketplace", "Amazon.de"]:
        name, conf = normalize_merchant(raw)
        assert "Amazon" in name or name == "Amazon"
        assert conf >= 0.8


def test_netflix():
    """Netflix normalizes."""
    name, conf = normalize_merchant("NETFLIX.COM")
    assert "Netflix" in name
    assert conf >= 0.8


def test_unknown_merchant():
    """Unknown merchant gets cleaned fallback."""
    name, conf = normalize_merchant("RANDOM SHOP 12345")
    assert name
    assert 0 < conf < 1
