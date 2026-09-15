# -*- coding: utf-8 -*-
"""
원시 데이터(raw) -> 전처리/매핑 후 데이터를 같은 행 단위로 나란히 보여주기 위한
예시 차량 2대(SAMPLE_VIDS)의 원본+파생 컬럼을 추출한다.
scripts/01_pipeline.py와 완전히 동일한 변환식을 이 두 차량에 대해서만 재계산한다
(속도를 위해 부분 재계산 -- 값은 outputs/*와 100% 동일해야 함).
"""
import json
import numpy as np
import pandas as pd

ENC = "utf-8"
COUNTERS = ["171_0", "666_0", "427_0", "837_0", "309_0", "835_0", "370_0", "100_0"]
BASELINE_MIN_READOUTS = 4
Z_THRESH = 2.5
LOOKBACK_H = 240

GROUP_LABEL = {"Cat0": "형상A", "Cat1": "형상B", "Cat2": "형상C", "Cat3": "형상D"}

SAMPLE_VIDS = [1201, 19222]  # 둘 다 형상B(Cat1) 수리차량: 탐지 성공 예시 vs 탐지 실패 예시

tte = pd.read_csv("data_raw/train_tte.csv", encoding=ENC)
spec = pd.read_csv("data_raw/train_specifications.csv", encoding=ENC)
veh = tte.merge(spec, on="vehicle_id")

dtype_map = {"vehicle_id": "int32", "time_step": "float32"}
for c in COUNTERS:
    dtype_map[c] = "float32"

print("loading operational readouts once for", SAMPLE_VIDS, "...")
ro_all = pd.read_csv("data_raw/train_operational_readouts.csv", dtype=dtype_map,
                      usecols=["vehicle_id", "time_step"] + COUNTERS)
ro_all = ro_all[ro_all.vehicle_id.isin(SAMPLE_VIDS)]

samples = []
for vid in SAMPLE_VIDS:
    ro = ro_all[ro_all.vehicle_id == vid].sort_values("time_step").reset_index(drop=True)
    raw_rows = ro[["time_step"] + COUNTERS].copy()

    # same transform as 01_pipeline.py, computed for this single vehicle
    dt = ro["time_step"].diff()
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

    vrow = veh[veh.vehicle_id == vid].iloc[0]
    flagged = ro[ro.anomaly_score > Z_THRESH]
    first_flag = float(flagged.time_step.min()) if len(flagged) else None
    lead_time = (vrow.length_of_study_time_step - first_flag) if first_flag is not None else None
    detected = bool(lead_time is not None and 0 <= lead_time <= 60)

    processed_rows = []
    for _, r in ro.iterrows():
        processed_rows.append(dict(
            time_step=round(float(r.time_step), 1),
            rates={c: (None if pd.isna(r[f"{c}_rate"]) else round(float(r[f"{c}_rate"]), 2)) for c in COUNTERS},
            zscores={c: (None if pd.isna(r[f"{c}_z"]) else round(float(r[f"{c}_z"]), 2)) for c in COUNTERS},
            anomaly_score=(None if pd.isna(r.anomaly_score) else round(float(r.anomaly_score), 3)),
            flagged=bool(pd.notna(r.anomaly_score) and r.anomaly_score > Z_THRESH),
        ))

    raw_out = []
    for _, r in raw_rows.iterrows():
        raw_out.append(dict(time_step=round(float(r.time_step), 1),
                             counters={c: (None if pd.isna(r[c]) else round(float(r[c]), 1)) for c in COUNTERS}))

    samples.append(dict(
        vehicle_id=int(vid),
        raw_mapping=dict(vehicle_id=int(vid), Spec_3=vrow.Spec_3, in_study_repair=int(vrow.in_study_repair),
                          length_of_study_time_step=float(vrow.length_of_study_time_step)),
        mapped=dict(group=vrow.Spec_3, group_label=GROUP_LABEL[vrow.Spec_3],
                    failure_label="수리(고장)" if vrow.in_study_repair else "무고장",
                    exposure_time_step=float(vrow.length_of_study_time_step)),
        derived_summary=dict(first_flag_time_step=first_flag, lead_time=(round(lead_time, 1) if lead_time is not None else None),
                              detected_within_lookback=detected,
                              n_readouts=len(ro)),
        raw_rows=raw_out,
        processed_rows=processed_rows,
    ))
    print(vid, "readouts:", len(ro), "detected:", detected, "lead_time:", lead_time)

with open("app_data/transform_sample.json", "w", encoding="utf-8") as f:
    json.dump(dict(counters=COUNTERS, z_thresh=Z_THRESH, samples=samples), f, ensure_ascii=False, indent=2)
print("wrote app_data/transform_sample.json")
