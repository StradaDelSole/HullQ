"""Repository-local JSON Schema contract loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

__all__ = ["ContractRegistry"]


class ContractRegistry:
    """Load and validate repository-local Draft 2020-12 JSON Schema contracts.

    Instantiate via :meth:`from_directory`. The registry holds all schemas found
    in the supplied directory and exposes a deterministic lookup by filename.
    No network access is performed at any point.
    """

    def __init__(
        self,
        by_name: dict[str, dict[str, object]],
        registry: Registry[Any],
    ) -> None:
        self._by_name = by_name
        self._registry = registry

    @classmethod
    def from_directory(cls, schema_dir: Path) -> ContractRegistry:
        """Build a registry from every ``*_SCHEMA*.json`` file in *schema_dir*.

        Fails explicitly for:

        - malformed JSON (``ValueError``);
        - non-object schema root (``TypeError``);
        - schema that does not satisfy the Draft 2020-12 meta-schema
          (``jsonschema.SchemaError``);
        - duplicate ``$id`` values across schemas in the directory
          (``ValueError``).

        Does not perform any network access.
        """
        by_name: dict[str, dict[str, object]] = {}
        seen_ids: set[str] = set()
        registry: Registry[Any] = Registry()

        for path in sorted(schema_dir.glob("*_SCHEMA*.json")):
            try:
                raw: object = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSON in {path.name}: {exc}") from exc

            if not isinstance(raw, dict):
                raise TypeError(
                    f"Schema root must be a JSON object, got {type(raw).__name__}: {path.name}"
                )

            schema: dict[str, object] = raw
            Draft202012Validator.check_schema(schema)
            by_name[path.name] = schema

            schema_id = schema.get("$id")
            if isinstance(schema_id, str):
                if schema_id in seen_ids:
                    raise ValueError(
                        f"Duplicate schema $id {schema_id!r} encountered in {path.name}"
                    )
                seen_ids.add(schema_id)
                registry = registry.with_resource(schema_id, Resource.from_contents(schema))

        return cls(by_name, registry)

    def validator_by_name(self, filename: str) -> Any:
        """Return a ``Draft202012Validator`` configured for *filename*.

        The validator uses the in-memory local registry for ``$ref`` resolution.
        No network access is performed.

        Raises ``KeyError`` for an unknown *filename*.
        """
        if filename not in self._by_name:
            available = sorted(self._by_name)
            raise KeyError(f"Unknown schema {filename!r}. Available: {available}")
        return Draft202012Validator(self._by_name[filename], registry=self._registry)

    @property
    def schema_names(self) -> frozenset[str]:
        """Filenames of all loaded schemas."""
        return frozenset(self._by_name)
