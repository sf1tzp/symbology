"""Tests for the declarative pipeline config loader (DB-free).

Exercises the real prompts/model_configs.yaml + prompt files, plus the
flat-vs-legacy resolution in load_prompt_content using a tmp directory.
"""
import pytest

from symbology.database.generated_content import ContentStage
from symbology.worker.config_loader import load_pipeline_config
from symbology.worker.pipeline import load_prompt_content

EXPECTED_STAGES = {
    "change_report",
    "change_report_intro",
    "company_main_content",
    "company_intro",
    "group_main_content",
    "group_intro",
    "filing_main_content",
    "filing_intro",
    "document_page_intro",
}
VALID_STAGES = {s.value for s in ContentStage}


def test_loads_and_validates_real_config():
    cfg = load_pipeline_config()
    # Every prompt-mapped stage is present and a valid ContentStage.
    # prompts map ContentStage -> prompt path, so their keys must be valid stages.
    assert EXPECTED_STAGES.issubset(set(cfg.prompts))
    for stage in cfg.prompts:
        assert stage in VALID_STAGES
    # model_configs keys are free-form profile names (not ContentStage); each
    # must carry the minimal option vocabulary.
    for profile, opts in cfg.model_configs.items():
        assert {"model", "max_tokens", "temperature"} <= set(opts), profile


def test_every_prompt_path_resolves_to_a_file():
    cfg = load_pipeline_config()
    for stage, path in cfg.prompts.items():
        content = load_prompt_content(path, cfg.prompts_dir)
        assert content, f"empty prompt for stage {stage} at {path}"
    for doc_type, path in cfg.doc_type_prompts.items():
        content = load_prompt_content(path, cfg.prompts_dir)
        assert content, f"empty L1 prompt for {doc_type} at {path}"


def test_model_config_options_are_minimal_vocabulary():
    cfg = load_pipeline_config()
    opts = cfg.model_config_options("change_report")
    assert set(opts) == {"model", "max_tokens", "temperature"}
    assert opts["model"].startswith("claude")
    assert isinstance(opts["max_tokens"], int)


def test_form_document_types_present():
    cfg = load_pipeline_config()
    assert "10-K" in cfg.form_document_types
    assert "business_description" in cfg.form_document_types["10-K"]
    # Item 7A market-risk disclosures are in scope for 10-Ks too (present in the
    # filings; needed so a 10-Q page's anchor 10-K has a market_risk summary).
    assert "market_risk" in cfg.form_document_types["10-K"]


def test_main_content_source_per_form():
    cfg = load_pipeline_config()
    # A 10-K leads with its business description; a 10-Q (no business
    # description) leads with the MD&A. Unknown forms fall back to the former.
    assert cfg.main_content_source("10-K") == "business_description"
    assert cfg.main_content_source("10-Q") == "management_discussion"
    assert cfg.main_content_source("8-K") == "business_description"


def test_form_prompts_override_selection():
    cfg = load_pipeline_config()
    # A 10-Q selects its quarterly variant for the company-page stages; a 10-K (and
    # an unknown form) keeps the form-agnostic default.
    for stage in (
        "change_report",
        "change_report_intro",
        "company_main_content",
        "company_intro",
    ):
        assert cfg.prompt_path(stage, "10-Q") == cfg.form_prompts["10-Q"][stage]
        assert cfg.prompt_path(stage, "10-Q").endswith("-quarterly")
        assert cfg.prompt_path(stage, "10-K") == cfg.prompts[stage]
        # No form (or an unknown form) also falls back to the default.
        assert cfg.prompt_path(stage) == cfg.prompts[stage]
        assert cfg.prompt_path(stage, "8-K") == cfg.prompts[stage]


def test_form_prompt_overrides_resolve_to_files():
    cfg = load_pipeline_config()
    for form, stage_paths in cfg.form_prompts.items():
        for stage, path in stage_paths.items():
            assert stage in VALID_STAGES, f"{form}: bad stage {stage}"
            content = load_prompt_content(path, cfg.prompts_dir)
            assert content, f"empty {form} override for {stage} at {path}"


def test_load_prompt_content_prefers_flat(tmp_path):
    (tmp_path / "l2").mkdir()
    (tmp_path / "l2" / "change-report.md").write_text("FLAT CONTENT")
    assert load_prompt_content("l2/change-report", tmp_path) == "FLAT CONTENT"


def test_load_prompt_content_falls_back_to_legacy(tmp_path):
    legacy = tmp_path / "risk_factors"
    legacy.mkdir()
    (legacy / "prompt.md").write_text("LEGACY CONTENT")
    (legacy / "examples").mkdir()
    (legacy / "examples" / "a.md").write_text("EXAMPLE A")
    out = load_prompt_content("risk_factors", tmp_path)
    assert "LEGACY CONTENT" in out and "EXAMPLE A" in out


def test_load_prompt_content_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_prompt_content("nope/missing", tmp_path)
