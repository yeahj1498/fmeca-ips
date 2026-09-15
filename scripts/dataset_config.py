# -*- coding: utf-8 -*-
"""Loads a dataset's config.yaml (see /DATASET_FORMAT.md) and resolves the
paths/columns/params/assumptions every pipeline stage needs. Shared by
01_pipeline.py, 02_lifecycle.py and 03_export_app_data.py so the dataset
contract is defined in exactly one place.
"""
import os
import yaml


class DatasetConfig:
    def __init__(self, dataset_dir):
        self.dir = os.path.abspath(dataset_dir)
        cfg_path = os.path.join(self.dir, "config.yaml")
        with open(cfg_path, encoding="utf-8") as f:
            self.raw = yaml.safe_load(f)

        self.dataset = self.raw["dataset"]
        self.columns = self.raw["columns"]
        self.groups = self.raw.get("groups", {})
        self.params = self.raw.get("params", {})
        self.assumptions = self.raw.get("assumptions", {})
        self.content = self.raw.get("content", {})

        self.files = {k: os.path.join(self.dir, v) for k, v in self.raw["files"].items()}
        self.out_dir = os.path.join(self.dir, "outputs")
        self.app_data_dir = os.path.join(self.dir, "app_data")
        os.makedirs(self.out_dir, exist_ok=True)
        os.makedirs(self.app_data_dir, exist_ok=True)

    # shorthand accessors for the frequently used values
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
