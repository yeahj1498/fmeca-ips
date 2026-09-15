# -*- coding: utf-8 -*-
"""
FMECA pipeline on the REAL SCANIA Component X dataset (train split).
Source: SCANIA CV / Stockholm University, researchdata.se DOI 10.5878/jvb5-d390,
CC BY 4.0. Kharazian et al., "SCANIA Component X dataset: a real-world
multivariate time series dataset for predictive maintenance", Scientific Data (2025).

Real truck fleet, real repair records -- but the publisher explicitly perturbed
(scaled) operational data and repair rates, and anonymized all variable names,
for confidentiality. See 01_dataset_card.md for the full provenance statement.

This dataset covers a SINGLE anonymized engine component ("Component X"), not
several LRUs. To still produce a multi-row FMECA comparison, failure MODE rows
are defined as Spec_3 configuration groups (4 real categories) of the same
component -- i.e. "does the same failure mode behave differently by truck
configuration", which mirrors the strongest finding from the earlier two
example runs (config-dependent occurrence) but here it is the dataset's own
real structure, not an injected assumption.
"""
import json
import os
import numpy as np
import pandas as pd
from scipy import stats

ENC = "utf-8"
OUT = "outputs"
os.makedirs(OUT, exist_ok=True)

COUNTERS = ["171_0", "666_0", "427_0", "837_0", "309_0", "835_0", "370_0", "100_0"]
LOOKBACK_STEPS = 60      # detection lookback window, in time_step units
BASELINE_MIN_READOUTS = 4
Z_THRESH = 2.5
TAIL_READOUTS_FOR_SEVERITY = 3   # how many final readouts define "at-repair" severity window

print("loading tte / specifications ...")
tte = pd.read_csv("data_raw/train_tte.csv")
spec = pd.read_csv("data_raw/train_specifications.csv")
veh = tte.merge(spec, on="vehicle_id")

cleansing = {}

# ---------------------------------------------------------------------------
# 01 sync -- verify keys, check the irregular per-vehicle sampling the paper warns about
# ---------------------------------------------------------------------------
print("loading operational readouts (this is the big file) ...")
dtype_map = {"vehicle_id": "int32", "time_step": "float32"}
for c in COUNTERS:
    dtype_map[c] = "float32"
ro = pd.read_csv("data_raw/train_operational_readouts.csv", dtype=dtype_map,
                  usecols=["vehicle_id", "time_step"] + COUNTERS)
print("readouts loaded:", ro.shape)

n_vehicles_tte = veh.vehicle_id.nunique()
n_vehicles_ro = ro.vehicle_id.nunique()
readouts_per_vehicle = ro.groupby("vehicle_id").size()
cleansing["01_sync"] = {
    "operational_readouts_rows": int(len(ro)),
    "vehicles_in_readouts": int(n_vehicles_ro),
    "vehicles_in_tte": int(n_vehicles_tte),
    "vehicles_in_both": int(len(set(ro.vehicle_id) & set(veh.vehicle_id))),
    "readouts_per_vehicle_min": int(readouts_per_vehicle.min()),
    "readouts_per_vehicle_median": float(readouts_per_vehicle.median()),
    "readouts_per_vehicle_max": int(readouts_per_vehicle.max()),
    "note": "차량마다 판독 시점이 불규칙(논문 명시) — 공통 시간축이 아니라 차량별 time_step 순서로만 정렬 가능. 8개 누적 카운터만 사용(나머지 6개 히스토그램 변수는 계산량 축소를 위해 이번 예시에서 제외 — 02_domain_mapping.md에 명시).",
}

# ---------------------------------------------------------------------------
# 02 drift removal -- per-vehicle increment rate, then per-vehicle z vs own history
#    (baseline excludes the tail window used for severity/detection to avoid leakage)
# ---------------------------------------------------------------------------
ro = ro.sort_values(["vehicle_id", "time_step"]).reset_index(drop=True)
g = ro.groupby("vehicle_id", sort=False)
dt = g["time_step"].diff()
missing_before = ro[COUNTERS].isna().sum().to_dict()

for c in COUNTERS:
    dval = g[c].diff()
    rate = dval / dt.replace(0, np.nan)
    ro[f"{c}_rate"] = rate

rate_cols = [f"{c}_rate" for c in COUNTERS]
# negative rates are impossible for accumulative counters -> physically implausible, clip
n_negative = int((ro[rate_cols] < 0).sum().sum())
for rc in rate_cols:
    ro.loc[ro[rc] < 0, rc] = np.nan

