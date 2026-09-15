# -*- coding: utf-8 -*-
"""표준 프로그래밍 플로우차트(시작/입출력/처리/판단 도형) 생성기 -- v3.
scripts/run_pipeline.py가 실제로 실행하는 4개 스크립트(01_pipeline -> 02_lifecycle
-> 04_export_transform_sample -> 03_export_app_data)의 진짜 제어흐름을 그린다.
config.yaml의 failure_modes 리스트를 도는 바깥 루프 안에, 각 모드의 그룹을 도는
중첩 루프가 있다 -- 이게 이전 버전과의 핵심 차이(고장모드 다중화 이후의 실제 구조).
모든 2지 분기는 다이아몬드 -> 좌(예)/우(아니오) 박스 -> 아래 한 점으로 합류하는
대칭 V-병합 패턴을 쓴다. RCM만 3지 분기라 예외적으로 확장한다."""

SPINE_X = 520
W = 1560

INK = "#1a2422"
DIM = "#55635e"
ACCENT = "#2c6b73"
LINE = "#aab5af"
GREEN = "#3c7a4f"
RED = "#a8342c"

parts = []
n_counter = 0


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def arrow(x1, y1, x2, y2, ah=True):
    m = 'marker-end="url(#ah)"' if ah else ""
    parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{INK}" stroke-width="1.8" fill="none" {m}/>')


def elbow(pts, ah=True, color=INK, dash=None):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    m = 'marker-end="url(#ah)"' if ah else ""
    dd = f'stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<path d="{d}" stroke="{color}" stroke-width="1.8" fill="none" {m} {dd}/>')


def label(x, y_, text, size=11, color=DIM, anchor="middle", bold=False, italic=False):
    w = 'font-weight="700"' if bold else ""
    it = 'font-style="italic"' if italic else ""
    parts.append(f'<text x="{x}" y="{y_}" text-anchor="{anchor}" font-size="{size}" fill="{color}" {w} {it}>{esc(text)}</text>')


def multiline(cx, cy, lines, size=12.2, color=INK, bold=False, mono_from=None, lh=16):
    n = len(lines)
    start = cy - (n - 1) * lh / 2 + 4
    for i, ln in enumerate(lines):
        mono = mono_from is not None and i >= mono_from
        fam = 'font-family="Consolas,monospace"' if mono else ""
        sz = size - 1 if mono else size
        w = 'font-weight="700"' if bold else ""
        parts.append(f'<text x="{cx}" y="{start + i*lh}" text-anchor="middle" font-size="{sz}" fill="{color}" {fam} {w}>{esc(ln)}</text>')


def step_num():
    global n_counter
    n_counter += 1
    return n_counter


def badge(cx, top_y, num):
    parts.append(f'<circle cx="{cx-2}" cy="{top_y-15}" r="12.5" fill="#ffffff" stroke="{LINE}" stroke-width="1"/>')
    label(cx-2, top_y-10.5, str(num), size=11, color=ACCENT, bold=True)


def terminator(cx, cy, text, w=210, h=48):
    x, yt = cx - w/2, cy - h/2
    parts.append(f'<rect x="{x}" y="{yt}" width="{w}" height="{h}" rx="{h/2}" fill="#eef1ef" stroke="{INK}" stroke-width="1.6"/>')
    label(cx, cy+5, text, size=13.5, color=INK, bold=True)
    return h


def io_box(cx, cy, lines, w=420, h=64):
    x, yt = cx - w/2, cy - h/2
    skew = 22
    pts = f"{x+skew},{yt} {x+w},{yt} {x+w-skew},{yt+h} {x},{yt+h}"
    parts.append(f'<polygon points="{pts}" fill="#eeeeee" stroke="{ACCENT}" stroke-width="1.4"/>')
    multiline(cx, cy, lines, size=11.8, bold=True)
    return h


def process(cx, cy, lines, w=420, h=None, mono_from=None):
    n = len(lines)
    if h is None:
        h = max(50, 26 + n * 18)
    x, yt = cx - w/2, cy - h/2
    parts.append(f'<rect x="{x}" y="{yt}" width="{w}" height="{h}" fill="#ffffff" stroke="{LINE}" stroke-width="1.3"/>')
    multiline(cx, cy, lines, size=12, mono_from=mono_from)
    return h


