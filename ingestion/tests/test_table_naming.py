import pytest
from core.table_naming import (
    generate_table_names,
    normalize_identifier,
)


def test_generate_names_for_multiple_layers():
    result = generate_table_names(
        "imope-42005.gpkg",
        ["adresse", "bati", "activite"],
    )

    assert result == {
        "adresse": "imope_42005_adresse",
        "bati": "imope_42005_bati",
        "activite": "imope_42005_activite",
    }


def test_generate_name_for_single_layer():
    result = generate_table_names(
        "communes.gpkg",
        ["communes"],
    )

    assert result == {
        "communes": "communes",
    }


def test_normalize_identifier():
    assert normalize_identifier("IMOPÉ-42005") == "imope_42005"
    assert normalize_identifier("My Source (2026)") == "my_source_2026"
    assert normalize_identifier("123_data") == "_123_data"


def test_generated_names_respect_postgres_limit():
    result = generate_table_names(
        "a" * 60 + ".gpkg",
        ["adresse", "bati"],
    )

    assert all(len(name.encode("utf-8")) <= 63 for name in result.values())


def test_collision_after_normalization():
    with pytest.raises(ValueError, match="collision"):
        generate_table_names(
            "source.gpkg",
            ["my-layer", "my_layer"],
        )


def test_collision_after_layer_truncation():
    prefix = "a" * 30

    with pytest.raises(ValueError, match="collision"):
        generate_table_names(
            "source.gpkg",
            [prefix + "_first", prefix + "_second"],
        )


def test_empty_layer_list():
    with pytest.raises(ValueError, match="At least one"):
        generate_table_names("source.gpkg", [])


def test_duplicate_layer_names():
    with pytest.raises(ValueError, match="Duplicate"):
        generate_table_names(
            "source.gpkg",
            ["adresse", "adresse"],
        )


def test_layer_name_is_truncated():
    result = generate_table_names(
        "source.gpkg",
        ["a" * 40, "b" * 40],
    )

    assert result == {
        "a" * 40: "source_" + "a" * 30,
        "b" * 40: "source_" + "b" * 30,
    }
