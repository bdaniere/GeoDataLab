from datetime import UTC, datetime
from pathlib import Path

from core.ingestion_runner import IngestionRunner
from core.models import DestinationConfig, IngestionResult, SourceData
from extraction.layer_discovery import LayerInfo


class FakeLayerDiscovery:
    """Simulate layer discovery."""

    def discover(self, source_path):
        return [
            LayerInfo("adresse", "Multi Point", 3832, 2154),
            LayerInfo("bati", "Multi Polygon", 7148, 2154),
            LayerInfo("activite", "None", 1394, None),
        ]


class FakeLoader:
    """Simulate a data loader."""

    def __init__(self):
        self.calls = []

    def load(self, source, destination):
        self.calls.append((source, destination))
        now = datetime.now(UTC)

        return IngestionResult(
            source_name=source.source_name,
            success=True,
            started_at=now,
            finished_at=now,
        )


def test_runner_loads_all_layers():
    source = SourceData(
        source_name="imope",
        source_type="local",
        content=Path("imope-42005.gpkg"),
        format="gpkg",
    )
    destination = DestinationConfig(
        destination_type="postgis",
        schema="raw_data",
    )
    loader = FakeLoader()
    runner = IngestionRunner(
        loader=loader,
        layer_discovery=FakeLayerDiscovery(),
    )

    result = runner.run(source, destination)

    assert result.success
    assert result.successful_layers == 3
    assert result.failed_layers == 0
    assert len(loader.calls) == 3
    assert [call[1].table for call in loader.calls] == [
        "imope_42005_adresse",
        "imope_42005_bati",
        "imope_42005_activite",
    ]
    assert [call[0].metadata["source_layer"] for call in loader.calls] == [
        "adresse",
        "bati",
        "activite",
    ]
    assert all(call[1].schema == "raw_data" for call in loader.calls)


def test_runner_continues_after_layer_failure():
    source = SourceData(
        source_name="imope",
        source_type="local",
        content=Path("imope-42005.gpkg"),
        format="gpkg",
    )
    destination = DestinationConfig(destination_type="postgis")

    class FailingLoader(FakeLoader):
        def load(self, source, destination):
            if source.metadata["source_layer"] == "bati":
                self.calls.append((source, destination))
                raise RuntimeError("Simulated loading error")

            return super().load(source, destination)

    loader = FailingLoader()
    runner = IngestionRunner(
        loader=loader,
        layer_discovery=FakeLayerDiscovery(),
    )

    result = runner.run(source, destination)

    assert not result.success
    assert result.successful_layers == 2
    assert result.failed_layers == 1
    assert len(loader.calls) == 3
    assert list(result.layer_results) == ["adresse", "bati", "activite"]

    failed_result = result.layer_results["bati"]
    assert not failed_result.success
    assert failed_result.error == "Simulated loading error"
    assert failed_result.metadata == {
        "source_layer": "bati",
        "destination_schema": "raw_data",
        "destination_table": "imope_42005_bati",
    }
