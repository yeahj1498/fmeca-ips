# -*- coding: utf-8 -*-
"""
FMECA pipeline, generic across datasets -- see /DATASET_FORMAT.md.

Given a dataset folder with a config.yaml (asset events + time-series readouts
+ grouping attributes), computes the 6-step cleansing report, then O/S/D and
RPN/RI per group, and writes fmeca_worksheet.csv + supporting stats to
<dataset>/outputs/.

S (severity) is computed as an anomaly-magnitude PROXY, not true consequence
severity -- see the S section below and /doc/FMECA_IPS_공식정리.docx for why.

Usage: python 01_pipeline.py --dataset ../datasets/scania_component_x
"""
import argparse
import json
import numpy as np
import pandas as pd
from scipy import stats
from dataset_config import DatasetConfig

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", required=True, help="path to a dataset folder containing config.yaml")
args = ap.parse_args()
cfg = DatasetConfig(args.dataset)

ENC = "utf-8"
OUT = cfg.out_dir

ASSET = cfg.asset_id
EXPOSURE = cfg.exposure_time
LABEL = cfg.failure_label
RTIME = cfg.readout_time
COUNTERS = cfg.counters
GROUP_COL = cfg.group_col
BONUS_GROUP_COL = cfg.bonus_group_col

LOOKBACK_STEPS = cfg.param("lookback_steps", 60)
Z_THRESH = cfg.param("z_thresh", 2.5)
TAIL_READOUTS_FOR_SEVERITY = cfg.param("tail_readouts_for_severity", 3)
BONUS_GROUP_MIN_SIZE = cfg.param("bonus_group_min_size", 200)

print(f"[{cfg.dataset['name']}] loading events / groups ...")
events = pd.read_csv(cfg.files["events"])
groups_df = pd.read_csv(cfg.files["groups"])
veh = events.merge(groups_df, on=ASSET)

cleansing = {}

# ---------------------------------------------------------------------------
# 01 sync -- verify keys, check per-asset sampling
# ---------------------------------------------------------------------------
print("loading readouts (can be the big file) ...")
dtype_map = {ASSET: "int32", RTIME: "float32"}
for c in COUNTERS:
    dtype_map[c] = "float32"
ro = pd.read_csv(cfg.files["readouts"], dtype=dtype_map, usecols=[ASSET, RTIME] + COUNTERS)
print("readouts loaded:", ro.shape)

n_assets_events = veh[ASSET].nunique()
n_assets_ro = ro[ASSET].nunique()
readouts_per_asset = ro.groupby(ASSET).size()
cleansing["01_sync"] = {
    "readout_rows": int(len(ro)),
    "assets_in_readouts": int(n_assets_ro),
    "assets_in_events": int(n_assets_events),
    "assets_in_both": int(len(set(ro[ASSET]) & set(veh[ASSET]))),
    "readouts_per_asset_min": int(readouts_per_asset.min()),
    "readouts_per_asset_median": float(readouts_per_asset.median()),
    "readouts_per_asset_max": int(readouts_per_asset.max()),
}

# ---------------------------------------------------------------------------
# 02 drift removal -- per-asset increment rate, then per-asset z vs own history
#    (baseline excludes the tail window used for severity/detection to avoid leakage)
# ---------------------------------------------------------------------------
ro = ro.sort_values([ASSET, RTIME]).reset_index(drop=True)
g = ro.groupby(ASSET, sort=False)
dt = g[RTIME].diff()
missing_before = ro[COUNTERS].isna().sum().to_dict()

for c in COUNTERS:
    dval = g[c].diff()
    rate = dval / dt.replace(0, np.nan)
    ro[f"{c}_rate"] = rate

rate_cols = [f"{c}_rate" for c in COUNTERS]
n_negative = int((ro[rate_cols] < 0).sum().sum())
for rc in rate_cols:
    ro.loc[ro[rc] < 0, rc] = np.nan

ro["rn"] = g.cumcount(ascending=False)  # 0 = last readout of that asset
base_mask = ro["rn"] >= 1
base_stats = ro.loc[base_mask].groupby(ASSET)[rate_cols].agg(["mean", "std"])
base_stats.columns = [f"{c}_{stat}" for c, stat in base_stats.columns]
ro = ro.merge(base_stats, on=ASSET, how="left")

for c in COUNTERS:
    m, s = f"{c}_rate_mean", f"{c}_rate_std"
    ro[f"{c}_z"] = (ro[f"{c}_rate"] - ro[m]) / ro[s].replace(0, np.nan)

z_cols = [f"{c}_z" for c in COUNTERS]
ro["anomaly_score"] = ro[z_cols].abs().mean(axis=1, skipna=True)
ro["anomaly_signed"] = ro[z_cols].mean(axis=1, skipna=True)

