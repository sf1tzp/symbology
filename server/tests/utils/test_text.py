from symbology.utils.text import normalize_filing_text, validate_section_content


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


class TestValidateSectionContent:
    """Tests for the section content quality validator."""

    def test_accepts_substantive_prose(self):
        text = "The company operates in multiple segments. " * 100
        valid, reason = validate_section_content(text)
        assert valid is True
        assert reason == ""

    def test_rejects_empty(self):
        valid, reason = validate_section_content("")
        assert valid is False
        assert reason == "empty"

    def test_rejects_none(self):
        valid, reason = validate_section_content(None)
        assert valid is False
        assert reason == "empty"

    def test_rejects_whitespace_only(self):
        valid, reason = validate_section_content("   \n\n  ")
        assert valid is False
        assert reason == "empty"

    def test_rejects_too_short(self):
        valid, reason = validate_section_content("A short section.")
        assert valid is False
        assert "too_short" in reason

    def test_rejects_toc_with_page_references(self):
        """Reproduce the Intel TOC pattern."""
        toc = (
            "Item Number       Item\n"
            "Part I\n"
            "Item 1.           Business:\n"
            "                  General development of business       Pages 3-5, 18\n"
            "                  Description of business               Pages 3-24, 33, 52, 72-75\n"
            "                  Available information                  Page 2\n"
            "Item 1A.          Risk Factors                          Pages 37-51\n"
            "Item 1B.          Unresolved Staff Comments             None\n"
            "Item 1C.          Cybersecurity                         Page 54\n"
            "Item 2.           Properties                            Pages 11, 32\n"
            "Item 3.           Legal Proceedings                     Pages 102-105\n"
            "Item 4.           Mine Safety Disclosures               None\n"
            "Part II\n"
            "Item 5.           Market                                Page 55\n"
            "Item 6.           Reserved                              None\n"
            "Item 7.           MD&A                                  Pages 56-71\n"
            "Item 7A.          Market Risk                           Pages 72-75\n"
            "Item 8.           Financial Statements                  Pages 76-101\n"
        )
        # Pad to exceed minimum length so we test the density check, not length
        toc_padded = toc + ("\n" + " " * 80) * 20
        valid, reason = validate_section_content(toc_padded)
        assert valid is False
        assert "page_ref_density" in reason

    def test_accepts_prose_with_occasional_page_ref(self):
        """Real prose may mention a page once or twice - that's fine."""
        # One page ref per ~1200 chars of prose -> well under the density threshold
        filler = "The company reported strong revenue growth in fiscal year 2025. " * 20
        prose = filler + "See Page 45 for details. " + filler
        valid, reason = validate_section_content(prose)
        assert valid is True

    def test_rejects_short_toc(self):
        """A short TOC gets rejected (by length or density - either is fine)."""
        short_toc = (
            "Item 1. Business  Page 3\n"
            "Item 2. Properties  Page 10\n"
        )
        valid, _ = validate_section_content(short_toc)
        assert valid is False
