# -*- coding: utf-8 -*-
"""
FMECA -> RCM -> LORA -> 보급소요 -> IETM 연계 -> 설계개선(ECP), applied to the
REAL SCANIA Component X results (outputs/fmeca_worksheet.csv etc). Rows are the
four Spec_3 configuration groups of the SAME real engine component. All
assumption parameters (repair complexity, lead time, unit cost) below are
author-defined illustrative values, clearly separated from the real O/S/D
numbers computed from the dataset.
"""
import json
import math
import pandas as pd

ENC = "utf-8"
OUT = "outputs"

ws = pd.read_csv(f"{OUT}/fmeca_worksheet.csv", encoding=ENC)
occ = pd.read_csv(f"{OUT}/occurrence_stats.csv", encoding=ENC)
sev = pd.read_csv(f"{OUT}/severity_stats.csv", encoding=ENC)
det = pd.read_csv(f"{OUT}/detection_stats.csv", encoding=ENC)
feat = pd.read_csv(f"{OUT}/vehicle_features.csv", encoding=ENC)

GROUP_LABEL = {"Cat0": "형상A(Spec_3=Cat0)", "Cat1": "형상B(Spec_3=Cat1)",
               "Cat2": "형상C(Spec_3=Cat2)", "Cat3": "형상D(Spec_3=Cat3)"}

# ---------------------------------------------------------------------------
# assumption parameters (author-defined, NOT from the dataset)
# ---------------------------------------------------------------------------
ASSUMED_LEAD_DAYS = 75          # 정밀부품 국외조달 가정 (엔진계통)
ASSUMED_UNIT_COST_KRW = 28_000_000
ASSUMED_REPAIR_COMPLEXITY = "중상"   # 엔진계통 구성품 공통 가정
ASSUMED_FLEET_SIZE = 400        # 이 방법론을 적용할 가상 군 차량 정비단 규모(가정)
ASSUMED_DAILY_OP_TIMESTEPS = 0.7  # 가상 함대의 time_step/day 환산 가정(문서화된 가정치일 뿐, 데이터셋 자체 단위 아님)
Z_SERVICE_95 = 1.645