pctdev_cols = []
for c in COUNTERS:
    m = f"{c}_rate_mean"
    pc = f"{c}_pctdev"
    pctdev_cols.append(pc)
    ro[pc] = (ro[f"{c}_rate"] - ro[m]) / ro[m].replace(0, np.nan) * 100
ro["anomaly_pctdev"] = ro[pctdev_cols].abs().mean(axis=1, skipna=True)

n_established = int(ro["anomaly_score"].notna().sum())
cleansing["02_drift_removal"] = {
    "method": f"자산별 {len(COUNTERS)}개 누적 카운터의 증분율(rate) 계산 -> 해당 자산 자신의 과거 이력(마지막 판독 제외) 평균/표준편차로 z-정규화 -> 채널 |z| 평균을 종합 이상지수(anomaly_score)로 사용. 부호를 살린 평균(anomaly_signed)은 HAZOP guide word(MORE/LESS) 판정에, 채널별 %이탈(anomaly_pctdev)은 오차율 정량화에 사용",
    "rows_total": int(len(ro)),
    "rows_with_anomaly_score": n_established,
    "negative_rate_values_clipped": n_negative,
}

# ---------------------------------------------------------------------------
# 03 segmentation
# ---------------------------------------------------------------------------
cleansing["03_segmentation"] = {
    "note": f"{cfg.raw['files']['events']}가 이미 노출시간({EXPOSURE})을 제공 -> 별도 구간분할 불필요.",
    "failure_events": int(veh[LABEL].sum()),
    "censored_assets": int((veh[LABEL] == 0).sum()),
}

# ---------------------------------------------------------------------------
# 04 missing / outliers
# ---------------------------------------------------------------------------
missing_pct = {c: round(100 * missing_before[c] / len(ro), 3) for c in COUNTERS}
outlier_rows = int((ro["anomaly_score"] > 8).sum())
cleansing["04_missing_outliers"] = {
    "missing_pct_by_counter_column": missing_pct,
    "outlier_rule": "anomaly_score(채널 평균 |z|) > 8 -> 극단치 플래그(제거 아님)",
    "outlier_rows_flagged": outlier_rows,
    "outlier_rows_pct": round(100 * outlier_rows / n_established, 4) if n_established else None,
}

# ---------------------------------------------------------------------------
# 05 code reconciliation
# ---------------------------------------------------------------------------
cleansing["05_code_reconciliation"] = {
    "assets_in_readouts_not_in_events": int(len(set(ro[ASSET]) - set(veh[ASSET]))),
    "assets_in_events_not_in_readouts": int(len(set(veh[ASSET]) - set(ro[ASSET]))),
    "duplicate_asset_time_rows": int(ro.duplicated([ASSET, RTIME]).sum()),
}

# ---------------------------------------------------------------------------
# 06 label definition
# ---------------------------------------------------------------------------
total_exposure = float(veh[EXPOSURE].sum())
cleansing["06_label_definition"] = {
    "positive_label": f"{cfg.raw['files']['events']}: {LABEL}=1",
    "n_positive_events": int(veh[LABEL].sum()),
    "n_total_exposure_time_steps": round(total_exposure, 1),
    "class_imbalance_per_1000_timesteps": round(1000 * veh[LABEL].sum() / total_exposure, 4),
}

with open(f"{OUT}/cleansing_stats.json", "w", encoding="utf-8") as f:
    json.dump(cleansing, f, indent=2, ensure_ascii=False, default=str)
print("cleansing:")
for k, v in cleansing.items():
    print(k, v)

# ---------------------------------------------------------------------------
# severity + detection per asset (needs full trajectory -> compute once)
# ---------------------------------------------------------------------------
print("computing per-asset severity/detection features ...")
last_readouts = ro[ro.rn < TAIL_READOUTS_FOR_SEVERITY].groupby(ASSET)[
    ["anomaly_score", "anomaly_signed", "anomaly_pctdev"]].mean()
last_readouts.columns = ["severity_anomaly_at_end", "severity_signed_at_end", "severity_pctdev_at_end"]

flagged = ro[ro.anomaly_score > Z_THRESH][[ASSET, RTIME]]
first_flag = flagged.groupby(ASSET)[RTIME].min()
first_flag.name = "first_flag_time_step"

feat = veh.set_index(ASSET).join(last_readouts).join(first_flag)
feat["lead_time"] = feat[EXPOSURE] - feat["first_flag_time_step"]
feat["detected_within_lookback"] = feat["lead_time"].between(0, LOOKBACK_STEPS)

feat = feat.reset_index()
feat.to_csv(f"{OUT}/vehicle_features.csv", index=False, encoding=ENC)
print("asset_features:", feat.shape)

