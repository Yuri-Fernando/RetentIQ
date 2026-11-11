"""Controles técnicos de privacidade do export de KPIs (pseudonimização + k-anonimato)."""
from __future__ import annotations

import pandas as pd
import pytest

from governance.privacy import KEY_ENV, build_kpi_export, generalize_rare, load_key, pseudonymize

KEY = b"chave-de-teste-nao-secreta-0123456789"


def test_key_is_required_and_minimum_length():
    with pytest.raises(RuntimeError):
        load_key({})
    with pytest.raises(RuntimeError):
        load_key({KEY_ENV: "curta"})
    assert load_key({KEY_ENV: "x" * 32}) == b"x" * 32


def test_pseudonymize_is_deterministic_keyed_and_opaque():
    t1, t2 = pseudonymize(90001, KEY), pseudonymize(90001, KEY)
    assert t1 == t2
    assert pseudonymize(90001, b"outra-chave-0123456789") != t1
    assert pseudonymize(90002, KEY) != t1
    assert "90001" not in t1 and len(t1) == 24


def test_generalize_rare_groups():
    s = pd.Series(["UK"] * 5 + ["FR"] * 2 + ["PT"])
    out = generalize_rare(s, k=3)
    assert set(out) == {"UK", "OUTROS"}


def test_export_minimizes_and_preserves_totals(fixture_db):
    k = 10
    out = build_kpi_export(fixture_db, KEY, k=k)
    assert "customer_id" not in out.columns and "primary_country" not in out.columns
    assert not out["customer_token"].astype(str).str.fullmatch(r"\d+").any()
    sizes = out["country_group"].value_counts()
    assert all(n >= k for g, n in sizes.items() if g != "OUTROS")
    assert out["last_purchase_month"].str.fullmatch(r"\d{4}-\d{2}").all()
    assert out["customer_token"].is_unique