# per-vehicle baseline mean/std of each rate channel, EXCLUDING each vehicle's own final readout
# (a simple leave-last-out baseline, cheap and avoids trivial contamination)
ro["rn"] = g.cumcount(ascending=False)  # 0 = last readout of that vehicle
base_mask = ro["rn"] >= 1
base_stats = ro.loc[base_mask].groupby("vehicle_id")[rate_cols].agg(["mean", "std"])
base_stats.columns = [f"{c}_{stat}" for c, stat in base_stats.columns]
ro = ro.merge(base_stats, on="vehicle_id", how="left")

for c in COUNTERS:
    m, s = f"{c}_rate_mean", f"{c}_rate_std"
    ro[f"{c}_z"] = (ro[f"{c}_rate"] - ro[m]) / ro[s].replace(0, np.nan)

z_cols = [f"{c}_z" for c in COUNTERS]
ro["anomaly_score"] = ro[z_cols].abs().mean(axis=1, skipna=True)
# signed mean z -> deviation DIRECTION (HAZOP guide word 판정용: 자기 기준선 대비 경고발생률이
# 증가(MORE) 하는지 감소(LESS) 하는지). abs 평균(anomaly_score)과 달리 부호를 살린다.
ro["anomaly_signed"] = ro[z_cols].mean(axis=1, skipna=True)
# 오차율(%): 채널별 (rate - 자기기준선평균)/자기기준선평균 x100 의 절대값 평균 -> z-score와
# 별개로, "기준 대비 몇 % 벗어났는가"를 직접 해석 가능한 단위로 표현한 값
pctdev_cols = []
for c in COUNTERS:
    m = f"{c}_rate_mean"
    pc = f"{c}_pctdev"
    pctdev_cols.append(pc)
    ro[pc] = (ro[f"{c}_rate"] - ro[m]) / ro[m].replace(0, np.nan) * 100
ro["anomaly_pctdev"] = ro[pctdev_cols].abs().mean(axis=1, skipna=True)

n_established = int(ro["anomaly_score"].notna().sum())
cleansing["02_drift_removal"] = {
    "method": "차량별 8개 누적 카운터의 증분율(rate) 계산 -> 해당 차량 자신의 과거 이력(마지막 판독 제외) 평균/표준편차로 z-정규화 -> 8채널 |z| 평균을 종합 이상지수(anomaly_score)로 사용. 부호를 살린 평균(anomaly_signed)은 HAZOP guide word(MORE/LESS) 판정에, 채널별 %이탈(anomaly_pctdev)은 오차율 정량화에 사용",
    "rows_total": int(len(ro)),
    "rows_with_anomaly_score": n_established,
    "negative_rate_values_clipped": n_negative,
}

# ---------------------------------------------------------------------------
# 03 segmentation -- TBF = length_of_study_time_step itself (already time-to-event by design)
# ---------------------------------------------------------------------------
cleansing["03_segmentation"] = {
    "note": "train_tte.csv가 이미 '구성품 장착 이후 경과 time_step'을 제공 -> 별도 구간분할 불필요(가장 단순한 real-world 사례: 좌측절단 없음, 관측시작=장착시점으로 기록됨).",
    "failure_events": int(veh.in_study_repair.sum()),
    "censored_vehicles": int((veh.in_study_repair == 0).sum()),
}

# ---------------------------------------------------------------------------
# 04 missing / outliers
# ---------------------------------------------------------------------------
missing_pct = {c: round(100 * missing_before[c] / len(ro), 3) for c in COUNTERS}
outlier_rows = int((ro["anomaly_score"] > 8).sum())
cleansing["04_missing_outliers"] = {
    "missing_pct_by_counter_column": missing_pct,
    "outlier_rule": "anomaly_score(8채널 평균 |z|) > 8 -> 극단치 플래그(제거 아님)",
    "outlier_rows_flagged": outlier_rows,
    "outlier_rows_pct": round(100 * outlier_rows / n_established, 4) if n_established else None,
}

# ---------------------------------------------------------------------------
# 05 code reconciliation
# ---------------------------------------------------------------------------
cleansing["05_code_reconciliation"] = {
    "vehicles_in_readouts_not_in_tte": int(len(set(ro.vehicle_id) - set(veh.vehicle_id))),
    "vehicles_in_tte_not_in_readouts": int(len(set(veh.vehicle_id) - set(ro.vehicle_id))),
    "duplicate_vehicle_timestep_rows": int(ro.duplicated(["vehicle_id", "time_step"]).sum()),
}

