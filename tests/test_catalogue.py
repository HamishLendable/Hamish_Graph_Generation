"""Tests for motor_graphs.catalogue — JSON shape + search behaviour."""

from motor_graphs import recipes, styles
from motor_graphs.catalogue import build_catalogue, search


def test_catalogue_lists_all_25_styles():
    cat = build_catalogue()
    assert cat["n_styles"] == 25
    catalogue_names = {e["name"] for e in cat["styles"]}
    assert catalogue_names == set(styles.__all__)


def test_catalogue_lists_all_8_recipes():
    cat = build_catalogue()
    assert cat["n_recipes"] == 8
    catalogue_names = {e["name"] for e in cat["recipes"]}
    assert catalogue_names == set(recipes.__all__)


def test_every_style_has_required_fields():
    cat = build_catalogue()
    required = {"name", "kind", "module", "summary", "use_when", "data_shape", "parameters"}
    for entry in cat["styles"]:
        assert required.issubset(entry.keys()), f"{entry['name']} missing fields"
        assert entry["kind"] == "style"
        assert entry["summary"], f"{entry['name']} has no summary"
        assert entry["use_when"], f"{entry['name']} missing Use this when:"
        assert entry["data_shape"], f"{entry['name']} missing Data shape:"


def test_every_recipe_has_snowflake_tables():
    cat = build_catalogue()
    for entry in cat["recipes"]:
        assert entry["kind"] == "recipe"
        assert entry["summary"], f"{entry['name']} has no summary"
        assert entry["use_when"], f"{entry['name']} missing Use this when:"
        assert entry["snowflake_tables_used"], (
            f"{entry['name']} missing Snowflake tables used:"
        )


def test_parameters_extracted_per_style():
    cat = build_catalogue()
    # Every style takes `df` as the first positional arg.
    for entry in cat["styles"]:
        params = entry["parameters"]
        assert params, f"{entry['name']} has no parameters"
        assert params[0]["name"] == "df", f"{entry['name']} first param is not df"


def test_search_finds_swap_matrix():
    hits = search("swap")
    names = [h["name"] for h in hits]
    assert "heatmap_swap" in names


def test_search_finds_recipe_by_keyword():
    hits = search("introducer")
    # introducer_volume_league_table and introducer_volume_mix_monthly recipes
    # mention "introducer" in their docstrings.
    names = {h["name"] for h in hits}
    assert "introducer_volume_league_table" in names
    assert "introducer_volume_mix_monthly" in names


def test_search_returns_empty_for_no_match():
    assert search("zzz_does_not_exist") == []


def test_search_case_insensitive():
    assert search("SWAP") == search("swap") == search("Swap")
