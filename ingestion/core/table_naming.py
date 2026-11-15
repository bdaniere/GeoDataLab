import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path

MAX_POSTGRES_IDENTIFIER_LENGTH = 63
MAX_LAYER_NAME_LENGTH = 30


def normalize_identifier(value: str) -> str:
    """Normalize a string into a valid PostgreSQL identifier.

    Args:
        value: Original identifier.

    Returns:
        str: Normalized PostgreSQL identifier.

    Raises:
        ValueError: If the input is not a valid string.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Identifier must be a non-empty string.")

    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")

    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")

    if not normalized:
        normalized = "source"

    if normalized[0].isdigit():
        normalized = f"_{normalized}"

    return normalized[:MAX_POSTGRES_IDENTIFIER_LENGTH].rstrip("_")


def generate_table_names(
    source_path: str | Path,
    layer_names: Sequence[str],
) -> dict[str, str]:
    """Generate PostgreSQL table names for the layers of a source file."""

    if not layer_names:
        raise ValueError("At least one source layer is required.")

    if len(set(layer_names)) != len(layer_names):
        raise ValueError("Duplicate source layer names detected.")

    source_prefix = normalize_identifier(Path(source_path).stem)

    generated_names = {}

    for layer_name in layer_names:
        normalized_layer = normalize_identifier(layer_name)

        # Truncate the layer name independently.
        normalized_layer = normalized_layer[:MAX_LAYER_NAME_LENGTH].rstrip("_")

        if len(layer_names) == 1:
            candidate = source_prefix
        else:
            candidate = normalize_identifier(f"{source_prefix}_{normalized_layer}")

        if candidate in generated_names.values():
            previous_layer = next(
                name for name, table in generated_names.items() if table == candidate
            )

            raise ValueError(
                f"Table name collision: layers '{previous_layer}' "
                f"and '{layer_name}' both generate '{candidate}'."
            )

        generated_names[layer_name] = candidate

    return generated_names
