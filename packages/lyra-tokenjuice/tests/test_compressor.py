"""Tests for token compressor."""

import pytest

from lyra_tokenjuice import TokenCompressor


def test_token_counting():
    """Test token counting."""
    compressor = TokenCompressor()

    text = "Hello, world!"
    tokens = compressor.count_tokens(text)

    assert tokens > 0
    assert isinstance(tokens, int)


def test_basic_compression():
    """Test basic text compression."""
    compressor = TokenCompressor()

    text = "This is a test.    This is a test.    This is a test."
    result = compressor.compress(text)

    assert result.compressed_tokens < result.original_tokens
    assert result.compression_ratio > 0
    assert result.information_loss < 1.0


def test_html_to_markdown():
    """Test HTML to Markdown conversion."""
    compressor = TokenCompressor()

    html = """
    <html>
        <body>
            <h1>Title</h1>
            <p>This is a paragraph.</p>
            <script>alert('test');</script>
        </body>
    </html>
    """

    result = compressor.compress(html)

    assert "<html>" not in result.compressed_text
    assert "<script>" not in result.compressed_text
    assert "Title" in result.compressed_text
    assert "paragraph" in result.compressed_text
    assert "html_to_markdown" in result.rules_applied


def test_url_shortening():
    """Test URL shortening."""
    compressor = TokenCompressor()

    text = "Check out https://example.com/very/long/path/to/resource?param1=value1&param2=value2&param3=value3"
    result = compressor.compress(text)

    assert len(result.compressed_text) < len(text)
    assert "example.com" in result.compressed_text


def test_whitespace_normalization():
    """Test whitespace normalization."""
    compressor = TokenCompressor()

    text = "Hello    world\n\n\n\nMultiple    spaces"
    result = compressor.compress(text)

    assert "    " not in result.compressed_text
    assert "\n\n\n\n" not in result.compressed_text


def test_deduplication():
    """Test line deduplication."""
    compressor = TokenCompressor()

    text = "Line 1\nLine 1\nLine 2\nLine 2\nLine 2"
    result = compressor.compress(text)

    # Should have fewer lines
    assert result.compressed_text.count("\n") < text.count("\n")


def test_aggressive_compression():
    """Test aggressive compression mode."""
    compressor = TokenCompressor()

    text = "The application configuration information is stored in the database repository."
    result = compressor.compress(text, aggressive=True)

    # Should apply abbreviations
    assert "app" in result.compressed_text or "config" in result.compressed_text
    assert "abbreviations" in result.rules_applied


def test_compression_ratio_target():
    """Test that compression achieves good ratio."""
    compressor = TokenCompressor()

    # Large repetitive text
    text = "Error: Connection failed\n" * 100
    result = compressor.compress(text)

    # Should achieve significant compression
    assert result.compression_ratio > 0.5  # At least 50% reduction


def test_information_loss_limit():
    """Test that information loss is acceptable."""
    compressor = TokenCompressor()

    text = "Important security finding: CVE-2021-44228 affects Apache Log4j"
    result = compressor.compress(text)

    # Should preserve key information
    assert "CVE-2021-44228" in result.compressed_text
    assert "Log4j" in result.compressed_text
    assert result.information_loss < 0.2  # Less than 20% loss