def decision(cx, cy, lines, w=320, h=100):
    x, yt = cx - w/2, cy - h/2
    pts = f"{cx},{yt} {cx+w/2},{cy} {cx},{yt+h} {cx-w/2},{cy}"
    parts.append(f'<polygon points="{pts}" fill="#f7ebdd" stroke="#b5651d" stroke-width="1.5"/>')
    multiline(cx, cy, lines, size=11.5, color="#8a4a15", bold=True, lh=15)
    return h


# ---------------------------------------------------------------------------
def flow_down(cy, gap=36):
    """중심선을 따라 화살표 하나 그리고 다음 중심 y 반환."""
    ny = cy + gap
    arrow(SPINE_X, cy, SPINE_X, ny)
    return ny


def decision_pair(cy_top, dtext, yes_lines, no_lines, half_w=170, box_dx=250, box_w=270, box_h=58,
                   gap1=44, gap2=40, d_h=100):
    """대칭 V-병합: 다이아몬드 -> 좌(예)/우(아니오) 박스 -> 한 점으로 합류.
       return: 합류 후 중심 y"""
    d_h_ = decision(SPINE_X, cy_top, dtext, w=2*half_w, h=d_h)
    badge(SPINE_X, cy_top - d_h_/2, step_num())
    left_v = (SPINE_X - half_w, cy_top)
    right_v = (SPINE_X + half_w, cy_top)
    box_cy = cy_top + d_h_/2 + gap1 + box_h/2
    yes_x = SPINE_X - box_dx
    no_x = SPINE_X + box_dx
    elbow([left_v, (yes_x, box_cy - box_h/2)])
    elbow([right_v, (no_x, box_cy - box_h/2)])
    label((left_v[0]+yes_x)/2 - 6, (left_v[1]+box_cy-box_h/2)/2 - 6, "예", size=12, color=GREEN, bold=True, anchor="end")
    label((right_v[0]+no_x)/2 + 6, (right_v[1]+box_cy-box_h/2)/2 - 6, "아니오", size=12, color=RED, bold=True, anchor="start")
    process(yes_x, box_cy, yes_lines, w=box_w, h=box_h)
    process(no_x, box_cy, no_lines, w=box_w, h=box_h)
    merge_y = box_cy + box_h/2 + gap2
    elbow([(yes_x, box_cy+box_h/2), (SPINE_X, merge_y)])
    elbow([(no_x, box_cy+box_h/2), (SPINE_X, merge_y)])
    return merge_y


def loop_back(loop_x, from_y, top_y, left_v_xy, from_x=None, text=None, color=DIM):
    """루프 조건 다이아몬드 왼쪽 정점으로 돌아가는 경로. from_x 없으면 SPINE_X-210."""
    fx = from_x if from_x is not None else SPINE_X - 210
    elbow([(fx, from_y), (loop_x, from_y), (loop_x, top_y), left_v_xy])
    if text:
        parts.append(f'<g transform="rotate(-90,{loop_x-18},{(from_y+top_y)/2})">'
                      f'<text x="{loop_x-18}" y="{(from_y+top_y)/2}" text-anchor="middle" font-size="10.5" '
                      f'fill="{color}" font-style="italic">{esc(text)}</text></g>')


parts.append(f'''<defs>
  <marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{INK}"/></marker>
</defs>''')

