import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LayerInfo:
    """Contains metadata describing a source layer."""

    name: str
    geometry_type: str
    feature_count: int | None = None
    epsg: int | None = None


class LayerDiscovery:
    """Discovers layers and their metadata using GDAL/OGR."""

    def discover(self, source_path: str | Path) -> list[LayerInfo]:
        """Discover all layers contained in a source file.

        Args:
            source_path: Path to the source dataset.

        Returns:
            list[LayerInfo]: Discovered layers and their metadata.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the source contains no discoverable layers.
            RuntimeError: If ogrinfo fails.
        """

        source_path = Path(source_path)

        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        listing = self._run_ogrinfo(
            [
                "ogrinfo",
                "-ro",
                "-q",
                str(source_path),
            ]
        )

        layer_names = self._parse_layer_listing(listing)

        if not layer_names:
            raise ValueError(f"No layers found in source: {source_path}")

        layers = []

        for layer_name in layer_names:
            metadata = self._run_ogrinfo(
                [
                    "ogrinfo",
                    "-ro",
                    "-so",
                    "-q",
                    str(source_path),
                    layer_name,
                ]
            )

            layers.append(self._parse_layer_metadata(layer_name, metadata))

        return layers

    @staticmethod
    def _run_ogrinfo(command: list[str]) -> str:
        """Execute an ogrinfo command and return its output."""

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"ogrinfo failed: {exc.stderr or exc}") from exc

        return result.stdout

    @staticmethod
    def _parse_layer_listing(output: str) -> list[str]:
        """Extract layer names from ogrinfo datasource output."""

        layer_names = []

        for line in output.splitlines():
            match = re.match(
                r"^\s*\d+:\s*(.*?)\s+\([^()]*\)\s*$",
                line,
            )

            if match:
                layer_names.append(match.group(1).strip())

        return layer_names

    @staticmethod
    def _parse_layer_metadata(
        layer_name: str,
        output: str,
    ) -> LayerInfo:
        """Extract metadata from ogrinfo layer output."""

        geometry_match = re.search(
            r"^\s*Geometry:\s*(.+)$",
            output,
            re.MULTILINE,
        )

        count_match = re.search(
            r"^\s*Feature Count:\s*(\d+)",
            output,
            re.MULTILINE,
        )

        epsg_matches = re.findall(
            r'(?:ID|AUTHORITY)\["EPSG",\s*"?(\d+)"?\]',
            output,
        )

        return LayerInfo(
            name=layer_name,
            geometry_type=(
                geometry_match.group(1).strip() if geometry_match else "Unknown"
            ),
            feature_count=(int(count_match.group(1)) if count_match else None),
            epsg=(int(epsg_matches[-1]) if epsg_matches else None),
        )
