from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "refresh_catalog_contract", ROOT / "scripts" / "refresh_catalog.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_booth_observation_rejects_type_coercion_at_network_boundary() -> None:
    with pytest.raises(ValidationError):
        MOD.Observation(
            item_id="123",
            source_url="https://booth.pm/ja/items/123",
            status_code=200,
            price="1200",
        )
