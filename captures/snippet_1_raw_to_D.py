# scripts/01_pipeline.py -- 원시데이터(raw telemetry) -> 열화추세 -> D(검출도)
# (원본 68~109행 + 243~273행, 두 구간 사이는 O/S 산출 -- 생략)

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