# ---------------------------------------------------------------------------
# 06 label definition
# ---------------------------------------------------------------------------
total_exposure = float(veh.length_of_study_time_step.sum())
cleansing["06_label_definition"] = {
    "positive_label": "train_tte.csv: in_study_repair=1 (Component X 교체/수리)",
    "n_positive_events": int(veh.in_study_repair.sum()),
    "n_total_exposure_time_steps": round(total_exposure, 1),
    "class_imbalance_per_1000_timesteps": round(1000 * veh.in_study_repair.sum() / total_exposure, 4),
}

with open(f"{OUT}/cleansing_stats.json", "w", encoding="utf-8") as f:
    json.dump(cleansing, f, indent=2, ensure_ascii=False, default=str)
print("cleansing:")
for k, v in cleansing.items():
    print(k, v)

# ---------------------------------------------------------------------------
# severity + detection per vehicle (needs full trajectory -> compute once)
# ---------------------------------------------------------------------------
print("computing per-vehicle severity/detection features ...")
last_readouts = ro[ro.rn < TAIL_READOUTS_FOR_SEVERITY].groupby("vehicle_id")[
    ["anomaly_score", "anomaly_signed", "anomaly_pctdev"]].mean()
last_readouts.columns = ["severity_anomaly_at_end", "severity_signed_at_end", "severity_pctdev_at_end"]

repaired_ids = set(veh.loc[veh.in_study_repair == 1, "vehicle_id"])
healthy_ids = set(veh.loc[veh.in_study_repair == 0, "vehicle_id"])
end_time = veh.set_index("vehicle_id")["length_of_study_time_step"]

flagged = ro[ro.anomaly_score > Z_THRESH][["vehicle_id", "time_step"]]
first_flag = flagged.groupby("vehicle_id")["time_step"].min()
first_flag.name = "first_flag_time_step"

feat = veh.set_index("vehicle_id").join(last_readouts).join(first_flag)
feat["lead_time"] = feat["length_of_study_time_step"] - feat["first_flag_time_step"]
feat["detected_within_lookback"] = feat["lead_time"].between(0, LOOKBACK_STEPS)

feat = feat.reset_index()
feat.to_csv(f"{OUT}/vehicle_features.csv", index=False, encoding=ENC)
print("vehicle_features:", feat.shape)

# ---------------------------------------------------------------------------
# O -- per Spec_3 group (the 4 "failure-mode rows")
# ---------------------------------------------------------------------------
GROUP_COL = "Spec_3"
o_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    k = int(gdf.in_study_repair.sum())
    exposure = float(gdf.length_of_study_time_step.sum())
    rate_1000 = k / exposure * 1000
    lo = stats.chi2.ppf(0.025, 2 * k) / 2 if k > 0 else 0.0
    hi = stats.chi2.ppf(0.975, 2 * (k + 1)) / 2
    o_rows.append(dict(group=grp, n_vehicles=int(len(gdf)), n_repairs=k, exposure_time_steps=round(exposure, 1),
                        rate_per_1000_timesteps=round(rate_1000, 5),
                        ci95_lo=round(lo / exposure * 1000, 5), ci95_hi=round(hi / exposure * 1000, 5)))
o_df = pd.DataFrame(o_rows).sort_values("rate_per_1000_timesteps", ascending=False)
rates = o_df.rate_per_1000_timesteps.values
log_rates = np.log10(rates)
pad = (log_rates.max() - log_rates.min()) * 0.05 or 0.1
edges = np.linspace(log_rates.min() - pad, log_rates.max() + pad, 11)
o_df["O_grade"] = np.digitize(log_rates, edges[1:-1]) + 1
o_df.to_csv(f"{OUT}/occurrence_stats.csv", index=False, encoding=ENC)
print("\nO by", GROUP_COL, ":\n", o_df)

# bonus real drill-down: Spec_2 extreme spread (documented in chat, recomputed here for the app)
s2_rows = []
for grp, gdf in feat.groupby("Spec_2"):
    if len(gdf) < 200:
        continue
    k = int(gdf.in_study_repair.sum())
    exposure = float(gdf.length_of_study_time_step.sum())
    s2_rows.append(dict(group=grp, n_vehicles=int(len(gdf)), n_repairs=k,
                         rate_per_1000=round(k / exposure * 1000, 5)))
