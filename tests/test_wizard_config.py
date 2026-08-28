"""The remembered look preference must never be able to stop someone grading.

It is a convenience stored outside the project, in a file the user can edit,
that survives upgrades which retire a LUT. Every failure mode here has to end in
"use the default", not in an exception.
"""
import json

import pytest

from silbersalz_look import wizard


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    monkeypatch.setattr(wizard, "config_path", lambda: p)
    return p


def test_missing_config_reads_as_empty(cfg):
    assert wizard.load_config() == {}
    assert wizard.remembered_look("250d") is None


def test_corrupt_config_reads_as_empty(cfg):
    cfg.write_text("{not json at all")
    assert wizard.load_config() == {}
    assert wizard.remembered_look("250d") is None


def test_config_that_is_not_an_object_reads_as_empty(cfg):
    cfg.write_text('["looks"]')
    assert wizard.load_config() == {}


def test_round_trip(cfg):
    wizard.remember_look("250d", "paired")
    assert json.loads(cfg.read_text(encoding="utf-8")) == {"looks": {"250d": "paired"}}
    assert wizard.remembered_look("250d") == "paired"


def test_remembering_one_stock_leaves_the_others_alone(cfg):
    wizard.remember_look("250d", "paired")
    wizard.remember_look("500t", "v1")
    assert wizard.load_config()["looks"] == {"250d": "paired", "500t": "v1"}


def test_a_remembered_key_for_a_retired_lut_is_ignored(cfg):
    cfg.write_text(json.dumps({"looks": {"250d": "some-lut-we-removed"}}), encoding="utf-8")
    assert wizard.remembered_look("250d") is None


def test_an_unwritable_config_is_not_an_error(tmp_path, monkeypatch):
    # a read-only home, a sandboxed install: storing the preference fails, grading does not
    monkeypatch.setattr(wizard, "config_path", lambda: tmp_path / "nope" / "config.json")
    monkeypatch.setattr(wizard.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(PermissionError()))
    wizard.remember_look("250d", "paired")   # must not raise
