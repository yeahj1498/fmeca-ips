/**
 * IPS 연계 코드 (클라이언트 사이드) -- app/index.html에서 추출
 *
 * FMECA(O·S·D)가 RCM·LORA·IETM·보급소요·ECP 5개 요소로 어떻게 퍼지는지,
 * 그리고 설계개선(ECP)이 적용됐다고 가정했을 때 그 5개 요소가 "같은 새
 * O'/D' 값을 공유하며" 함께 재계산되는지를 보여주는 부분만 뽑았다.
 *
 * 원본(정적) 판정 로직은 scripts/02_lifecycle.py에 있고, 이 파일은 그 판정
 * 규칙을 브라우저에서 실시간으로 재계산하기 위해 그대로 옮겨 쓴 것이다 --
 * 두 파일의 임계값(O>=8, S>=5, significant && detectRate>=50 등)은 반드시
 * 같은 값을 유지해야 한다.
 *
 * 입력 데이터: app_data/fmeca.json (modes[].O_grade/S_grade/D_grade/
 * significant/detection_rate_pct/mean_lead_time 등)과
 * app_data/lifecycle.json (rows[].rcm_strategy/ecp_triggers 등).
 */

// ---------------------------------------------------------------------------
// 04 RCM -- 상태기반정비(CBM) 가능 여부 판정
// ---------------------------------------------------------------------------
function deriveRCM(O, S, D, significant, detectRatePct) {
  if (significant && detectRatePct >= 50) {
    return { strategy: "상태기반정비(CBM)", pill: "ok" };
  }
  if (S >= 5) return { strategy: "시간기준 예방정비(Hard-Time)", pill: "gap" };
  return { strategy: "사후정비(Run-to-Failure)", pill: "crit" };
}

// ---------------------------------------------------------------------------
// 05 LORA -- 수리수준(야전/창정비) 판정. scripts/02_lifecycle.py와 동일 임계값(O>=8)
// ---------------------------------------------------------------------------
function deriveLORA(O) {
  if (O >= 8) return { level: "창정비 우선순위 상향 + 예비품 전진배치", pill: "gap" };
  return { level: "표준 2-Level (야전 LRU교환 + 창정비 모듈수리)", pill: "neutral" };
}

// ---------------------------------------------------------------------------
// 07 IETM -- 사전점검 SLA를 정의할 근거(통계적 유의성 + 리드타임)가 있는지
// ---------------------------------------------------------------------------
function deriveIETM(significant, leadTimeH) {
  if (significant && leadTimeH) {
    return { proc: "사전점검 SLA 정의", sla: Math.round(leadTimeH * 0.5 * 10) / 10, pill: "ok" };
  }
  return { proc: "정기점검 강화 (사전 SLA 없음)", sla: null, pill: "neutral" };
}

// ---------------------------------------------------------------------------
// 08 ECP -- 개선 적용 후에도 설계개선 트리거가 남아있는지 재평가
// (RPN 전체 1위 여부는 이 그룹 하나만으로는 재확인할 수 없어 O=10, 비유의성만 재검사)
// ---------------------------------------------------------------------------
function deriveECP(O2, sig2) {
  const stillTrig = [];
  if (O2 >= 10) stillTrig.push("발생도 여전히 최고등급");
  if (!sig2) stillTrig.push("이상신호 여전히 비유의");
  return { resolved: stillTrig.length === 0, remaining: stillTrig };
}

