# scripts/01_pipeline.py -- O / S / D 산출 공식 (원본 181~273행)

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

# ---------------------------------------------------------------------------
# S -- severity surrogate: mean anomaly magnitude in final readouts, by group
# ---------------------------------------------------------------------------
s_rows = []
for grp, gdf in feat.groupby(GROUP_COL):
    rep = gdf[gdf.in_study_repair == 1]
    s_rows.append(dict(group=grp,
                        mean_severity_anomaly=round(float(rep.severity_anomaly_at_end.mean()), 3) if len(rep) else None,
                        n_repairs_with_signal=int(rep.severity_anomaly_at_end.notna().sum())))
s_df = pd.DataFrame(s_rows)

def minmax(s):
    s = s.fillna(s.min())
    return (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0

s_df["S_score_raw"] = minmax(s_df.mean_severity_anomaly)
s_df["S_grade"] = (1 + 9 * s_df.S_score_raw).round().astype(int)

# ---------------------------------------------------------------------------
# D -- detection: crossing-based lead time + chance-level comparison
# ---------------------------------------------------------------------------
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
    p_null = float(null_p_by_group.get(grp, healthy_feat.false_flag_near_end.mean()))
    pval = stats.binomtest(n_det, n, max(p_null, 1e-6), alternative="greater").pvalue if n else np.nan
    d_rows.append(dict(group=grp, n_repairs=n, n_detected=n_det,
                        detection_rate_pct=round(100 * n_det / n, 2) if n else None,
                        mean_lead_time=round(mean_lead, 1) if pd.notna(mean_lead) else None,
                        expected_rate_if_random_pct=round(100 * p_null, 2),
                        binom_p=round(pval, 5) if pd.notna(pval) else None))
d_df = pd.DataFrame(d_rows)
norm_rate = d_df.detection_rate_pct.fillna(0) / 100
lead_capped = d_df.mean_lead_time.fillna(0).clip(upper=LOOKBACK_STEPS) / LOOKBACK_STEPS
detectability = 0.6 * norm_rate + 0.4 * lead_capped
d_df["D_grade"] = (10 - 9 * detectability).round().astype(int).clip(1, 10)

# ---------------------------------------------------------------------------
# risk index (RPN vs weighted index)
# ---------------------------------------------------------------------------
risk = o_df[["group", "O_grade"]].merge(s_df[["group", "S_grade"]], on="group").merge(d_df[["group", "D_grade"]], on="group")
risk["RPN"] = risk.O_grade * risk.S_grade * risk.D_grade
risk["RI_weighted"] = (0.4 * risk.O_grade + 0.4 * risk.S_grade + 0.2 * risk.D_grade).round(2)