s2_df = pd.DataFrame(s2_rows).sort_values("rate_per_1000", ascending=False)
s2_df.to_csv(f"{OUT}/spec2_case.csv", index=False, encoding=ENC)
top = s2_df.iloc[0]; bot = s2_df.iloc[-1]
spec2_case = dict(top_group=top.group, top_rate=float(top.rate_per_1000), top_n=int(top.n_vehicles),
                   bottom_group=bot.group, bottom_rate=float(bot.rate_per_1000), bottom_n=int(bot.n_vehicles),
                   ratio=round(float(top.rate_per_1000 / max(bot.rate_per_1000, 1e-9)), 2))
with open(f"{OUT}/spec2_case.json", "w", encoding="utf-8") as f:
    json.dump(spec2_case, f, ensure_ascii=False, indent=2)
print("\nSpec_2 extreme case:", spec2_case)

# ---------------------------------------------------------------------------
# S -- 주의: 이것은 "고장 결과의 심각도(안전/임무/비용 영향)"가 아니라 "고장 직전 신호
# 이탈 강도"에 대한 근사 대리지표(severity PROXY)다. SCANIA Component X 데이터셋에는
# 결과 심각도를 산출할 안전/가동중단/비용 기록이 전혀 없어 -> 진짜 심각도는 산출 불가.
# 대신 HAZOP guide word(이탈 방향) + 오차율(이탈 크기, %)로 구조화해 "무엇을 대리 측정
# 했는지"를 투명하게 남긴다.
#   - guide word 판정: 그룹 평균 부호부 z(anomaly_signed)가 양수면 MORE(경고발생률 평소
#     대비 증가), 음수면 LESS(평소 대비 감소/응답저하). 카운터가 누적값이라 원천적으로
#     REVERSE/NO 같은 다른 guide word는 이 데이터 구조에서 산출 불가.
#   - 오차율(%): 채널별 |rate - 자기기준선평균| / 자기기준선평균 x100 의 평균
# ---------------------------------------------------------------------------
s_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    rep = gdf[gdf.in_study_repair == 1]
    mean_anomaly = round(float(rep.severity_anomaly_at_end.mean()), 3) if len(rep) else None
    mean_signed = round(float(rep.severity_signed_at_end.mean()), 3) if len(rep) else None
    mean_pctdev = round(float(rep.severity_pctdev_at_end.mean()), 1) if len(rep) else None
    guide_word = ("MORE" if mean_signed is not None and mean_signed > 0
                  else "LESS" if mean_signed is not None else "산출불가")
    s_rows.append(dict(group=grp,
                        mean_severity_anomaly=mean_anomaly,
                        mean_signed_z=mean_signed,
                        mean_error_rate_pct=mean_pctdev,
                        hazop_guide_word=guide_word,
                        n_repairs_with_signal=int(rep.severity_anomaly_at_end.notna().sum())))
s_df = pd.DataFrame(s_rows)

