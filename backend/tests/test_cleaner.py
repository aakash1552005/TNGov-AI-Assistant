"""Tests for the text cleaning pipeline."""

from ingestion.cleaner import (
    clean_page,
    clean_pages,
    collapse_whitespace,
    detect_repeated_lines,
    normalize_unicode,
    remove_page_numbers,
    remove_repeated_headers_footers,
    strip_control_characters,
)


class TestNormalizeUnicode:
    """Test NFKC Unicode normalization."""

    def test_basic_latin(self) -> None:
        assert normalize_unicode("hello world") == "hello world"

    def test_nfkc_decomposed(self) -> None:
        # ﬁ (U+FB01 LATIN SMALL LIGATURE FI) → fi
        assert normalize_unicode("\ufb01") == "fi"

    def test_tamil_text_preserved(self) -> None:
        tamil = "தமிழ்நாடு அரசு"
        assert normalize_unicode(tamil) == tamil


class TestStripControlCharacters:
    """Test control character removal."""

    def test_preserves_newlines_and_tabs(self) -> None:
        assert strip_control_characters("a\nb\tc") == "a\nb\tc"

    def test_removes_null_bytes(self) -> None:
        assert strip_control_characters("a\x00b") == "ab"

    def test_removes_form_feed(self) -> None:
        assert strip_control_characters("a\x0cb") == "ab"


class TestCollapseWhitespace:
    """Test whitespace collapsing."""

    def test_multiple_spaces(self) -> None:
        assert collapse_whitespace("a   b") == "a b"

    def test_preserves_single_newlines(self) -> None:
        assert collapse_whitespace("a\nb") == "a\nb"

    def test_collapses_excessive_newlines(self) -> None:
        assert collapse_whitespace("a\n\n\n\nb") == "a\n\nb"

    def test_strips_leading_trailing(self) -> None:
        assert collapse_whitespace("  hello  ") == "hello"


class TestRemovePageNumbers:
    """Test page number removal."""

    def test_standalone_number(self) -> None:
        result = remove_page_numbers("content\n3\nmore content")
        assert "3" not in result.split("\n")

    def test_dash_number_dash(self) -> None:
        result = remove_page_numbers("content\n- 5 -\nmore")
        assert "- 5 -" not in result

    def test_page_prefix(self) -> None:
        result = remove_page_numbers("content\nPage 12\nmore")
        assert "Page 12" not in result

    def test_preserves_numbers_in_text(self) -> None:
        text = "The income limit is 72000 rupees per year."
        assert remove_page_numbers(text) == text


class TestDetectRepeatedLines:
    """Test cross-page header/footer detection."""

    def test_detects_header_in_majority_of_pages(self) -> None:
        pages = [
            "Government of Tamil Nadu\nContent of page 1.",
            "Government of Tamil Nadu\nContent of page 2.",
            "Government of Tamil Nadu\nContent of page 3.",
            "Government of Tamil Nadu\nContent of page 4.",
        ]
        repeated = detect_repeated_lines(pages)
        assert "government of tamil nadu" in repeated

    def test_skips_short_documents(self) -> None:
        # Fewer than 3 pages → no detection
        pages = ["Header\nContent 1.", "Header\nContent 2."]
        assert detect_repeated_lines(pages) == set()

    def test_preserves_unique_content(self) -> None:
        pages = [
            "Header\nUnique content A is here.",
            "Header\nUnique content B is here.",
            "Header\nUnique content C is here.",
        ]
        repeated = detect_repeated_lines(pages)
        # "unique content a is here." should NOT be in repeated
        assert not any("unique content" in line for line in repeated)

    def test_detects_footers(self) -> None:
        pages = [
            "Content page 1.\nConfidential Document",
            "Content page 2.\nConfidential Document",
            "Content page 3.\nConfidential Document",
        ]
        repeated = detect_repeated_lines(pages)
        assert "confidential document" in repeated


class TestRemoveRepeatedHeadersFooters:
    """Test removal of detected repeated lines."""

    def test_removes_matched_lines(self) -> None:
        text = "Government of TN\nActual content here.\nPage footer"
        repeated = {"government of tn", "page footer"}
        result = remove_repeated_headers_footers(text, repeated)
        assert "Government of TN" not in result
        assert "Page footer" not in result
        assert "Actual content here." in result

    def test_empty_repeated_set_is_noop(self) -> None:
        text = "Some content\nMore content"
        assert remove_repeated_headers_footers(text, set()) == text


class TestCleanPage:
    """Test the composed cleaning pipeline."""

    def test_full_pipeline(self) -> None:
        raw = "  \ufb01rst line  \n\n\n\n  second line  \n3\n"
        result = clean_page(raw)
        assert "first line" in result
        assert "second line" in result

    def test_tamil_content_preserved(self) -> None:
        tamil = "திட்டத்தின் பெயர்: முதியோர் ஓய்வூதியத் திட்டம்"
        result = clean_page(tamil)
        assert "திட்டத்தின்" in result


class TestCleanPages:
    """Test the batch cleaning with header/footer detection."""

    def test_removes_repeated_headers_across_pages(self) -> None:
        pages = [
            "Dept of Social Welfare\nScheme A details here.",
            "Dept of Social Welfare\nScheme B details here.",
            "Dept of Social Welfare\nScheme C details here.",
        ]
        cleaned = clean_pages(pages)
        for page in cleaned:
            assert "Dept of Social Welfare" not in page
            assert "details here" in page
