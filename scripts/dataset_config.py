# -*- coding: utf-8 -*-
"""Loads a dataset's config.yaml (see /DATASET_FORMAT.md) and resolves the
paths/columns/params/assumptions every pipeline stage needs. Shared by
01_pipeline.py, 02_lifecycle.py, 03_export_app_data.py and
04_export_transform_sample.py so the dataset contract is defined in exactly
one place.

A dataset can define MULTIPLE failure modes (e.g. engine vs transmission vs
hydraulics on the same platform) -- each with its own files/columns/counters,
since different components plausibly come from different sensor sets
entirely. A dataset with only one failure mode (like SCANIA Component X,
which is a single anonymized component split into FMECA rows by vehicle
spec) just declares a `failure_modes:` list with one entry.
"""
import os
import yaml


class FailureMode:
    def __init__(self, base_dir, raw):
        self.id = raw["id"]
        self.label = raw.get("label", self.id)
        self.cause = raw.get("cause")  # optional free-text root-cause note
        self.files = {k: os.path.join(base_dir, v) for k, v in raw["files"].items()}
        self.columns = raw["columns"]
        self.groups = raw.get("groups", {})
        self.params = raw.get("params", {})

    @property
    def asset_id(self): return self.columns["asset_id"]
    @property
    def exposure_time(self): return self.columns["exposure_time"]
    @property
    def failure_label(self): return self.columns["failure_label"]
    @property
    def readout_time(self): return self.columns["readout_time"]
    @property
    def counters(self): return self.columns["counters"]
    @property
    def group_col(self): return self.columns["group_col"]
    @property
    def bonus_group_col(self): return self.columns.get("bonus_group_col")

    def group_label(self, value):
        return self.groups.get(value, value)

    def param(self, name, default=None):
        return self.params.get(name, default)


class DatasetConfig:
    def __init__(self, dataset_dir):
        self.dir = os.path.abspath(dataset_dir)
        cfg_path = os.path.join(self.dir, "config.yaml")
        with open(cfg_path, encoding="utf-8") as f:
            self.raw = yaml.safe_load(f)

        self.dataset = self.raw["dataset"]
        self.assumptions = self.raw.get("assumptions", {})
        self.content = self.raw.get("content", {})
        self.modes = [FailureMode(self.dir, m) for m in self.raw["failure_modes"]]

        self.out_dir = os.path.join(self.dir, "outputs")
        self.app_data_dir = os.path.join(self.dir, "app_data")
        os.makedirs(self.out_dir, exist_ok=True)
        os.makedirs(self.app_data_dir, exist_ok=True)

    def mode(self, mode_id):
        return next(m for m in self.modes if m.id == mode_id)

    def assumption(self, name, default=None):
        """Returns the VALUE of an assumption. Each assumption in config.yaml
        is {value, rationale} -- see /DATASET_FORMAT.md for why both are
        required (an assumed number with no stated reason is not trustworthy)."""
        a = self.assumptions.get(name)
        if a is None:
            return default
        return a["value"] if isinstance(a, dict) else a

    def assumption_rationale(self, name):
        a = self.assumptions.get(name)
        return a.get("rationale") if isinstance(a, dict) else None

    def assumptions_list(self):
        """[{name, value, rationale}, ...] for display (worksheet notes, web app)."""
        out = []
        for name, a in self.assumptions.items():
            if isinstance(a, dict):
                out.append(dict(name=name, value=a.get("value"), rationale=a.get("rationale")))
            else:
                out.append(dict(name=name, value=a, rationale=None))
        return out