cy = 60
h = terminator(SPINE_X, cy, "시작"); badge(SPINE_X, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["config.yaml 로드", "(failure_modes · assumptions · content 파싱)"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["modes = failure_modes ;  i = 0"], h=44, mono_from=0)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ===== OUTER LOOP: 고장모드(failure_mode) =====
outer_top_y = cy
d_h = decision(SPINE_X, cy, ["i < len(modes) ?", "(모든 고장모드 처리?)"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
outer_left_v = (SPINE_X - 160, cy)
outer_right_v = (SPINE_X + 160, cy)
outer_bottom = cy + d_h/2
label(outer_left_v[0]-8, cy-8, "예", size=12.5, color=GREEN, bold=True, anchor="end")
label(outer_right_v[0]+8, cy-8, "아니오", size=12.5, color=RED, bold=True, anchor="start")

cy = flow_down(outer_bottom, 36)
h = process(SPINE_X, cy, ["mode = modes[i]", "events · readouts · groups CSV 로드 (모드별 컬럼·카운터)"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["정제 6단계",
                           "(동기화 → 드리프트제거 → 구간분할 → 결측/이상치 → 코드정합 → 라벨정의)"], h=64)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["자산별 rate(t) → z(t) → anomaly(t) → t*, lead_time 계산"], h=52)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["groups = mode.group_col의 값 목록 ;  j = 0"], h=44, mono_from=0)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- NESTED INNER LOOP: 그룹(group) -- O,S,D 계산 ----
inner_top_y = cy
d_h2 = decision(SPINE_X, cy, ["j < len(groups) ?", "(이 모드의 모든 그룹 처리?)"], w=280, h=92)
badge(SPINE_X, cy - d_h2/2, step_num())
inner_left_v = (SPINE_X - 140, cy)
inner_right_v = (SPINE_X + 140, cy)
inner_bottom = cy + d_h2/2
label(inner_left_v[0]-8, cy-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(inner_right_v[0]+8, cy-8, "아니오", size=12, color=RED, bold=True, anchor="start")

cy = flow_down(inner_bottom, 32)
h = process(SPINE_X, cy, ["group = groups[j]"], w=340, h=40)
badge(SPINE_X - 170, cy, step_num())
cy = flow_down(cy + h/2, 50)

h = process(SPINE_X, cy, ["O, S, D 계산  (§2 공식)",
                           "λ,rate,O등급 · S_raw,S등급(근사)",
                           "guide word+오차율% · 탐지율,이항검정,D등급"], w=400, h=78)
badge(SPINE_X - 200, cy, step_num())
cy = flow_down(cy + h/2, 32)

h = process(SPINE_X, cy, ["j = j + 1"], w=200, h=36)
badge(SPINE_X - 100, cy, step_num())
inner_incr_y = cy

INNER_LOOP_X = 260
loop_back(INNER_LOOP_X, inner_incr_y, inner_top_y, inner_left_v, from_x=SPINE_X-100,
          text="↺ 그룹 루프백", color=ACCENT)

# inner loop exit ("아니오") -> routes right, then down, then into i++ box (NOT a
# spine fallthrough from j++ -- the inner loop's only way out is the diamond's "아니오")
inner_exit_x = SPINE_X + 360
elbow([inner_right_v, (inner_exit_x, inner_right_v[1])], ah=False)
cy = inner_incr_y + 18 + 30 + 18  # j++ box bottom + gap + i++ box half-height, no drawn line

h = process(SPINE_X, cy, ["i = i + 1"], w=200, h=36)
badge(SPINE_X - 100, cy, step_num())
elbow([(inner_exit_x, inner_right_v[1]), (inner_exit_x, cy), (SPINE_X+100, cy)])
outer_incr_y = cy

OUTER_LOOP_X = 90
loop_back(OUTER_LOOP_X, outer_incr_y, outer_top_y, outer_left_v, from_x=SPINE_X-100,
          text="↺ 고장모드 루프백 — 다음 모드로", color=DIM)

# outer loop exit ("아니오") -> down to combine step
outer_exit_x = SPINE_X + 460
elbow([outer_right_v, (outer_exit_x, outer_right_v[1])], ah=False)

cy_combine = outer_incr_y + 110
h = process(SPINE_X, cy_combine, ["전체 (고장모드,그룹) 결합",
                                   "RPN = O×S×D    RI = 0.4O + 0.4S + 0.2D"], h=60, mono_from=1)
badge(SPINE_X - 210, cy_combine, step_num())
elbow([(outer_exit_x, outer_right_v[1]), (outer_exit_x, cy_combine), (SPINE_X+210, cy_combine)])
cy = flow_down(cy_combine + h/2, 36)

h = io_box(SPINE_X, cy, ["fmeca_worksheet.csv 등 outputs/ 저장", "— 01_pipeline.py 종료 —"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ===== LOOP: 02_lifecycle.py -- 워크시트 각 행 =====
lc_top_y = cy
d_h3 = decision(SPINE_X, cy, ["k < len(worksheet) ?", "(모든 (고장모드,그룹) 행 처리?)"], w=340, h=100)
badge(SPINE_X, cy - d_h3/2, step_num())
lc_left_v = (SPINE_X - 170, cy)
lc_right_v = (SPINE_X + 170, cy)
lc_bottom = cy + d_h3/2
label(lc_left_v[0]-8, cy-8, "예", size=12.5, color=GREEN, bold=True, anchor="end")
label(lc_right_v[0]+8, cy-8, "아니오", size=12.5, color=RED, bold=True, anchor="start")

cy = flow_down(lc_bottom, 36)
h = process(SPINE_X, cy, ["row = worksheet[k]  (failure_mode, group)"], w=440, h=40)
badge(SPINE_X - 220, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- RCM: 3-way (special) ----
d_h = decision(SPINE_X, cy, ["유의(p<.05) &", "탐지율 ≥ 50% ?"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
lv, rv = (SPINE_X-160, cy), (SPINE_X+160, cy)
d1_bottom = cy + d_h/2
label(lv[0]-8, cy-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(rv[0]+8, cy-8, "아니오", size=12, color=RED, bold=True, anchor="start")

cbm_cy = d1_bottom + 44 + 29
elbow([lv, (SPINE_X-260, cbm_cy-29)])
process(SPINE_X-260, cbm_cy, ["RCM = CBM", "(상태기반정비)"], w=250, h=58)

cy2 = flow_down(d1_bottom, 84)
d_h2b = decision(SPINE_X, cy2, ["S ≥ 5 ?"], w=280, h=96)
badge(SPINE_X, cy2 - d_h2b/2, step_num())
lv2, rv2 = (SPINE_X-140, cy2), (SPINE_X+140, cy2)
d2_bottom = cy2 + d_h2b/2
label(lv2[0]-8, cy2-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(rv2[0]+8, cy2-8, "아니오", size=12, color=RED, bold=True, anchor="start")

box_cy = d2_bottom + 40 + 29
elbow([lv2, (SPINE_X-250, box_cy-29)])
elbow([rv2, (SPINE_X+250, box_cy-29)])
process(SPINE_X-250, box_cy, ["RCM = Hard-Time", "(시간기준 예방정비)"], w=260, h=58)
process(SPINE_X+250, box_cy, ["RCM = RTF", "(사후정비)"], w=260, h=58)

merge_y = box_cy + 29 + 40
elbow([(SPINE_X-250, box_cy+29), (SPINE_X, merge_y)])
elbow([(SPINE_X+250, box_cy+29), (SPINE_X, merge_y)])
far_x = SPINE_X - 460
elbow([(SPINE_X-260, cbm_cy+29), (far_x, cbm_cy+29)], ah=False)
elbow([(far_x, cbm_cy+29), (far_x, merge_y), (SPINE_X, merge_y)])
label(far_x-10, (cbm_cy+merge_y)/2, "CBM 결과 합류", size=10, color=DIM, italic=True, anchor="middle")
cy = merge_y

# ---- LORA ----
cy = flow_down(cy, 84)
cy = decision_pair(cy, ["O ≥ 8 ?"],
                    ["LORA = 창정비 우선상향", "+ 예비품 전진배치"],
                    ["LORA = 표준 2-Level", "(야전교환+창정비모듈수리)"])

# ---- 보급소요 ----
cy = flow_down(cy, 40)
h = process(SPINE_X, cy, ["보급소요 계산 (가정치+실측 O 결합)",
                           "annual_demand, reorder_point = f(rate, fleet_size, lead_days)"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- IETM ----
cy = decision_pair(cy, ["유의 & 리드타임", "존재 ?"],
                    ["IETM = 사전점검 SLA", "SLA = 리드타임 × 0.5"],
                    ["IETM = 정기점검 강화", "(사전 SLA 없음)"])

# ---- ECP ----
cy = flow_down(cy, 84)
cy = decision_pair(cy, ["RPN 1위 / O=10 /", "비유의 중 하나 ?"],
                    ["ECP = 후보", "(설계개선 필요)"],
                    ["ECP = 현행유지", "(트리거 없음)"])

# ---- save row, k++, loop back ----
cy = flow_down(cy, 36)
h = process(SPINE_X, cy, ["결과 행 저장 ;  k = k + 1"], h=44)
badge(SPINE_X - 210, cy, step_num())
lc_loopback_y = cy

LC_LOOP_X = 90
loop_back(LC_LOOP_X, lc_loopback_y, lc_top_y, lc_left_v, text="↺ 행 루프백 — 다음 (고장모드,그룹)으로")

lc_exit_x = SPINE_X + 460
elbow([lc_right_v, (lc_exit_x, lc_right_v[1])], ah=False)

cy_out = lc_loopback_y + 110
h = io_box(SPINE_X, cy_out, ["lifecycle.csv/json 저장", "— 02_lifecycle.py 종료 —"], h=60)
badge(SPINE_X - 210, cy_out, step_num())
elbow([(lc_exit_x, lc_right_v[1]), (lc_exit_x, cy_out), (SPINE_X+210, cy_out)])
cy = flow_down(cy_out + h/2, 40)

# ---- 04: 원본↔전처리 비교 샘플 자동선정 ----
h = process(SPINE_X, cy, ["고장모드별 예시자산 자동선정(탐지성공1+실패1)",
                           "원본 판독 재계산 → transform_sample.json",
                           "— 04_export_transform_sample.py —"], h=78)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

# ---- 03: JSON export ----
h = io_box(SPINE_X, cy, ["dataset·fmeca·lifecycle·events·cleansing.json 생성",
                          "— 03_export_app_data.py —"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = io_box(SPINE_X, cy, ["app_data/ → app/data/ 복사 (run_pipeline.py)"], h=48)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- feedback decision (웹앱 §09) ----
d_h = decision(SPINE_X, cy, ["ECP 후보 있음 ?", "(피드백 시뮬레이션, 웹앱)"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
lv, rv = (SPINE_X-160, cy), (SPINE_X+160, cy)
db = cy + d_h/2
label(lv[0]-8, cy-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(rv[0]+8, cy-8, "아니오", size=12, color=RED, bold=True, anchor="start")

fb_cy = db + 40 + 32
elbow([lv, (SPINE_X-260, fb_cy-32)])
process(SPINE_X-260, fb_cy, ["O′=O−2, D′=D−3 재계산 →", "RPN′,RI′,RCM′,LORA′,IETM′,보급소요′"], w=300, h=64)
fb2_cy = fb_cy + 32 + 26 + 26
h_io = io_box(SPINE_X-260, fb2_cy, ["웹앱 §09에 결과 표시"], w=300, h=48)

merge_y = fb2_cy + h_io/2 + 40
elbow([(SPINE_X-260, fb2_cy+h_io/2), (SPINE_X, merge_y)])
elbow([rv, (SPINE_X+40, db+20), (SPINE_X, merge_y)])
label(rv[0]+16, db+20, "(바로 종료로)", size=9.5, color=DIM, italic=True, anchor="start")

cy = flow_down(merge_y, 40)
h = terminator(SPINE_X, cy, "종료")
badge(SPINE_X, cy, step_num())

TOTAL_H = int(cy + h/2 + 60)
CANVAS_W = W

svg = f'''<svg viewBox="0 0 {CANVAS_W} {TOTAL_H}" xmlns="http://www.w3.org/2000/svg" font-family="'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif">
<rect x="0" y="0" width="{CANVAS_W}" height="{TOTAL_H}" fill="#ffffff"/>
<text x="40" y="34" font-family="Georgia,serif" font-size="22" font-weight="700" fill="{INK}">FMECA-IPS 파이프라인 — 프로그래밍 플로우차트</text>
<text x="40" y="54" font-size="12" fill="{DIM}">범용 데이터셋 스키마 기준(DATASET_FORMAT.md) · run_pipeline.py가 01→02→04→03 순서로 실행 · 표준 도형: ⬭시작/종료 ▱입출력 ▭처리 ◇판단</text>
{"".join(parts)}
</svg>'''

with open("flowchart_program.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("done, height=", TOTAL_H, "width=", CANVAS_W, "steps=", n_counter)
