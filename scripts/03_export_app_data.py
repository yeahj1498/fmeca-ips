# -*- coding: utf-8 -*-
"""Exports <dataset>/outputs/* into <dataset>/app_data/*.json for the generic
web app (app/index.html) to fetch(). Generic across datasets AND multiple
failure modes -- see /DATASET_FORMAT.md. Also carries the dataset's
config.yaml `content:` block through unchanged, since that narrative text is
written per-dataset by hand.

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

ws = pd.read_csv(f"{OUT}/fmeca_worksheet.csv", encoding=ENC)
occ = pd.read_csv(f"{OUT}/occurrence_stats.csv", encoding=ENC)
sev = pd.read_csv(f"{OUT}/severity_stats.csv", encoding=ENC)
det = pd.read_csv(f"{OUT}/detection_stats.csv", encoding=ENC)
cl = json.load(open(f"{OUT}/cleansing_stats.json", encoding="utf-8"))
lifecycle = json.load(open(f"{OUT}/lifecycle.json", encoding="utf-8"))
spec2_path = f"{OUT}/spec2_case.json"
spec2_case = json.load(open(spec2_path, encoding="utf-8")) if os.path.exists(spec2_path) else None
feat = pd.read_csv(f"{OUT}/vehicle_features.csv", encoding=ENC)

KEY = ["failure_mode", "group"]
occ_extra = occ[KEY + ["n_vehicles", "exposure_time_steps", "rate_per_1000_timesteps", "ci95_lo", "ci95_hi"]]
sev_extra = sev[KEY + ["mean_severity_anomaly", "mean_signed_z", "mean_error_rate_pct", "hazop_guide_word"]]
det_extra = det[KEY + ["detection_rate_pct", "expected_rate_if_random_pct", "binom_p", "mean_lead_time", "median_lead_time"]]

merged = ws.rename(columns={"failure_mode_group": "group"}).merge(
    occ_extra, on=KEY).merge(sev_extra, on=KEY).merge(det_extra, on=KEY)

modes = []
for _, r in merged.iterrows():
    fm = cfg.mode(r.failure_mode)
    modes.append(dict(
        failure_mode=r.failure_mode, failure_mode_label=fm.label, failure_cause=fm.cause,
        group=r.group, label=fm.group_label(r.group), n_vehicles=int(r.n_vehicles), n_repairs=int(r.n_repairs),
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
# each failure mode has its own asset_id/group/label/exposure columns, so export per-mode then concat.
ev_parts = []
for fm in cfg.modes:
    ASSET, GROUP_COL, LABEL, EXPOSURE = fm.asset_id, fm.group_col, fm.failure_label, fm.exposure_time
    fmt_feat = feat[feat.failure_mode == fm.id]
    rep = fmt_feat[fmt_feat[LABEL] == 1]
    healthy_pool = fmt_feat[fmt_feat[LABEL] == 0]
    healthy_sample = healthy_pool.sample(n=min(3000, len(healthy_pool)), random_state=0)
    ev = pd.concat([rep, healthy_sample]).copy()
    ev_out = ev[[ASSET, GROUP_COL, LABEL, EXPOSURE,
                 "severity_anomaly_at_end", "first_flag_time_step", "lead_time", "detected_within_lookback"]].copy()
    ev_out["group_label"] = ev_out[GROUP_COL].map(fm.groups)
    ev_out = ev_out.rename(columns={ASSET: "asset_id", GROUP_COL: "group", LABEL: "failed", EXPOSURE: "exposure_time"})
    ev_out.insert(0, "failure_mode", fm.id)
    ev_out.insert(1, "failure_mode_label", fm.label)
    ev_parts.append(ev_out)
ev_all = pd.concat(ev_parts, ignore_index=True)
ev_all.to_json(f"{APP}/events.json", orient="records", force_ascii=False, indent=0)

n_groups = len(modes)
d = cfg.dataset
first_mode = cfg.modes[0]
dataset = dict(
    name=d["name"],
    component_label=d.get("component_label", ""),
    source=f"{d['name']} ({d.get('citation', '')})",
    source_url=d.get("source_url", ""),
    license=d.get("license", ""),
    n_vehicles=int(sum(feat[feat.failure_mode == m.id][m.asset_id].nunique() for m in cfg.modes)),
    n_repairs=int(sum(int((feat[feat.failure_mode == m.id][m.failure_label] == 1).sum()) for m in cfg.modes)),
    n_readout_rows=int(sum(cl[m.id]["01_sync"]["readout_rows"] for m in cfg.modes)),
    total_exposure_time_steps=float(sum(feat[feat.failure_mode == m.id][m.exposure_time].sum() for m in cfg.modes)),
    groups={(m.group_label(k) if len(cfg.modes) == 1 else f"{m.label} · {m.group_label(k)}"): int(v)
            for m in cfg.modes for k, v in feat[feat.failure_mode == m.id][m.group_col].value_counts().to_dict().items()},
    counters=sorted({c for m in cfg.modes for c in m.counters}),
    group_col=first_mode.group_col if len(cfg.modes) == 1 else "failure_mode + group",
    bonus_group_col=first_mode.bonus_group_col if len(cfg.modes) == 1 else None,
    n_groups=n_groups,
    n_failure_modes=len(cfg.modes),
    failure_modes=[dict(id=m.id, label=m.label, cause=m.cause) for m in cfg.modes],
    assumptions=cfg.assumptions_list(),
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
print("modes:", len(modes), "events:", len(ev_all))
print("OK ->", APP)
