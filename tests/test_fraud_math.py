"""Canonicalization and pure rarity math. Expected numbers are computed by hand here."""
from __future__ import annotations

import math
from dataclasses import replace
from typing import get_args

import pytest

from prism.contract import EntityKind
from prism.engine.config import ConfigError, load_fraud_config
from prism.fraud import canon, rarity


# --------------------------------------------------------------------------- canon

def test_legal_suffix_variants_share_one_key():
    keys = {canon.split_legal_suffix(s) for s in ("Zeta Works, L.L.C.", "ZETA WORKS LLC", "zeta works llc")}
    assert len(keys) == 1
    k = keys.pop()
    assert (k.base, k.suffix, k.full) == ("zeta works", "llc", "zeta works llc")


def test_different_suffix_same_base():
    a, b = canon.split_legal_suffix("Zeta Works LLC"), canon.split_legal_suffix("Zeta Works Inc")
    assert a.base == b.base == "zeta works"
    assert a.suffix != b.suffix and a.full != b.full


def test_ampersand_and_suffix_only_names():
    k = canon.split_legal_suffix("Smith & Co")
    assert (k.base, k.suffix) == ("smith and", "co")
    assert canon.canon_text("A & B") == canon.canon_text("A and B")
    only = canon.split_legal_suffix("LLC")
    assert only.base == "llc" and only.suffix == "" and only.full == "llc"
    assert canon.split_legal_suffix("Acme Incorporated").suffix == "inc"
    assert canon.canon_text("O'Brien Ltd.") == "obrien ltd"


def test_phone_variants_collapse():
    for raw in ("(210) 555-0142", "210.555.0142", "1-210-555-0142"):
        assert canon.canon_phone(raw) == "2105550142"
    assert canon.canon_phone("") == ""
    assert canon.canon_phone(None) == ""


def test_address_variants_collapse_and_ignore_order():
    a = canon.canon_address("12 Main St., Suite 4")
    assert a == canon.canon_address("12 main street ste 4")
    assert canon.canon_address("Suite 4, 12 Main Street") == a


def test_canon_value_is_idempotent_for_every_kind():
    samples = ["Zeta Works, L.L.C.", "12 Main St., Suite 4", "(210) 555-0142", "AB-12 cd", "Smith & Co", "  "]
    for kind in get_args(EntityKind):
        for s in samples:
            once = canon.canon_value(kind, s)
            assert canon.canon_value(kind, once) == once, (kind, s)
    assert canon.canon_value("vendor", None) == ""
    assert canon.canon_value("vendor", "Zeta Works Inc.") == "zeta works inc"
    assert canon.canon_value("remit_account", "ab-12 3") == "ab123"


# --------------------------------------------------------------------------- rarity

def test_surprisal_values():
    n = 257
    for df, want in ((0, 8.011), (5, 5.43), (15, 4.01), (200, 0.36)):
        assert rarity.surprisal(df, n) == pytest.approx(want, abs=0.01)
        assert rarity.surprisal(df, n) == pytest.approx(-math.log2((df + 1) / (n + 1)))
    assert rarity.surprisal(0, 0) == 0.0
    assert rarity.p_hat(2, 9) == pytest.approx(0.3)


def test_is_strong_rules():
    assert rarity.is_strong(5, 257, 2, 0.02, 2)
    assert not rarity.is_strong(6, 257, 2, 0.02, 2)
    assert not rarity.is_strong(0, 257, 1, 0.02, 2)
    assert not rarity.is_strong(2, 257, 2, 0.02, 3)
    assert rarity.is_strong(2, 257, 3, 0.02, 3)
    assert not rarity.is_strong(0, 0, 5, 0.02, 2)


def test_outcome_discount():
    assert rarity.outcome_discount(2, 2, 0.5) == pytest.approx(0.625)
    assert rarity.outcome_discount(0, 2, 0.5) == pytest.approx(0.875)
    assert rarity.outcome_discount(2, 2, 0.0) == 1.0
    assert rarity.outcome_discount(7, 9, 0.0) == 1.0


def test_params_from_config_and_validation():
    cfg = load_fraud_config()
    p = rarity.FraudParams.from_config(cfg)
    assert p.rho == cfg.f1_rarity_fraction and p.min_linked == cfg.f1_min_linked_deals
    assert p.type_weights["remit_account"] > p.type_weights["address"] > 0
    assert 0 <= p.outcome_beta <= 1
    assert p.train_end == cfg.train_end
    assert rarity.FraudParams.from_config(None).type_weights == {}

    def bad(**raw_f1):
        raw = {**cfg.raw, "families": {**cfg.raw["families"], "F1": {**cfg.raw["families"]["F1"], **raw_f1}}}
        return replace(cfg, raw=raw)

    with pytest.raises(ConfigError):
        rarity.FraudParams.from_config(bad(type_weights={"preparer": -1.0}))
    with pytest.raises(ConfigError):
        rarity.FraudParams.from_config(bad(outcome_beta=1.5))
    with pytest.raises(ConfigError):
        rarity.FraudParams.from_config(bad(outcome_beta="x"))