rows = []
for _, r in ws.iterrows():
    grp = r.failure_mode_group
    label = GROUP_LABEL.get(grp, grp)
    o = int(r.O_grade); s = int(r.S_grade); d = int(r.D_grade)
    detr = det.loc[det.group == grp].iloc[0]
    occr = occ.loc[occ.group == grp].iloc[0]

    significant = bool(pd.notna(detr.binom_p) and detr.binom_p < 0.05)
    detect_rate = detr.detection_rate_pct if pd.notna(detr.detection_rate_pct) else 0

    # RCM
    if significant and detect_rate >= 50:
        strategy = "상태기반정비(CBM)"
        priority = "우선순위 높음(모니터링 강화)" if o >= 7 else "표준 모니터링 주기"
        rcm_reason = f"이상지수 임계값 교차가 우연 수준 대비 통계적으로 유의(p={detr.binom_p:.4f}) + 탐지율 {detect_rate:.1f}% → 상태감시로 개입 가능"
    else:
        if significant:
            signal_clause = f"조기신호는 통계적으로 유의(p={detr.binom_p:.4f})하지만 탐지율이 {detect_rate:.1f}%로 낮아 상태감시만으로는 불충분"
        else:
            signal_clause = f"조기신호가 우연 수준과 통계적으로 구분 안 됨(p={detr.binom_p:.4f})"
        if s >= 5:
            strategy = "시간기준 예방정비(Hard-Time)"
            rcm_reason = f"{signal_clause} — 심각도 S={s} 높음 → 정기 교체 검토"
        else:
            strategy = "사후정비(Run-to-Failure)"
            rcm_reason = f"{signal_clause} + 낮은 심각도(S={s}) → 고장 후 조치가 경제적"
        priority = "표준"

    # LORA (동일 물리 구성품이므로 복잡도는 고정, 위험도에 따라 우선순위만 차등)
    if o >= 8:
        lora = "창정비 우선순위 상향 + 예비품 전진배치"
        lora_reason = f"이 형상군의 발생률이 함대 상위권(O={o}) → 창정비 대기열 우선순위 상향, 야전 교환용 예비품을 부대 인근에 전진배치"
    else:
        lora = "표준 2-Level(야전 LRU교환 + 창정비 모듈수리)"
        lora_reason = f"발생률이 상대적으로 낮음(O={o}) → 표준 정비체계로 충분"

    # 보급소요 (가상 함대 규모로 환산 — 실측 O를 가정 함대에 적용하는 예시)
    fleet_n_this_group = ASSUMED_FLEET_SIZE / 4  # 4개 형상군에 균등 배분 가정
    annual_timesteps = ASSUMED_DAILY_OP_TIMESTEPS * 365
    annual_demand = occr.rate_per_1000_timesteps / 1000 * fleet_n_this_group * annual_timesteps
    lead_time_demand = annual_demand * (ASSUMED_LEAD_DAYS / 365)
    safety_stock = Z_SERVICE_95 * math.sqrt(max(lead_time_demand, 0.01))
    reorder_point = lead_time_demand + safety_stock
    annual_cost = annual_demand * ASSUMED_UNIT_COST_KRW

    # IETM 연계 (이상지수 임계교차를 가상 경고코드로 취급)
    warn_code = f"AX-{grp}"
    if significant and pd.notna(detr.mean_lead_time):
        sla = round(detr.mean_lead_time * 0.5, 1)
        ietm_note = f"이상지수 임계교차({warn_code}) 후 {sla} time-step 이내 점검 착수 (평균 리드타임 {detr.mean_lead_time}의 절반을 SLA로 설정)"
        ietm_proc = f"IETM-CX-{grp}-01 (이상신호 대응 점검절차)"
    else:
        sla = None
        ietm_note = "유의한 사전 이상신호 없음 — 사전점검 절차 정의 근거 부족, 정기점검 주기 강화로 대체"
        ietm_proc = f"IETM-CX-{grp}-02 (정기점검 강화 절차)"

    # 설계개선(ECP)
    triggers = []
    if int(r.rank_RPN) == 1:
        triggers.append(f"RPN 전체 1위(RPN={int(r.RPN)}) → 이 형상군 구성품 우선 재설계/대체부품 검토")
    if o == 10:
        triggers.append(f"발생도 최고등급(O=10) → 근본 설계원인 분석 필요")
    if not significant:
        triggers.append(f"이상지수 조기신호가 우연 수준과 통계적으로 구분 안 됨(p={detr.binom_p}) → 진단 알고리즘/센서 고도화 필요")

    rows.append(dict(
        group=grp, label=label, rcm_strategy=strategy, rcm_priority=priority, rcm_reason=rcm_reason,
        significant_detection=significant, lora_level=lora, lora_reason=lora_reason,
        repair_complexity=ASSUMED_REPAIR_COMPLEXITY,
        annual_demand_units=round(annual_demand, 2), lead_days=ASSUMED_LEAD_DAYS,
        lead_time_demand=round(lead_time_demand, 2), safety_stock=round(safety_stock, 2),
        reorder_point=round(reorder_point, 2), annual_cost_krw=round(annual_cost, 0),
        unit_cost_krw=ASSUMED_UNIT_COST_KRW,
        ietm_procedure=ietm_proc, ietm_sla=sla, ietm_note=ietm_note, warn_code=warn_code,
        ecp_triggers=triggers, ecp_candidate=len(triggers) > 0,
    ))

lifecycle = pd.DataFrame(rows)
lifecycle.to_csv(f"{OUT}/lifecycle.csv", index=False, encoding=ENC)
with open(f"{OUT}/lifecycle.json", "w", encoding="utf-8") as f:
    json.dump(dict(
        assumptions=dict(lead_days=ASSUMED_LEAD_DAYS, unit_cost_krw=ASSUMED_UNIT_COST_KRW,
                          repair_complexity=ASSUMED_REPAIR_COMPLEXITY, assumed_fleet_size=ASSUMED_FLEET_SIZE,
                          service_level="95%(z=1.645)", note="보급소요 파라미터는 전량 가정치 -- 실측이 아님. 실측인 것은 O/S/D 등급 산출 원천 데이터."),
        rows=rows,
    ), f, ensure_ascii=False, indent=2)

print(lifecycle[["group", "rcm_strategy", "lora_level", "annual_demand_units", "reorder_point", "ecp_candidate"]].to_string())
