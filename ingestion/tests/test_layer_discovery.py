import subprocess

from extraction import layer_discovery
from extraction.layer_discovery import LayerDiscovery


def test_parse_layer_listing():
    output = """
    1: adresse (Multi Point)
    2: bati (Multi Polygon)
    3: activite (None)
    """

    result = LayerDiscovery._parse_layer_listing(output)

    assert result == ["adresse", "bati", "activite"]


def test_parse_layer_metadata():
    output = """
    Layer name: adresse
    Geometry: Multi Point
    Feature Count: 3832
    ID["EPSG",2154]
    """

    result = LayerDiscovery._parse_layer_metadata(
        "adresse",
        output,
    )

    assert result.name == "adresse"
    assert result.geometry_type == "Multi Point"
    assert result.feature_count == 3832
    assert result.epsg == 2154


def test_parse_attribute_only_layer():
    output = """
    Layer name: activite
    Geometry: None
    Feature Count: 1394
    """

    result = LayerDiscovery._parse_layer_metadata(
        "activite",
        output,
    )

    assert result.name == "activite"
    assert result.geometry_type == "None"
    assert result.feature_count == 1394
    assert result.epsg is None


def test_discover_multiple_layers(geopackage, monkeypatch):
    listing = """
    1: adresse (Multi Point)
    2: activite (None)
    """

    adresse_metadata = """
    Layer name: adresse
    Geometry: Multi Point
    Feature Count: 3832
    ID["EPSG",2154]
    """

    activite_metadata = """
    Layer name: activite
    Geometry: None
    Feature Count: 1394
    """

    outputs = iter([listing, adresse_metadata, activite_metadata])

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout=next(outputs),
            stderr="",
        )

    monkeypatch.setattr(layer_discovery.subprocess, "run", fake_run)

    result = LayerDiscovery().discover(geopackage)

    assert len(result) == 2
    assert result[0].name == "adresse"
    assert result[0].epsg == 2154
    assert result[1].name == "activite"
    assert result[1].geometry_type == "None"