// ---------------------------------------------------------------------------
// 설계개선(ECP) 적용 가정 -- 등급 변화폭 자체는 실측이 아니라 이 시뮬레이션의
// 가정치. RPN·RI·RCM·LORA·IETM·보급소요는 이 가정된 새 등급으로부터
// "실제 산식"으로 재계산된다 (여기서부터가 06 보급소요 / 09 피드백 루프의 핵심).
// ---------------------------------------------------------------------------
const O_TRIGGER_RE = /(RPN 전체 1위|발생도 최고등급)/;
const D_TRIGGER_RE = /(우연 수준과 통계적으로 구분 안 됨)/;
const ASSUMED_O_GRADE_DELTA = 2;      // 근본설계 개선 가정 -> O등급 2단계 하향
const ASSUMED_RATE_FACTOR = 0.60;     // 위와 짝을 이루는 발생률 감소 가정(약 40% 감소) -- 보급소요 재계산에 직접 사용
const ASSUMED_D_GRADE_DELTA = 3;      // 진단 알고리즘/센서 고도화 가정 -> D등급 3단계 개선
const ASSUMED_NEW_DETECT_RATE = 60;   // 위 개선이 적용됐다고 가정할 때의 탐지율(%)

/**
 * FMECA 결과(m)와 lifecycle 산출값(r)을 입력받아, ECP를 적용했다고 가정했을 때
 * RCM·LORA·IETM·보급소요·ECP 5개 요소가 어떻게 바뀌는지 한 번에 재계산한다.
 * 이게 바로 "다른 요소랑도 연계하는 부분" -- RCM 하나만이 아니라
 * 같은 O2/D2/sig2를 5개 함수 모두에 동일하게 넘긴다.
 */
function computeIntervention(m, r) {
  const applyO = O_TRIGGER_RE.test(r.ecp_triggers.join(" "));
  const applyD = D_TRIGGER_RE.test(r.ecp_triggers.join(" "));

  // -- 새 O'/D'/유의성 (설계개선 가정 적용)
  const O2 = applyO ? Math.max(1, m.O_grade - ASSUMED_O_GRADE_DELTA) : m.O_grade;
  const D2 = applyD ? Math.max(1, m.D_grade - ASSUMED_D_GRADE_DELTA) : m.D_grade;
  const sig2 = applyD ? true : m.significant;
  const rate2Pct = applyD ? ASSUMED_NEW_DETECT_RATE : m.detection_rate_pct;
  const S2 = m.S_grade; // 설계/검출 개선이 심각도 자체를 바꾼다고 가정하지 않음

  // -- 위험지수 재계산 (실제 산식, 가정 없음)
  const RPN2 = O2 * S2 * D2;
  const RI2 = +(0.4 * O2 + 0.4 * S2 + 0.2 * D2).toFixed(2);

  // -- 06 보급소요: 발생률에 동일 비율(ASSUMED_RATE_FACTOR)을 적용해 재계산
  const rate2 = applyO ? +(m.rate_per_1000 * ASSUMED_RATE_FACTOR).toFixed(4) : m.rate_per_1000;

  // -- 04 RCM: 개선 전/후 동일 규칙으로 재판정
  const rcmBefore = deriveRCM(m.O_grade, m.S_grade, m.D_grade, m.significant, m.detection_rate_pct || 0);
  const rcmAfter = deriveRCM(O2, S2, D2, sig2, rate2Pct || 0);

  // -- 05/07/08 LORA·IETM·ECP: RCM과 동일한 O2/D2/sig2를 공유해 재판정
  const loraBefore = deriveLORA(m.O_grade);
  const loraAfter = deriveLORA(O2);
  const ietmBefore = deriveIETM(m.significant, m.mean_lead_time);
  const ietmAfter = deriveIETM(sig2, m.mean_lead_time);
  const ecpAfter = deriveECP(O2, sig2);

  return {
    applyO, applyD, O2, D2, S2, RPN2, RI2, rate2,
    rcmBefore, rcmAfter, loraBefore, loraAfter, ietmBefore, ietmAfter, ecpAfter,
  };
}

// Node/브라우저 양쪽에서 재사용할 수 있게 내보내기 (module 환경이면)
if (typeof module !== "undefined") {
  module.exports = { deriveRCM, deriveLORA, deriveIETM, deriveECP, computeIntervention };
}
