"""
Fixtures compartilhadas dos testes de modelagem/governança.

`fixture_db` constrói UMA vez por sessão um warehouse SQLite completo (schema
físico real do ETL + fixture sintética determinística), sem depender do dataset
de terceiros nem de dados pessoais reais.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "data-platform", ROOT / "data-platform" / "ingestion", ROOT / "data-platform" / "quality"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session")
def fixture_build(tmp_path_factory):
    from extract_transform_load import build_warehouse
    from governance.fixtures import synthetic_raw

    db = tmp_path_factory.mktemp("warehouse") / "fixture.db"
    stats = build_warehouse(synthetic_raw(), db, "synthetic_fixture(seed=42)", None, None)
    return db, stats


@pytest.fixture(scope="session")
def fixture_db(fixture_build) -> Path:
    return fixture_build[0]


@pytest.fixture()
def db_copy(fixture_db, tmp_path) -> Path:
    """Cópia descartável do warehouse para testes que alteram o banco."""
    dst = tmp_path / "copy.db"
    shutil.copyfile(fixture_db, dst)
    return dst
