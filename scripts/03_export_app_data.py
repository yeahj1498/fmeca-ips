# -*- coding: utf-8 -*-
"""Exports <dataset>/outputs/* into <dataset>/app_data/*.json for the generic
web app (app/index.html) to fetch(). Generic across datasets -- see
/DATASET_FORMAT.md. Also carries the dataset's config.yaml `content:` block
through unchanged, since that narrative text is written per-dataset by hand.

Usage: python 03_export_app_data.py --dataset ../datasets/scania_component_x
"""
import argparse
import json
import os
import pandas as pd
from dataset_config import DatasetConfig

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", required=True)
args = ap.parse_args()
cfg = DatasetConfig(args.dataset)

ENC = "utf-8"
OUT = cfg.out_dir
APP = cfg.app_data_dir

ASSET = cfg.asset_id
EXPOSURE = cfg.exposure_time
LABEL = cfg.failure_label
GROUP_COL = cfg.group_col

ws = pd.read_csv(f"{OUT}/fmeca_worksheet.csv", encoding=ENC)
occ = pd.read_csv(f"{OUT}/occurrence_stats.csv", encoding=ENC)
sev = pd.read_csv(f"{OUT}/severity_stats.csv", encoding=ENC)
det = pd.read_csv(f"{OUT}/detection_stats.csv", encoding=ENC)
cl = json.load(open(f"{OUT}/cleansing_stats.json", encoding="utf-8"))
lifecycle = json.load(open(f"{OUT}/lifecycle.json", encoding="utf-8"))
spec2_path = f"{OUT}/spec2_case.json"
spec2_case = json.load(open(spec2_path, encoding="utf-8")) if os.path.exists(spec2_path) else None
feat = pd.read_csv(f"{OUT}/vehicle_features.csv", encoding=ENC)
events = pd.read_csv(cfg.files["events"])
groups_df = pd.read_csv(cfg.files["groups"])

GROUP_LABEL = cfg.groups

occ_extra = occ[["group", "n_vehicles", "exposure_time_steps", "rate_per_1000_timesteps", "ci95_lo", "ci95_hi"]]
sev_extra = sev[["group", "mean_severity_anomaly", "mean_signed_z", "mean_error_rate_pct", "hazop_guide_word"]]
det_extra = det[["group", "detection_rate_pct", "expected_rate_if_random_pct", "binom_p", "mean_lead_time", "median_lead_time"]]

merged = ws.merge(occ_extra, left_on="failure_mode_group", right_on="group").merge(sev_extra, on="group").merge(det_extra, on="group")
modes = []
for _, r in merged.iterrows():
    modes.append(dict(
        group=r.group, label=GROUP_LABEL.get(r.group, r.group), n_vehicles=int(r.n_vehicles), n_repairs=int(r.n_repairs),
        O_grade=int(r.O_grade), S_grade=int(r.S_grade), D_grade=int(r.D_grade),
        RPN=int(r.RPN), rank_RPN=int(r.rank_RPN), RI_weighted=float(r.RI_weighted), rank_RI=int(r.rank_RI),
        rank_changed=bool(r.rank_changed), O_basis=r.O_basis, S_basis=r.S_basis, D_basis=r.D_basis,
        rate_per_1000=float(r.rate_per_1000_timesteps), ci95_lo=float(r.ci95_lo), ci95_hi=float(r.ci95_hi),
        mean_severity_anomaly=(None if pd.isna(r.mean_severity_anomaly) else float(r.mean_severity_anomaly)),
        mean_signed_z=(None if pd.isna(r.mean_signed_z) else float(r.mean_signed_z)),
        mean_error_rate_pct=(None if pd.isna(r.mean_error_rate_pct) else float(r.mean_error_rate_pct)),
        hazop_guide_word=r.hazop_guide_word,
        detection_rate_pct=(None if pd.isna(r.detection_rate_pct) else float(r.detection_rate_pct)),
        expected_rate_if_random=(None if pd.isna(r.expected_rate_if_random_pct) else float(r.expected_rate_if_random_pct)),
        binom_p=(None if pd.isna(r.binom_p) else float(r.binom_p)),
        significant=bool(pd.notna(r.binom_p) and r.binom_p < 0.05),
        mean_lead_time=(None if pd.isna(r.mean_lead_time) else float(r.mean_lead_time)),
        median_lead_time=(None if pd.isna(r.median_lead_time) else float(r.median_lead_time)),
    ))
modes.sort(key=lambda x: x["rank_RPN"])

with open(f"{APP}/fmeca.json", "w", encoding="utf-8") as f:
    json.dump({"modes": modes, "spec2_case": spec2_case}, f, ensure_ascii=False, indent=2)

with open(f"{APP}/cleansing.json", "w", encoding="utf-8") as f:
    json.dump(cl, f, ensure_ascii=False, indent=2)
with open(f"{APP}/lifecycle.json", "w", encoding="utf-8") as f:
    json.dump(lifecycle, f, ensure_ascii=False, indent=2)

# asset-level explorer export (sampled to keep the file light: all failed + a random sample of healthy)
rep = feat[feat[LABEL] == 1]
healthy_sample = feat[feat[LABEL] == 0].sample(n=min(3000, (feat[LABEL] == 0).sum()), random_state=0)
ev = pd.concat([rep, healthy_sample]).copy()
ev_out = ev[[ASSET, GROUP_COL, LABEL, EXPOSURE,
             "severity_anomaly_at_end", "first_flag_time_step", "lead_time", "detected_within_lookback"]].copy()
ev_out["group_label"] = ev_out[GROUP_COL].map(GROUP_LABEL)
# rename to generic field names so the web app doesn't need to know this dataset's
# actual column names -- see /DATASET_FORMAT.md
ev_out = ev_out.rename(columns={ASSET: "asset_id", GROUP_COL: "group", LABEL: "failed", EXPOSURE: "exposure_time"})
ev_out.to_json(f"{APP}/events.json", orient="records", force_ascii=False, indent=0)

n_groups = len(modes)
d = cfg.dataset
dataset = dict(
    name=d["name"],
    component_label=d.get("component_label", ""),
    source=f"{d['name']} ({d.get('citation', '')})",
    source_url=d.get("source_url", ""),
    license=d.get("license", ""),
    n_vehicles=int(len(events)),
    n_repairs=int(events[LABEL].sum()),
    n_readout_rows=int(cl["01_sync"]["readout_rows"]),
    total_exposure_time_steps=float(events[EXPOSURE].sum()),
    groups={GROUP_LABEL.get(k, k): int(v) for k, v in groups_df[GROUP_COL].value_counts().to_dict().items()},
    counters=cfg.counters,
    group_col=GROUP_COL,
    bonus_group_col=cfg.bonus_group_col,
    n_groups=n_groups,
)

def fill(template):
    if not isinstance(template, str):
        return template
    return template.format(**dataset)

content = {k: (fill(v) if isinstance(v, str) else v) for k, v in cfg.content.items()}
dataset["content"] = content

with open(f"{APP}/dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print("dataset:", {k: v for k, v in dataset.items() if k != "content"})
print("modes:", len(modes), "events:", len(ev_out))
print("OK ->", APP)
