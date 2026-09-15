# -*- coding: utf-8 -*-
import json
import pandas as pd

ENC = "utf-8"
APP = "app_data"
import os
os.makedirs(APP, exist_ok=True)

ws = pd.read_csv("outputs/fmeca_worksheet.csv", encoding=ENC)
occ = pd.read_csv("outputs/occurrence_stats.csv", encoding=ENC)
sev = pd.read_csv("outputs/severity_stats.csv", encoding=ENC)
det = pd.read_csv("outputs/detection_stats.csv", encoding=ENC)
cl = json.load(open("outputs/cleansing_stats.json", encoding="utf-8"))
lifecycle = json.load(open("outputs/lifecycle.json", encoding="utf-8"))
spec2_case = json.load(open("outputs/spec2_case.json", encoding="utf-8"))
feat = pd.read_csv("outputs/vehicle_features.csv", encoding=ENC)
tte = pd.read_csv("data_raw/train_tte.csv")
spec = pd.read_csv("data_raw/train_specifications.csv")

GROUP_LABEL = {"Cat0": "형상A", "Cat1": "형상B", "Cat2": "형상C", "Cat3": "형상D"}

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

# vehicle-level explorer export (sampled to keep the file light: all repaired + a random sample of healthy)
rep = feat[feat.in_study_repair == 1]
healthy_sample = feat[feat.in_study_repair == 0].sample(n=min(3000, (feat.in_study_repair == 0).sum()), random_state=0)
ev = pd.concat([rep, healthy_sample]).copy()
ev_out = ev[["vehicle_id", "Spec_3", "in_study_repair", "length_of_study_time_step",
             "severity_anomaly_at_end", "first_flag_time_step", "lead_time", "detected_within_lookback"]].copy()
ev_out["group_label"] = ev_out.Spec_3.map(GROUP_LABEL)
ev_out.to_json(f"{APP}/events.json", orient="records", force_ascii=False, indent=0)

dataset = dict(
    source="SCANIA Component X dataset (Kharazian et al. 2025, Scientific Data)",
    source_url="https://doi.org/10.5878/jvb5-d390",
    license="CC BY 4.0",
    n_vehicles=int(len(tte)),
    n_repairs=int(tte.in_study_repair.sum()),
    n_readout_rows=int(cl["01_sync"]["operational_readouts_rows"]),
    total_exposure_time_steps=float(tte.length_of_study_time_step.sum()),
    groups={GROUP_LABEL.get(k, k): int(v) for k, v in spec.Spec_3.value_counts().to_dict().items()},
    counters=["171_0", "666_0", "427_0", "837_0", "309_0", "835_0", "370_0", "100_0"],
)
with open(f"{APP}/dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print("dataset:", dataset)
print("modes:", len(modes), "events:", len(ev_out))
print("OK")