# ---------------------------------------------------------------------------
# O -- per group_col group (the FMECA "failure mode" rows)
# ---------------------------------------------------------------------------
o_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    k = int(gdf[LABEL].sum())
    exposure = float(gdf[EXPOSURE].sum())
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

# bonus real drill-down: an optional secondary grouping's extreme spread
if BONUS_GROUP_COL and BONUS_GROUP_COL in feat.columns:
    s2_rows = []
    for grp, gdf in feat.groupby(BONUS_GROUP_COL):
        if len(gdf) < BONUS_GROUP_MIN_SIZE:
            continue
        k = int(gdf[LABEL].sum())
        exposure = float(gdf[EXPOSURE].sum())
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
    print("\nBonus group extreme case:", spec2_case)
else:
    spec2_case = None
    print("\n(no bonus_group_col configured -- skipping bonus drill-down)")

# ---------------------------------------------------------------------------
# S -- 주의: 이것은 "고장 결과의 심각도(안전/임무/비용 영향)"가 아니라 "고장 직전 신호
# 이탈 강도"에 대한 근사 대리지표(severity PROXY)다. 결과 심각도를 산출할 기록이 데이터셋에
# 없다면(대부분의 공개 계측 데이터셋이 그렇다) 진짜 심각도는 산출 불가.
# 대신 HAZOP guide word(이탈 방향) + 오차율(이탈 크기, %)로 구조화해 "무엇을 대리 측정
# 했는지"를 투명하게 남긴다.
#   - guide word 판정: 그룹 평균 부호부 z(anomaly_signed)가 양수면 MORE(계측값 평소
#     대비 증가), 음수면 LESS(평소 대비 감소/응답저하). 카운터가 누적값이라 원천적으로
#     REVERSE/NO 같은 다른 guide word는 이 데이터 구조에서 산출 불가.
#   - 오차율(%): 채널별 |rate - 자기기준선평균| / 자기기준선평균 x100 의 평균
# ---------------------------------------------------------------------------
s_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    rep = gdf[gdf[LABEL] == 1]
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
healthy_feat = feat[feat[LABEL] == 0].copy()
healthy_feat["end_minus_flag"] = healthy_feat[EXPOSURE] - healthy_feat["first_flag_time_step"]
healthy_feat["false_flag_near_end"] = healthy_feat["end_minus_flag"].between(0, LOOKBACK_STEPS)
null_p_by_group = healthy_feat.groupby(GROUP_COL)["false_flag_near_end"].mean()

d_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    rep = gdf[gdf[LABEL] == 1]
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
ws["O_basis"] = ws.apply(lambda r: f"repairs={r.n_repairs}/{r.exposure_time_steps:.0f}time-steps -> {r.rate_per_1000_timesteps:.4f}/1000steps (95%CI {r.ci95_lo:.4f}-{r.ci95_hi:.4f}); {GROUP_COL}", axis=1)
ws["S_basis"] = ws.apply(lambda r: (
    f"[근사 심각도 — 실제 고장결과(안전/가동중단/비용) 기록이 데이터셋에 없어 산출 불가, "
    f"고장직전 신호이탈 강도를 대리지표로 사용] HAZOP guide word={r.hazop_guide_word}"
    f"(그룹평균 부호부z={r.mean_signed_z}) · 오차율(평균 |이탈률|)={r.mean_error_rate_pct}% · "
    f"수리 직전 최종 {TAIL_READOUTS_FOR_SEVERITY}개 판독의 평균 |이상지수|={r.mean_severity_anomaly}; "
    f"{len(COUNTERS)}개 누적카운터 증분율 z-평균"
), axis=1)
ws["D_basis"] = ws.apply(lambda r: f"탐지율={r.detection_rate_pct}% (우연수준 {r.expected_rate_if_random_pct}%, 이항검정 p={r.binom_p}), 평균 리드타임={r.mean_lead_time} time-step", axis=1)
ws_out = ws[["group", "n_repairs", "O_grade", "O_basis", "S_grade", "hazop_guide_word", "mean_error_rate_pct", "S_basis", "D_grade", "D_basis", "RPN", "rank_RPN", "RI_weighted", "rank_RI", "rank_changed"]]
ws_out = ws_out.rename(columns={"hazop_guide_word": "S_guideword", "mean_error_rate_pct": "S_error_rate_pct"})
ws_out = ws_out.rename(columns={"group": "failure_mode_group"})
ws_out.to_csv(f"{OUT}/fmeca_worksheet.csv", index=False, encoding=ENC)
print("\nworksheet:\n", ws_out.to_string())

print("\nDONE ->", OUT)
