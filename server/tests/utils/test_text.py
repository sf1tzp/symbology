from symbology.utils.text import normalize_filing_text


class TestNormalizeFilingText:
    def test_collapses_excessive_blank_lines(self):
        text = "Section A\n\n\n\n\nSection B"
        assert normalize_filing_text(text) == "Section A\n\nSection B"

    def test_preserves_single_blank_line(self):
        text = "Paragraph 1\n\nParagraph 2"
        assert normalize_filing_text(text) == "Paragraph 1\n\nParagraph 2"

    def test_collapses_inline_whitespace(self):
        text = "word1   word2\tword3\t\tword4"
        assert normalize_filing_text(text) == "word1 word2 word3 word4"

    def test_strips_trailing_whitespace_per_line(self):
        text = "line1   \nline2\t\nline3"
        assert normalize_filing_text(text) == "line1\nline2\nline3"

    def test_decodes_html_entities(self):
        text = "AT&amp;T &nbsp; price &gt; $10 &#8220;quoted&#8221;"
        result = normalize_filing_text(text)
        assert "AT&T" in result
        assert "&amp;" not in result
        assert "&nbsp;" not in result
        assert "&gt;" not in result
        assert "\u201c" not in result  # no smart quotes left

    def test_normalizes_smart_quotes(self):
        text = "\u201cHello\u201d and \u2018world\u2019"
        assert normalize_filing_text(text) == '"Hello" and \'world\''

    def test_normalizes_dashes(self):
        text = "en\u2013dash and em\u2014dash"
        assert normalize_filing_text(text) == "en-dash and em-dash"

    def test_normalizes_ellipsis(self):
        text = "wait\u2026 more"
        assert normalize_filing_text(text) == "wait... more"

    def test_normalizes_non_breaking_space(self):
        text = "word1\u00a0word2"
        assert normalize_filing_text(text) == "word1 word2"

    def test_mixed_issues(self):
        text = (
            "  AT&amp;T \u201cresults\u201d  \n"
            "   \n"
            "\n"
            "\n"
            "Revenue\u2014$100M\u2026  \n"
            "  trailing  "
        )
        result = normalize_filing_text(text)
        assert "AT&T" in result
        assert '"results"' in result
        assert "Revenue-$100M..." in result
        # Excessive blank lines collapsed
        assert "\n\n\n" not in result
        # No trailing whitespace
        for line in result.split("\n"):
            assert line == line.rstrip()

    def test_empty_string(self):
        assert normalize_filing_text("") == ""

    def test_none_returns_none(self):
        assert normalize_filing_text(None) is None

    def test_whitespace_only(self):
        assert normalize_filing_text("   \n\n  \t  ") == ""

    def test_already_clean_text(self):
        text = "This is clean text.\n\nNew paragraph here."
        assert normalize_filing_text(text) == text
