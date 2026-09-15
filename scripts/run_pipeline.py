# -*- coding: utf-8 -*-
"""Runs the full FMECA-IPS pipeline for one dataset folder (see
/DATASET_FORMAT.md), then copies the result into app/data/ so the web app
serves it.

Usage: python scripts/run_pipeline.py --dataset datasets/scania_component_x
"""
import argparse
import os
import shutil
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", required=True, help="path to a dataset folder containing config.yaml")
ap.add_argument("--skip-app-copy", action="store_true", help="don't overwrite app/data/ with this dataset's output")
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
dataset_dir = os.path.abspath(args.dataset)

if not os.path.exists(os.path.join(dataset_dir, "config.yaml")):
    sys.exit(f"no config.yaml found in {dataset_dir} -- see /DATASET_FORMAT.md")

steps = ["01_pipeline.py", "02_lifecycle.py", "04_export_transform_sample.py", "03_export_app_data.py"]
for step in steps:
    print(f"\n=== {step} ===")
    r = subprocess.run([sys.executable, os.path.join(HERE, step), "--dataset", dataset_dir],
                        cwd=HERE, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        sys.exit(f"{step} failed (exit {r.returncode})")

if not args.skip_app_copy:
    app_data_src = os.path.join(dataset_dir, "app_data")
    app_data_dst = os.path.join(ROOT, "app", "data")
    if os.path.exists(app_data_dst):
        shutil.rmtree(app_data_dst)
    shutil.copytree(app_data_src, app_data_dst)
    print(f"\ncopied {app_data_src} -> {app_data_dst} (app/index.html will serve this dataset)")

print("\nDONE.")