def minmax(s):
    s = s.fillna(s.min())
    return (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0

s_df["S_score_raw"] = minmax(s_df.mean_severity_anomaly)
s_df["S_grade"] = (1 + 9 * s_df.S_score_raw).round().astype(int)
s_df.to_csv(f"{OUT}/severity_stats.csv", index=False, encoding=ENC)
print("\nS:\n", s_df)

# ---------------------------------------------------------------------------
# D -- detection: crossing-based lead time + chance-level comparison
# ---------------------------------------------------------------------------
# chance-level: among HEALTHY vehicles, what fraction have a flag anywhere in their last LOOKBACK_STEPS?
healthy_feat = feat[feat.in_study_repair == 0].copy()
healthy_feat["end_minus_flag"] = healthy_feat.length_of_study_time_step - healthy_feat.first_flag_time_step
healthy_feat["false_flag_near_end"] = healthy_feat["end_minus_flag"].between(0, LOOKBACK_STEPS)
null_p_by_group = healthy_feat.groupby(GROUP_COL)["false_flag_near_end"].mean()

d_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    rep = gdf[gdf.in_study_repair == 1]
    n = len(rep)
    n_det = int(rep.detected_within_lookback.sum())
    mean_lead = rep.loc[rep.detected_within_lookback, "lead_time"].mean()
    median_lead = rep.loc[rep.detected_within_lookback, "lead_time"].median()
    p_null = float(null_p_by_group.get(grp, healthy_feat.false_flag_near_end.mean()))
    pval = stats.binomtest(n_det, n, max(p_null, 1e-6), alternative="greater").pvalue if n else np.nan
    d_rows.append(dict(group=grp, n_repairs=n, n_detected=n_det,
                        detection_rate_pct=round(100 * n_det / n, 2) if n else None,
                        mean_lead_time=round(mean_lead, 1) if pd.notna(mean_lead) else None,
                        median_lead_time=round(median_lead, 1) if pd.notna(median_lead) else None,
                        expected_rate_if_random_pct=round(100 * p_null, 2),
                        binom_p=round(pval, 5) if pd.notna(pval) else None))
d_df = pd.DataFrame(d_rows)
norm_rate = d_df.detection_rate_pct.fillna(0) / 100
lead_capped = d_df.mean_lead_time.fillna(0).clip(upper=LOOKBACK_STEPS) / LOOKBACK_STEPS
detectability = 0.6 * norm_rate + 0.4 * lead_capped
d_df["D_grade"] = (10 - 9 * detectability).round().astype(int).clip(1, 10)
d_df.to_csv(f"{OUT}/detection_stats.csv", index=False, encoding=ENC)
print("\nD:\n", d_df)

# ---------------------------------------------------------------------------
# risk index + worksheet
# ---------------------------------------------------------------------------
risk = o_df[["group", "O_grade", "rate_per_1000_timesteps"]].merge(
    s_df[["group", "S_grade"]], on="group").merge(d_df[["group", "D_grade"]], on="group")
risk["RPN"] = risk.O_grade * risk.S_grade * risk.D_grade
risk["RI_weighted"] = (0.4 * risk.O_grade + 0.4 * risk.S_grade + 0.2 * risk.D_grade).round(2)
risk["rank_RPN"] = risk.RPN.rank(ascending=False, method="min").astype(int)
risk["rank_RI"] = risk.RI_weighted.rank(ascending=False, method="min").astype(int)
risk["rank_changed"] = risk.rank_RPN != risk.rank_RI
risk = risk.sort_values("rank_RPN")
risk.to_csv(f"{OUT}/risk_comparison.csv", index=False, encoding=ENC)
print("\nrisk:\n", risk)

ws = risk.merge(o_df[["group", "n_repairs", "exposure_time_steps", "ci95_lo", "ci95_hi"]], on="group")
ws = ws.merge(s_df[["group", "mean_severity_anomaly", "mean_signed_z", "mean_error_rate_pct", "hazop_guide_word"]], on="group")
ws = ws.merge(d_df[["group", "detection_rate_pct", "expected_rate_if_random_pct", "binom_p", "mean_lead_time"]], on="group")
ws["O_basis"] = ws.apply(lambda r: f"repairs={r.n_repairs}/{r.exposure_time_steps:.0f}time-steps -> {r.rate_per_1000_timesteps:.4f}/1000steps (95%CI {r.ci95_lo:.4f}-{r.ci95_hi:.4f}); train_tte.csv x train_specifications.csv({GROUP_COL})", axis=1)
ws["S_basis"] = ws.apply(lambda r: (
    f"[근사 심각도 — 실제 고장결과(안전/가동중단/비용) 기록이 데이터셋에 없어 산출 불가, "
    f"고장직전 신호이탈 강도를 대리지표로 사용] HAZOP guide word={r.hazop_guide_word}"
    f"(그룹평균 부호부z={r.mean_signed_z}) · 오차율(평균 |이탈률|)={r.mean_error_rate_pct}% · "
    f"수리 직전 최종 {TAIL_READOUTS_FOR_SEVERITY}개 판독의 평균 |이상지수|={r.mean_severity_anomaly}; "
    f"train_operational_readouts.csv 8개 누적카운터 증분율 z-평균"
), axis=1)
ws["D_basis"] = ws.apply(lambda r: f"탐지율={r.detection_rate_pct}% (우연수준 {r.expected_rate_if_random_pct}%, 이항검정 p={r.binom_p}), 평균 리드타임={r.mean_lead_time} time-step", axis=1)
ws_out = ws[["group", "n_repairs", "O_grade", "O_basis", "S_grade", "hazop_guide_word", "mean_error_rate_pct", "S_basis", "D_grade", "D_basis", "RPN", "rank_RPN", "RI_weighted", "rank_RI", "rank_changed"]]
ws_out = ws_out.rename(columns={"hazop_guide_word": "S_guideword", "mean_error_rate_pct": "S_error_rate_pct"})
ws_out = ws_out.rename(columns={"group": "failure_mode_group"})
ws_out.to_csv(f"{OUT}/fmeca_worksheet.csv", index=False, encoding=ENC)
print("\nworksheet:\n", ws_out.to_string())

print("\nDONE")
