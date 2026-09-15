# -*- coding: utf-8 -*-
"""
원시 데이터(raw) -> 전처리/매핑 후 데이터를 같은 행 단위로 나란히 보여주기 위한
예시 자산 2대의 원본+파생 컬럼을 추출한다. 01_pipeline.py와 완전히 동일한 변환식을
이 두 자산에 대해서만 재계산한다(속도를 위해 부분 재계산 -- 값은 outputs/*와 100% 동일해야 함).

예시 자산 2대는 vehicle_features.csv에서 자동 선택한다: 같은 그룹 안에서 조기탐지
"성공" 사례 1건 + "실패" 사례 1건을 고른다(둘 다 없으면 임의의 고장 자산 2건으로 대체).

Usage: python 04_export_transform_sample.py --dataset ../datasets/scania_component_x
"""
import argparse
import json
import numpy as np
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
RTIME = cfg.readout_time
COUNTERS = cfg.counters
GROUP_COL = cfg.group_col
Z_THRESH = cfg.param("z_thresh", 2.5)
GROUP_LABEL = cfg.groups

feat = pd.read_csv(f"{OUT}/vehicle_features.csv", encoding=ENC)
failed = feat[feat[LABEL] == 1]

sample_ids = []
if len(failed):
    by_group_detect = failed.groupby([GROUP_COL, "detected_within_lookback"]).size()
    top_group = failed[GROUP_COL].value_counts().idxmax()
    grp_rows = failed[failed[GROUP_COL] == top_group]
    detected = grp_rows[grp_rows.detected_within_lookback == True]
    missed = grp_rows[grp_rows.detected_within_lookback == False]
    if len(detected) and len(missed):
        sample_ids = [int(detected.iloc[0][ASSET]), int(missed.iloc[0][ASSET])]
    else:
        sample_ids = [int(x) for x in failed[ASSET].head(2)]
SAMPLE_IDS = sample_ids
print("auto-selected sample assets:", SAMPLE_IDS)

veh = pd.read_csv(cfg.files["events"]).merge(pd.read_csv(cfg.files["groups"]), on=ASSET)

dtype_map = {ASSET: "int32", RTIME: "float32"}
for c in COUNTERS:
    dtype_map[c] = "float32"

print("loading readouts once for", SAMPLE_IDS, "...")
ro_all = pd.read_csv(cfg.files["readouts"], dtype=dtype_map, usecols=[ASSET, RTIME] + COUNTERS)
ro_all = ro_all[ro_all[ASSET].isin(SAMPLE_IDS)]

samples = []
for vid in SAMPLE_IDS:
    ro = ro_all[ro_all[ASSET] == vid].sort_values(RTIME).reset_index(drop=True)
    raw_rows = ro[[RTIME] + COUNTERS].copy()

    # same transform as 01_pipeline.py, computed for this single asset
    dt = ro[RTIME].diff()
    for c in COUNTERS:
        dval = ro[c].diff()
        rate = dval / dt.replace(0, np.nan)
        ro[f"{c}_rate"] = rate
    rate_cols = [f"{c}_rate" for c in COUNTERS]
    for rc in rate_cols:
        ro.loc[ro[rc] < 0, rc] = np.nan

    ro["rn"] = np.arange(len(ro))[::-1]  # 0 = last readout
    base_mask = ro["rn"] >= 1
    base_stats = {}
    for c in COUNTERS:
        vals = ro.loc[base_mask, f"{c}_rate"]
        base_stats[f"{c}_rate_mean"] = vals.mean()
        base_stats[f"{c}_rate_std"] = vals.std()
    for c in COUNTERS:
        m, s = base_stats[f"{c}_rate_mean"], base_stats[f"{c}_rate_std"]
        ro[f"{c}_z"] = (ro[f"{c}_rate"] - m) / (s if s else np.nan)
    z_cols = [f"{c}_z" for c in COUNTERS]
    ro["anomaly_score"] = ro[z_cols].abs().mean(axis=1, skipna=True)

    vrow = veh[veh[ASSET] == vid].iloc[0]
    flagged = ro[ro.anomaly_score > Z_THRESH]
    first_flag = float(flagged[RTIME].min()) if len(flagged) else None
    lead_time = (vrow[EXPOSURE] - first_flag) if first_flag is not None else None
    detected = bool(lead_time is not None and 0 <= lead_time <= 60)

    processed_rows = []
    for _, r in ro.iterrows():
        processed_rows.append(dict(
            time_step=round(float(r[RTIME]), 1),
            rates={c: (None if pd.isna(r[f"{c}_rate"]) else round(float(r[f"{c}_rate"]), 2)) for c in COUNTERS},
            zscores={c: (None if pd.isna(r[f"{c}_z"]) else round(float(r[f"{c}_z"]), 2)) for c in COUNTERS},
            anomaly_score=(None if pd.isna(r.anomaly_score) else round(float(r.anomaly_score), 3)),
            flagged=bool(pd.notna(r.anomaly_score) and r.anomaly_score > Z_THRESH),
        ))

    raw_out = []
    for _, r in raw_rows.iterrows():
        raw_out.append(dict(time_step=round(float(r[RTIME]), 1),
                             counters={c: (None if pd.isna(r[c]) else round(float(r[c]), 1)) for c in COUNTERS}))

    grp_val = vrow[GROUP_COL]
    samples.append(dict(
        asset_id=int(vid),
        raw_mapping={"asset_id_field": ASSET, "asset_id": int(vid),
                     "group_field": GROUP_COL, "group": grp_val,
                     "label_field": LABEL, "failed": int(vrow[LABEL]),
                     "exposure_field": EXPOSURE, "exposure_time": float(vrow[EXPOSURE])},
        mapped=dict(group=grp_val, group_label=GROUP_LABEL.get(grp_val, grp_val),
                    failure_label="수리(고장)" if vrow[LABEL] else "무고장",
                    exposure_time_step=float(vrow[EXPOSURE])),
        derived_summary=dict(first_flag_time_step=first_flag, lead_time=(round(lead_time, 1) if lead_time is not None else None),
                              detected_within_lookback=detected,
                              n_readouts=len(ro)),
        raw_rows=raw_out,
        processed_rows=processed_rows,
    ))
    print(vid, "readouts:", len(ro), "detected:", detected, "lead_time:", lead_time)

with open(f"{APP}/transform_sample.json", "w", encoding="utf-8") as f:
    json.dump(dict(counters=COUNTERS, z_thresh=Z_THRESH, samples=samples), f, ensure_ascii=False, indent=2)
print(f"wrote {APP}/transform_sample.json")
