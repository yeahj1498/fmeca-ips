# -*- coding: utf-8 -*-
"""FMECA-IPS (SCANIA Component X) presentation, built with python-pptx."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn
import copy

# ---------------------------------------------------------------------------
# palette / type
# ---------------------------------------------------------------------------
DOMINANT = RGBColor(0x16, 0x30, 0x2B)   # deep teal-forest (dark bg)
SECONDARY = RGBColor(0x2C, 0x6B, 0x73)  # teal (headers, primary data)
PANEL = RGBColor(0xF0, 0xF4, 0xF2)      # light cool panel bg
LIGHT_LINE = RGBColor(0xDD, 0xE3, 0xDF)
INK = RGBColor(0x1A, 0x24, 0x22)
INK_DIM = RGBColor(0x55, 0x63, 0x5E)
INK_FAINT = RGBColor(0x8B, 0x96, 0x8F)
AMBER = RGBColor(0xB5, 0x65, 0x1D)
AMBER_BG = RGBColor(0xF7, 0xEB, 0xDD)
RED = RGBColor(0xA8, 0x34, 0x2C)
RED_BG = RGBColor(0xF8, 0xE2, 0xDF)
GREEN = RGBColor(0x3C, 0x7A, 0x4F)
GREEN_BG = RGBColor(0xE3, 0xF0, 0xE4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CREAM_TEXT = RGBColor(0xE7, 0xEC, 0xE9)  # light text on dark bg
CREAM_DIM = RGBColor(0xA9, 0xBB, 0xB4)

HEAD_FONT = "Cambria"
BODY_FONT = "Calibri"

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def new_slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    r.fill.solid(); r.fill.fore_color.rgb = bg
    r.line.fill.background()
    r.shadow.inherit = False
    return s

def set_run(run, text, size, color, bold=False, font=BODY_FONT, italic=False):
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font

def add_text(slide, x, y, w, h, lines, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             wrap=True, autosize=False, margin=0.0):
    """lines: list of paragraphs; each paragraph is list of (text,size,color,bold,font,italic) tuples,
       or a single tuple (shorthand for a one-run paragraph)."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(margin)
    if isinstance(lines[0], tuple):
        lines = [[ln] for ln in lines]
    for i, para in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for j, run_spec in enumerate(para):
            text, size, color = run_spec[0], run_spec[1], run_spec[2]
            bold = run_spec[3] if len(run_spec) > 3 else False
            font = run_spec[4] if len(run_spec) > 4 else BODY_FONT
            italic = run_spec[5] if len(run_spec) > 5 else False
            r = p.add_run()
            set_run(r, text, size, color, bold, font, italic)
    return tb

def add_rect(slide, x, y, w, h, fill, line_color=None, line_w=None, shape=MSO_SHAPE.RECTANGLE, radius=None, shadow=False):
    sh = slide.shapes.add_shape(shape, x, y, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line_color is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line_color
        sh.line.width = line_w or Pt(0.75)
    sh.shadow.inherit = shadow
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            sh.adjustments[0] = radius
        except Exception:
            pass
    return sh

def add_oval(slide, x, y, w, h, fill, line_color=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, x, y, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line_color is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line_color
        sh.line.width = Pt(1)
    sh.shadow.inherit = False
    return sh

def header(slide, eyebrow, title, dark=False, y=Inches(0.45)):
    ink = CREAM_TEXT if dark else INK
    eyebrow_color = RGBColor(0x9F, 0xD8, 0xDC) if dark else SECONDARY
    add_text(slide, Inches(0.6), y, Inches(11.5), Inches(0.35),
             [[(eyebrow, 12, eyebrow_color, True, BODY_FONT)]])
    add_text(slide, Inches(0.58), y + Inches(0.32), Inches(12), Inches(0.75),
             [[(title, 30, ink, True, HEAD_FONT)]])

def footer(slide, text, dark=False):
    c = CREAM_DIM if dark else INK_FAINT
    add_text(slide, Inches(0.6), Inches(7.08), Inches(9), Inches(0.3),
             [[(text, 9.5, c, False, BODY_FONT)]])
    add_text(slide, Inches(11.6), Inches(7.08), Inches(1.2), Inches(0.3),
             [[("", 9.5, c)]])

def stat_card(slide, x, y, w, h, number, label, color=SECONDARY, bg=PANEL):
    add_rect(slide, x, y, w, h, bg, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    add_text(slide, x + Inches(0.15), y + Inches(0.12), w - Inches(0.3), h - Inches(0.6),
              [[(number, 30, color, True, HEAD_FONT)]], anchor=MSO_ANCHOR.BOTTOM)
    add_text(slide, x + Inches(0.15), y + h - Inches(0.42), w - Inches(0.3), Inches(0.36),
              [[(label, 11, INK_DIM, False, BODY_FONT)]])

def bullet_block(slide, x, y, w, h, items, size=13.5, color=INK, gap=0.12, marker_color=SECONDARY):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap * 72)
        r = p.add_run()
        set_run(r, "―  ", size, marker_color, True, BODY_FONT)
        r2 = p.add_run()
        set_run(r2, it, size, color, False, BODY_FONT)
    return tb

def arrow_between(slide, x1, y, x2, color=INK_FAINT):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y, x2, y)
    conn.line.color.rgb = color
    conn.line.width = Pt(1.5)
    line = conn.line._get_or_add_ln()
    tail = line.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'})
    line.append(tail)

def style_chart_text(chart, color=INK_DIM, size=10):
    try:
        chart.category_axis.tick_labels.font.size = Pt(size)
        chart.category_axis.tick_labels.font.color.rgb = color
        chart.category_axis.format.line.color.rgb = LIGHT_LINE
    except Exception:
        pass
    try:
        chart.value_axis.tick_labels.font.size = Pt(size)
        chart.value_axis.tick_labels.font.color.rgb = color
        chart.value_axis.format.line.color.rgb = LIGHT_LINE
        chart.value_axis.has_major_gridlines = True
        chart.value_axis.major_gridlines.format.line.color.rgb = LIGHT_LINE
        chart.value_axis.major_gridlines.format.line.width = Pt(0.5)
    except Exception:
        pass

GROUP_LABELS = ["형상A", "형상B", "형상C", "형상D"]

# ===========================================================================
# SLIDE 1 -- Title
# ===========================================================================
s = new_slide(DOMINANT)
# subtle geometric accent: overlapping circles (motif repeated across deck), never a stripe
add_oval(s, Inches(10.6), Inches(-1.2), Inches(4.6), Inches(4.6), RGBColor(0x1D, 0x40, 0x3A))
add_oval(s, Inches(11.7), Inches(4.6), Inches(3.2), Inches(3.2), RGBColor(0x1D, 0x40, 0x3A))
add_oval(s, Inches(-1.4), Inches(5.6), Inches(3.6), Inches(3.6), RGBColor(0x1D, 0x40, 0x3A))

add_text(s, Inches(0.9), Inches(1.7), Inches(9.5), Inches(0.4),
         [[("실측 임베디드 장비 데이터 기반 FMECA–IPS 연계체계", 14, RGBColor(0x9F, 0xD8, 0xDC), True, BODY_FONT)]])
add_text(s, Inches(0.85), Inches(2.15), Inches(11), Inches(2.2),
         [[("FMECA → RCM → LORA →", 40, WHITE, True, HEAD_FONT)],
          [("보급소요 → IETM → 설계개선", 40, WHITE, True, HEAD_FONT)]])
add_text(s, Inches(0.9), Inches(4.05), Inches(10.5), Inches(0.5),
         [[("SCANIA Component X 실측 데이터로 실증한 종합군수지원(IPS) 연계 파이프라인", 17, CREAM_TEXT, False, BODY_FONT)]])

add_rect(s, Inches(0.9), Inches(4.85), Inches(0.55), Inches(0.32), AMBER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
add_text(s, Inches(0.9), Inches(4.85), Inches(0.55), Inches(0.32), [[("CC", 11, WHITE, True)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
add_text(s, Inches(1.55), Inches(4.85), Inches(6), Inches(0.32),
         [[("CC BY 4.0 · 실측(익명화·섭동 처리) · Kharazian et al. 2025, Scientific Data", 11.5, CREAM_DIM, False, BODY_FONT)]],
         anchor=MSO_ANCHOR.MIDDLE)

footer(s, "FMECA–IPS 연계체계 실증 연구  ·  2026", dark=True)

# ===========================================================================
# SLIDE 2 -- 배경 및 목적
# ===========================================================================
s = new_slide()
header(s, "배경 · 문제의식", "군 장비 데이터가 없으면, 실증은 불가능한가?")

col_w = Inches(5.55)
add_rect(s, Inches(0.6), Inches(1.7), col_w, Inches(4.9), PANEL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.035)
add_text(s, Inches(0.95), Inches(1.95), col_w - Inches(0.7), Inches(0.4),
         [[("왜 실측 대체 데이터인가", 16, SECONDARY, True, HEAD_FONT)]])
bullet_block(s, Inches(0.95), Inches(2.45), col_w - Inches(0.7), Inches(3.9), [
    "군 정비·운용 데이터는 보안 등급 때문에 이 환경에서 접근 불가능",
    "그렇다고 처음부터 가상 데이터로만 방법론을 보이면 “실전에서 통할까”라는 의문이 남음",
    "구조가 비슷한 민간 임베디드 장비(트럭 엔진계통)의 실측 공개 데이터로 대체 — 계산 절차 자체가 실제 데이터에서 작동하는지 검증",
    "산업계가 실제로 공개하는 데이터의 전형(민감정보는 섭동, 구조·경향은 보존)이라는 점도 오히려 현실적",
], size=13.5)

add_rect(s, Inches(6.35), Inches(1.7), col_w, Inches(4.9), WHITE, line_color=LIGHT_LINE, line_w=Pt(1), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.035)
add_text(s, Inches(6.7), Inches(1.95), col_w - Inches(0.7), Inches(0.4),
         [[("이 발표의 목적", 16, SECONDARY, True, HEAD_FONT)]])
bullet_block(s, Inches(6.7), Inches(2.45), col_w - Inches(0.7), Inches(3.9), [
    "원시 로그 한 줄이 FMECA의 O·S·D 칸을 채우는 계산식을 정확히 공개",
    "FMECA 결과가 RCM → LORA → 보급소요 → IETM → 설계개선(ECP)까지 실제로 이어지는 연계체계 시연",
    "설계개선이 다음 주기 FMECA에 피드백되는 환류(feedback) 구조를 수치로 시연",
    "실측 데이터가 보여준 정직한 한계(약한 탐지 신호 등)까지 있는 그대로 보고",
], size=13.5, marker_color=AMBER)

footer(s, "01_dataset_card.md · 05_ips_impact.md 참고")

# ===========================================================================
# SLIDE 3 -- 데이터셋 소개
# ===========================================================================
s = new_slide()
header(s, "입력 데이터", "SCANIA Component X dataset")

stats = [("23,550대", "차량(트럭) 규모"), ("1,122,452행", "계측(운영) 로그"),
         ("2,272건", "실제 수리(고장) 기록"), ("CC BY 4.0", "라이선스, 즉시 다운로드")]
cw = Inches(2.75); gap = Inches(0.2)
for i, (num, lab) in enumerate(stats):
    stat_card(s, Inches(0.6) + i * (cw + gap), Inches(1.75), cw, Inches(1.5), num, lab)

add_text(s, Inches(0.6), Inches(3.55), Inches(11.6), Inches(0.4),
         [[("무엇을 담고 있나", 15, SECONDARY, True, HEAD_FONT)]])
bullet_block(s, Inches(0.6), Inches(4.0), Inches(5.7), Inches(2.7), [
    "실제 SCANIA 트럭 함대의 엔진계통 구성품 “Component X” 1종 — 명칭·규격은 영업비밀로 익명화",
    "운영데이터(8개 누적 계측 카운터) + 수리기록(time-to-event) + 차량 사양(Spec_0–7)",
    "공개를 위해 판독·수리 빈도에 스케일링 등 섭동(perturbation) 처리 — “완전 실측”과 “완전 합성” 사이",
], size=13.5)

add_text(s, Inches(6.7), Inches(4.0), Inches(5.4), Inches(0.4),
         [[("이번 예시가 다른 점", 15, AMBER, True, HEAD_FONT)]])
bullet_block(s, Inches(6.7), Inches(4.4), Inches(5.4), Inches(2.4), [
    "구성품이 하나뿐 — “4개 고장모드” 대신 “1개 고장모드 × 4개 차량 사양군(Spec_3)”으로 FMECA 행 구성",
    "채널 8개 모두 물리적 의미 비공개 — “이상치 유무”까지만 판단 가능, 원인 설명 불가",
], size=13, marker_color=AMBER)

footer(s, "출처: doi.org/10.5878/jvb5-d390  ·  Kharazian et al., Scientific Data (2025)")

# ===========================================================================
# SLIDE 4 -- 연계체계 파이프라인 개요
# ===========================================================================
s = new_slide()
header(s, "전체 구조", "FMECA → RCM → LORA → 보급 → IETM → 설계개선, 한눈에")

nodes = ["실측\n운용·계측\n데이터", "FMECA\nO·S·D\n실적 계산", "RCM\n정비전략\n결정", "LORA\n수리수준\n분석",
         "보급소요\n산정", "IETM\n연계", "설계개선\n(ECP)"]
n = len(nodes)
box_w = Inches(1.55); box_h = Inches(1.35)
total_w = Inches(13.333) - Inches(1.2)
step = (Emu(total_w) - Emu(box_w)) // (n - 1)
y0 = Inches(2.1)
xs = []
for i, label in enumerate(nodes):
    x = Emu(Inches(0.6)) + i * step
    xs.append(x)
    fill = SECONDARY if i not in (0,) else DOMINANT
    box = add_rect(s, x, y0, box_w, box_h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.09)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.06)
    parts = label.split("\n")
    for j, part in enumerate(parts):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, part, 12.5 if j == 0 else 10.5, WHITE, j == 0, BODY_FONT)
    add_text(s, x, y0 - Inches(0.32), box_w, Inches(0.28),
              [[(f"{i:02d}" if i else "IN", 11, INK_FAINT, True, BODY_FONT)]], align=PP_ALIGN.CENTER)

for i in range(n - 1):
    mid_gap_x1 = Emu(xs[i]) + Emu(box_w)
    mid_gap_x2 = Emu(xs[i + 1])
    arrow_between(s, mid_gap_x1 + Emu(Inches(0.03)), y0 + Emu(box_h) // 2, mid_gap_x2 - Emu(Inches(0.03)), INK_FAINT)

# feedback loop annotation
add_rect(s, Inches(0.6), Inches(3.95), Inches(12.13), Inches(0.85), AMBER_BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
add_text(s, Inches(0.95), Inches(4.08), Inches(11.5), Inches(0.6),
         [[("↺  피드백 루프 — ", 13, AMBER, True, BODY_FONT),
           ("설계개선(ECP) 결과가 다음 재평가 주기의 O(발생도)·D(검출도) 입력을 갱신 — 실제로 재계산되는 예시는 p.13", 13, INK, False, BODY_FONT)]],
         anchor=MSO_ANCHOR.MIDDLE)

add_text(s, Inches(0.6), Inches(5.15), Inches(12.1), Inches(1.6),
         [[("이 발표의 각 섹션은 위 7단계 중 하나에 대응한다 — ", 13, INK_DIM, False, BODY_FONT),
           ("정제(§5) → O/S/D 공식(§6) → FMECA 결과(§7–9) → RCM/LORA(§10–11) → 보급/IETM/ECP(§11–12) → 피드백(§13)", 13, INK_DIM, True, BODY_FONT)]])

footer(s, "웹 워크벤치: claude.ai/code/artifact/7c5a27c2-… (09 피드백 시뮬레이터 탭)")

# ===========================================================================
# SLIDE 5 -- 정제 파이프라인 6단계
# ===========================================================================
s = new_slide()
header(s, "입력 정제", "정제 파이프라인 — 순서 고정 6단계")

steps = [
    ("01", "동기화", "차량별로 비동기인 계측 판독을 vehicle_id+time_step 키로 정합", "판독 1,122,452행 · 차량당 중앙값 43회(5~303회)"),
    ("02", "드리프트 제거", "차량×채널 증분율(rate)을 자기 자신의 과거 이력으로 z-정규화", "이상지수 산출 1,098,902행 (97.9%)"),
    ("03", "구간 분할", "train_tte.csv가 장착 이후 경과 time-step을 이미 제공 — 좌측절단 없음", "수리 2,272건 · 무고장(우측절단) 21,278대"),
    ("04", "결측치 / 이상치", "채널당 결측률 재확인, 이상지수>8 극단치 플래그(삭제 아님)", "결측 <1%/채널 · 이상치 94건(0.0086%)"),
    ("05", "코드 정합", "3개 파일 간 vehicle_id 일치성, 중복행 검증", "ID 불일치 0건 · 중복행 0건"),
    ("06", "라벨 정의", "수리(양성) vs 무고장(음성) 라벨 및 클래스 불균형비 산출", "0.4014건 / 1,000 time-step (극단 불균형)"),
]
y = Inches(1.65)
row_h = Inches(0.865)
for num, title, desc, stat in steps:
    add_oval(s, Inches(0.6), y + Inches(0.08), Inches(0.5), Inches(0.5), SECONDARY)
    add_text(s, Inches(0.6), y + Inches(0.08), Inches(0.5), Inches(0.5), [[(num, 13, WHITE, True)]],
              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(1.3), y, Inches(3.1), row_h, [[(title, 14.5, INK, True, HEAD_FONT)]], anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(4.5), y, Inches(4.9), row_h, [[(desc, 11.5, INK_DIM, False, BODY_FONT)]], anchor=MSO_ANCHOR.MIDDLE)
    add_rect(s, Inches(9.55), y + Inches(0.1), Inches(3.2), Inches(0.65), PANEL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.18)
    add_text(s, Inches(9.7), y + Inches(0.1), Inches(2.9), Inches(0.65), [[(stat, 11, SECONDARY, True, BODY_FONT)]], anchor=MSO_ANCHOR.MIDDLE)
    y = y + row_h

footer(s, "outputs/cleansing_stats.json 재계산 결과 (실측 데이터)")

# ===========================================================================
# SLIDE 6 -- O / D 산출 공식
# ===========================================================================
s = new_slide()
header(s, "계산식", "발생도(O)·검출도(D) — 원시 로그에서 등급까지")

add_rect(s, Inches(0.6), Inches(1.7), Inches(5.6), Inches(4.9), PANEL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.03)
add_text(s, Inches(0.9), Inches(1.9), Inches(5), Inches(0.4), [[("발생도 O", 16, SECONDARY, True, HEAD_FONT)]])
mono_lines = [
    "λ = 수리건수(k) / 노출시간(Σ time-step)",
    "rate = λ × 1000   (1000 time-step당 건수)",
    "O등급 = log10(rate)를 관측범위 10구간",
    "        균등분할해 1~10 배정",
    "95%CI = χ²(0.025,2k)/2 , χ²(0.975,2(k+1))/2",
]
add_text(s, Inches(0.9), Inches(2.35), Inches(5), Inches(1.9),
         [[(ln, 13, INK, False, "Consolas")] for ln in mono_lines], anchor=MSO_ANCHOR.TOP)
add_text(s, Inches(0.9), Inches(4.35), Inches(5), Inches(2.1),
         [[("발생도가 높다 = 노출시간당 실제 수리건수가 많다", 12, INK_DIM)],
          [("표본이 큰 사양군(수천 대)일수록 신뢰구간이 좁아 통계적으로 확고한 차이를 준다", 12, INK_DIM)]])

add_rect(s, Inches(6.5), Inches(1.7), Inches(6.2), Inches(4.9), WHITE, line_color=LIGHT_LINE, line_w=Pt(1), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.03)
add_text(s, Inches(6.8), Inches(1.9), Inches(5.6), Inches(0.4), [[("검출도 D — 열화추세 → 이상지수", 16, AMBER, True, HEAD_FONT)]])
d_steps = [
    ("①", "증분율", "rate(t) = [value(t)-value(t-1)] / [t-(t-1)]  — 8개 채널"),
    ("②", "자기기준 정규화", "z(t) = [rate(t) - μ] / σ   (그 차량 과거 이력 기준)"),
    ("③", "종합 이상지수", "anomaly(t) = mean(|z_1|, …, |z_8|)"),
    ("④", "최초 경보시점", "t* = min{t : anomaly(t) > 2.5}"),
    ("⑤", "리드타임", "lead = 수리시점 - t*  (0~60 이내만 “탐지”로 인정)"),
    ("⑥", "우연수준 검증", "이항검정으로 무고장 차량의 우연 교차율과 비교(p<0.05)"),
]
yy = Inches(2.4)
for tag, name, formula in d_steps:
    add_text(s, Inches(6.8), yy, Inches(0.4), Inches(0.5), [[(tag, 14, AMBER, True)]])
    add_text(s, Inches(7.25), yy, Inches(1.55), Inches(0.5), [[(name, 11.5, INK, True, BODY_FONT)]])
    add_text(s, Inches(8.85), yy, Inches(3.75), Inches(0.5), [[(formula, 10.8, INK_DIM, False, "Consolas")]])
    yy += Inches(0.62)
add_text(s, Inches(6.8), yy + Inches(0.05), Inches(5.7), Inches(0.5),
         [[("D등급 = round(10 − 9×[0.6×탐지율 + 0.4×min(리드타임/60,1)])", 12, INK, True, "Consolas")]])

footer(s, "scripts/01_pipeline.py  ·  S(심각도,근사)=anomaly평균, guide word+오차율(%)로 이탈 명시")

# ===========================================================================
# SLIDE 7 -- FMECA 워크시트 결과
# ===========================================================================
s = new_slide()
header(s, "분석 결과", "FMECA 워크시트 — 4개 사양군")

rows_data = [
    ("사양군", "차량수", "수리", "O", "S", "D", "RPN", "RI"),
    ("형상B (Cat1)", "5,083", "608", "10", "10", "8", "800", "9.6"),
    ("형상A (Cat0)", "14,438", "1,435", "9", "5", "8", "360", "7.2"),
    ("형상C (Cat2)", "2,158", "152", "5", "2", "8", "80", "4.4"),
    ("형상D (Cat3)", "1,871", "77", "1", "1", "8", "8", "2.4"),
]
tbl_x, tbl_y, tbl_w, tbl_h = Inches(0.6), Inches(1.75), Inches(6.6), Inches(2.75)
gtbl = s.shapes.add_table(len(rows_data), len(rows_data[0]), tbl_x, tbl_y, tbl_w, tbl_h).table
col_widths = [1.7, 0.85, 0.75, 0.6, 0.6, 0.6, 0.75, 0.75]
for i, w in enumerate(col_widths):
    gtbl.columns[i].width = Inches(w)
for ci, row in enumerate(rows_data):
    for cj, val in enumerate(row):
        cell = gtbl.cell(ci, cj)
        cell.text = ""
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if cj else PP_ALIGN.LEFT
        r = p.add_run()
        header_row = ci == 0
        set_run(r, val, 12 if header_row else 12.5, WHITE if header_row else INK, header_row or cj == 0, BODY_FONT)
        cell.fill.solid()
        cell.fill.fore_color.rgb = SECONDARY if header_row else (PANEL if ci % 2 == 0 else WHITE)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.08); cell.margin_top = Inches(0.03); cell.margin_bottom = Inches(0.03)

# RPN bar chart
cd = CategoryChartData()
cd.categories = GROUP_LABELS
cd.add_series("RPN", (360, 800, 80, 8))  # order matches GROUP_LABELS = [형상A, 형상B, 형상C, 형상D]
gx, gy, gw, gh = Inches(7.5), Inches(1.75), Inches(5.25), Inches(2.75)
gframe = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, gx, gy, gw, gh, cd)
chart = gframe.chart
chart.has_legend = False
chart.has_title = True
chart.chart_title.text_frame.text = "RPN (O×S×D)"
chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
chart.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = INK
plot = chart.plots[0]
plot.has_data_labels = True
plot.data_labels.number_format = "0"
plot.data_labels.number_format_is_linked = False
plot.data_labels.font.size = Pt(10.5)
plot.data_labels.font.color.rgb = INK
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
series = plot.series[0]
series.format.fill.solid()
series.format.fill.fore_color.rgb = SECONDARY
style_chart_text(chart)
chart.value_axis.visible = True

add_text(s, Inches(0.6), Inches(4.75), Inches(12.1), Inches(1.7),
         [[("순위 역전 없음: ", 13, INK, True, BODY_FONT),
           ("D등급이 4개 사양군 모두 동일(8)해 순위에 영향을 주지 못했고, O·S가 완전히 같은 순서로 정렬됨", 13, INK_DIM)],
          [("→ 위험 요인들이 서로 강화하는 방향으로 실제로 작동한다는 뜻 (이전 두 시뮬레이션 예시와 대조되는 실측 데이터의 특징)", 12.5, INK_DIM)]])

footer(s, "04_fmeca_worksheet.csv 전문")

# ===========================================================================
# SLIDE 8 -- 핵심발견 1: 사양군별 위험도 차이
# ===========================================================================
s = new_slide()
header(s, "핵심 발견 · 1", "동일 고장모드, 차량 사양에 따라 위험도가 2.8~14.7배 갈린다")

cd = CategoryChartData()
cd.categories = ["형상D\n(Cat3)", "형상C\n(Cat2)", "형상A\n(Cat0)", "형상B\n(Cat1)"]
cd.add_series("발생률 (/1000 time-step)", (0.17452, 0.29045, 0.41409, 0.4942))
gframe = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.7), Inches(6.4), Inches(4.0), cd)
chart = gframe.chart
chart.has_legend = False
chart.has_title = True
chart.chart_title.text_frame.text = "Spec_3 사양군별 발생률"
chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13); chart.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = INK
plot = chart.plots[0]
plot.has_data_labels = True
plot.data_labels.number_format = "0.000"; plot.data_labels.number_format_is_linked = False
plot.data_labels.font.size = Pt(10.5); plot.data_labels.font.color.rgb = INK
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
plot.series[0].format.fill.solid(); plot.series[0].format.fill.fore_color.rgb = SECONDARY
pts = plot.series[0].points
pts[3].format.fill.solid(); pts[3].format.fill.fore_color.rgb = RED
style_chart_text(chart)

add_text(s, Inches(7.35), Inches(1.75), Inches(5.4), Inches(0.4), [[("표본이 커서 통계적으로 확고함", 15, SECONDARY, True, HEAD_FONT)]])
bullet_block(s, Inches(7.35), Inches(2.25), Inches(5.4), Inches(2.3), [
    "형상B(5,083대) 0.494 vs 형상D(1,871대) 0.175 → 2.8배",
    "95% CI 0.456–0.535 vs 0.138–0.218 — 겹치지 않음",
    "심각도(S, 근사지표)도 같은 순서 — 형상B가 “더 자주, 더 강한 이상신호” 동반",
], size=12.5)

stat_card(s, Inches(7.35), Inches(4.75), Inches(5.4), Inches(1.75), "14.69배", "보너스 사례 · Spec_2 극단값: Cat5(545대, 0.918) vs Cat12(206대, 0.062) /1000 time-step", color=RED, bg=RED_BG)

footer(s, "outputs/occurrence_stats.csv · spec2_case.json")

# ===========================================================================
# SLIDE 9 -- 핵심발견 2: 탐지 신호의 한계
# ===========================================================================
s = new_slide()
header(s, "핵심 발견 · 2", "실측 데이터의 정직한 결론 — 조기경보는 생각보다 약하다")

cd = CategoryChartData()
cd.categories = GROUP_LABELS
cd.add_series("실제 탐지율(%)", (10.45, 11.84, 11.84, 9.09))
cd.add_series("우연 수준(%)", (9.52, 8.6, 9.47, 10.14))
gframe = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.75), Inches(7.1), Inches(4.1), cd)
chart = gframe.chart
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
chart.legend.font.size = Pt(11)
chart.has_title = True
chart.chart_title.text_frame.text = "탐지율 vs 우연 수준"
chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13); chart.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = INK
plot = chart.plots[0]
plot.has_data_labels = True
plot.data_labels.number_format = "0.0"; plot.data_labels.number_format_is_linked = False
plot.data_labels.font.size = Pt(9.5); plot.data_labels.font.color.rgb = INK
plot.series[0].format.fill.solid(); plot.series[0].format.fill.fore_color.rgb = SECONDARY
plot.series[1].format.fill.solid(); plot.series[1].format.fill.fore_color.rgb = INK_FAINT
style_chart_text(chart)

add_text(s, Inches(8.1), Inches(1.8), Inches(4.65), Inches(0.4), [[("이항검정 유의성 (p < 0.05)", 14.5, SECONDARY, True, HEAD_FONT)]])
sig_rows = [("형상B", "p = 0.0039", "유의함", GREEN, GREEN_BG), ("형상A", "p = 0.124", "비유의", RED, RED_BG),
            ("형상C", "p = 0.192", "비유의", RED, RED_BG), ("형상D", "p = 0.676", "비유의", RED, RED_BG)]
yy = Inches(2.3)
for name, pval, verdict, c, bg in sig_rows:
    add_rect(s, Inches(8.1), yy, Inches(4.65), Inches(0.62), bg, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
    add_text(s, Inches(8.3), yy, Inches(1.3), Inches(0.62), [[(name, 12.5, INK, True)]], anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(9.6), yy, Inches(1.7), Inches(0.62), [[(pval, 12, INK_DIM, False, "Consolas")]], anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(11.2), yy, Inches(1.4), Inches(0.62), [[(verdict, 12.5, c, True)]], anchor=MSO_ANCHOR.MIDDLE)
    yy += Inches(0.75)

add_text(s, Inches(0.6), Inches(6.1), Inches(12.1), Inches(0.9),
         [[("4개 사양군 중 3개는 탐지율이 우연 수준과 통계적으로 구분되지 않는다 — ", 13, RED, True, BODY_FONT),
           ("이는 방법론이 만든 결과가 아니라 데이터가 준 정직한 결론이며, 그대로 §10 RCM 결정에 반영된다.", 13, INK_DIM)]])

footer(s, "outputs/detection_stats.csv")

# ===========================================================================
# SLIDE 10 -- RCM 정비전략 결정
# ===========================================================================
s = new_slide()
header(s, "연계 · RCM", "RCM 정비전략 결정 — 규칙은 동일, 데이터가 결정한다")

add_text(s, Inches(0.6), Inches(1.62), Inches(12.1), Inches(0.55),
         [[("① 이상신호가 통계적으로 유의 + 탐지율≥50%면 상태기반정비(CBM)  →  ② 아니면 심각도(S)가 높으면 시간기준정비, 낮으면 사후정비", 12.5, INK_DIM, False, BODY_FONT)]])

rcm_cards = [
    ("형상B", "시간기준 예방정비\n(Hard-Time)", GREEN, GREEN_BG, "유의(p=0.004)하지만 탐지율 11.8%로 낮아 CBM 단독 불충분 · S=10 높음"),
    ("형상A", "시간기준 예방정비\n(Hard-Time)", AMBER, AMBER_BG, "조기신호 비유의(p=0.124) · S=5 → 정기 교체로 대응"),
    ("형상C", "사후정비\n(Run-to-Failure)", RED, RED_BG, "조기신호 비유의(p=0.192) · S=2 낮음 → 고장 후 조치가 경제적"),
    ("형상D", "사후정비\n(Run-to-Failure)", RED, RED_BG, "조기신호 비유의(p=0.676) · S=1 낮음 → 고장 후 조치가 경제적"),
]
cw = Inches(2.95); gap = Inches(0.15)
for i, (label, strat, c, bg, reason) in enumerate(rcm_cards):
    x = Inches(0.6) + i * (cw + gap)
    y = Inches(2.35)
    add_rect(s, x, y, cw, Inches(4.05), WHITE, line_color=LIGHT_LINE, line_w=Pt(1), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    add_text(s, x + Inches(0.18), y + Inches(0.18), cw - Inches(0.36), Inches(0.35), [[(label, 15, INK, True, HEAD_FONT)]])
    add_rect(s, x + Inches(0.18), y + Inches(0.62), cw - Inches(0.36), Inches(0.95), bg, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    strat_lines = strat.split("\n")
    add_text(s, x + Inches(0.18), y + Inches(0.7), cw - Inches(0.36), Inches(0.85),
              [[(ln, 13, c, True)] for ln in strat_lines], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, x + Inches(0.18), y + Inches(1.75), cw - Inches(0.36), Inches(2.15),
              [[(reason, 11, INK_DIM, False, BODY_FONT)]])

footer(s, "outputs/lifecycle.csv · scripts/02_lifecycle.py")

# ===========================================================================
# SLIDE 11 -- LORA · 보급소요
# ===========================================================================
s = new_slide()
header(s, "연계 · LORA / 보급소요", "수리수준분석과 정량 보급소요 산정")

add_text(s, Inches(0.6), Inches(1.62), Inches(12.1), Inches(0.45),
         [[("동일 물리 구성품이므로 수리복잡도(중상)는 공통 가정, O등급에 따라 창정비 우선순위만 차등", 12.5, INK_DIM)]])

rows_data = [
    ("사양군", "LORA 수준", "연간소요(건)", "재주문점", "단가"),
    ("형상B", "창정비 우선상향+전진배치", "12.63", "5.24", "2.80억"),
    ("형상A", "창정비 우선순위 상향", "10.58", "4.60", "2.80억"),
    ("형상C", "표준 2-Level", "7.42", "3.56", "2.80억"),
    ("형상D", "표준 2-Level", "4.46", "2.49", "2.80억"),
]
tbl = s.shapes.add_table(len(rows_data), len(rows_data[0]), Inches(0.6), Inches(2.3), Inches(9.0), Inches(2.6)).table
for i, w in enumerate([1.4, 3.3, 1.8, 1.35, 1.15]):
    tbl.columns[i].width = Inches(w)
for ci, row in enumerate(rows_data):
    for cj, val in enumerate(row):
        cell = tbl.cell(ci, cj)
        cell.text = ""
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if cj in (0, 1) else PP_ALIGN.CENTER
        r = p.add_run()
        header_row = ci == 0
        set_run(r, val, 12 if header_row else 12.5, WHITE if header_row else INK, header_row or cj == 0, BODY_FONT)
        cell.fill.solid()
        cell.fill.fore_color.rgb = SECONDARY if header_row else (PANEL if ci % 2 == 0 else WHITE)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.1)

add_rect(s, Inches(9.9), Inches(2.3), Inches(2.85), Inches(4.3), AMBER_BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
add_text(s, Inches(10.1), Inches(2.48), Inches(2.5), Inches(0.35), [[("보급소요 산식", 13, AMBER, True, HEAD_FONT)]])
add_text(s, Inches(10.1), Inches(2.88), Inches(2.5), Inches(3.5),
         [[("연간소요 = 실측 O등급 발생률", 11, INK)],
          [("  × 가정 함대 400대", 11, INK)],
          [("  × 가정 연간가동", 11, INK)],
          [("", 6, INK)],
          [("재주문점 = 리드타임수요", 11, INK)],
          [("  + 안전재고(서비스수준 95%,", 11, INK)],
          [("    z=1.645)", 11, INK)],
          [("", 6, INK)],
          [("가정: 리드타임 75일,", 10.5, INK_DIM, False, BODY_FONT, True)],
          [("단가 2.8억원 — 발생률만", 10.5, INK_DIM, False, BODY_FONT, True)],
          [("실측, 나머지는 예시 가정치", 10.5, INK_DIM, False, BODY_FONT, True)]])

add_text(s, Inches(0.6), Inches(5.35), Inches(9.0), Inches(1.2),
         [[("IETM 연계: ", 13, SECONDARY, True, BODY_FONT),
           ("경고코드 → 절차서 연동, D에서 얻은 평균 리드타임의 절반을 SLA로 설정. 유의하지 않은 3개 군은 “사전점검” 대신 정기점검 강화 절차만 정의", 12.5, INK_DIM)]])

footer(s, "outputs/lifecycle.json (assumptions)")

# ===========================================================================
# SLIDE 12 -- 설계개선(ECP)
# ===========================================================================
s = new_slide()
header(s, "연계 · 설계개선", "설계개선(ECP) 트리거 — RPN이 낮아도 “안 보이는 고장”은 후보")

add_text(s, Inches(0.6), Inches(1.62), Inches(12.1), Inches(0.45),
         [[("트리거 규칙: ① RPN 전체 1위  ② 발생도 최고등급(O=10)  ③ 이상신호가 우연 수준과 통계적으로 구분 안 됨", 12.5, INK_DIM)]])

ecp_cards = [
    ("형상B", ["RPN 전체 1위 (RPN=800) → 우선 재설계/대체부품 검토", "발생도 최고등급(O=10) → 근본 설계원인 분석 필요"]),
    ("형상A", ["이상신호가 우연 수준과 통계적으로 구분 안 됨(p=0.124) → 진단 알고리즘/센서 고도화 필요"]),
    ("형상C", ["이상신호가 우연 수준과 통계적으로 구분 안 됨(p=0.192) → 진단 알고리즘/센서 고도화 필요"]),
    ("형상D", ["이상신호가 우연 수준과 통계적으로 구분 안 됨(p=0.676) → 진단 알고리즘/센서 고도화 필요"]),
]
cw = Inches(2.95); gap = Inches(0.15)
for i, (label, triggers) in enumerate(ecp_cards):
    x = Inches(0.6) + i * (cw + gap)
    y = Inches(2.3)
    add_rect(s, x, y, cw, Inches(3.6), RED_BG, line_color=RED, line_w=Pt(1), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    add_text(s, x + Inches(0.18), y + Inches(0.15), cw - Inches(0.36), Inches(0.35), [[(label, 14.5, RED, True, HEAD_FONT)]])
    bullet_block(s, x + Inches(0.18), y + Inches(0.6), cw - Inches(0.36), Inches(2.9), triggers, size=10.8, color=INK, marker_color=RED, gap=0.1)

add_text(s, Inches(0.6), Inches(6.15), Inches(12.1), Inches(0.85),
         [[("4개 사양군 전부 ECP 후보 — ", 13, INK, True, BODY_FONT),
           ("이는 방법론의 과잉진단이 아니라, 이 구성품군 전체가 “탐지 신호 자체가 약하다”는 공통 이슈를 실측으로 보여준 것", 13, INK_DIM)]])

footer(s, "outputs/lifecycle.json (ecp_triggers)")

# ===========================================================================
# SLIDE 13 -- 피드백 시뮬레이터
# ===========================================================================
s = new_slide()
header(s, "환류(Feedback)", "ECP를 적용하면, 실제로 무엇이 바뀌는가")

add_text(s, Inches(0.6), Inches(1.6), Inches(12.1), Inches(0.5),
         [[("가정: ", 12.5, AMBER, True, BODY_FONT),
           ("근본설계 개선 → O등급 -2 (발생률 ~40%↓)   ·   진단 알고리즘 고도화 → D등급 -3 (탐지율 60%까지 개선)  — 등급만 가정, RPN·RI·RCM·보급소요는 실제 산식으로 재계산", 12, INK_DIM)]])

cd = CategoryChartData()
cd.categories = GROUP_LABELS
cd.add_series("적용 전 RPN", (360, 800, 80, 8))
cd.add_series("적용 후 RPN", (225, 640, 50, 5))
gframe = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(2.25), Inches(6.6), Inches(3.9), cd)
chart = gframe.chart
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
chart.legend.font.size = Pt(11)
chart.has_title = True
chart.chart_title.text_frame.text = "RPN: 적용 전 → 적용 후"
chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13); chart.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
chart.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = INK
plot = chart.plots[0]
plot.has_data_labels = True
plot.data_labels.font.size = Pt(9.5); plot.data_labels.font.color.rgb = INK
plot.series[0].format.fill.solid(); plot.series[0].format.fill.fore_color.rgb = INK_FAINT
plot.series[1].format.fill.solid(); plot.series[1].format.fill.fore_color.rgb = GREEN
style_chart_text(chart)

rcm_change = [("형상B", "Hard-Time", "Hard-Time", False), ("형상A", "Hard-Time", "CBM", True),
              ("형상C", "Run-to-Failure", "CBM", True), ("형상D", "Run-to-Failure", "CBM", True)]
add_text(s, Inches(7.5), Inches(2.3), Inches(5.25), Inches(0.4), [[("RCM 전략 재산정", 15, SECONDARY, True, HEAD_FONT)]])
yy = Inches(2.8)
for name, before, after, changed in rcm_change:
    bg = GREEN_BG if changed else PANEL
    add_rect(s, Inches(7.5), yy, Inches(5.25), Inches(0.72), bg, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    add_text(s, Inches(7.68), yy, Inches(1.1), Inches(0.72), [[(name, 12.5, INK, True)]], anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(8.8), yy, Inches(1.7), Inches(0.72), [[(before, 11, INK_FAINT)]], anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(10.55), yy, Inches(2.0), Inches(0.72),
             [[("→ " + after, 12, GREEN if changed else INK_DIM, True)]], anchor=MSO_ANCHOR.MIDDLE)
    yy += Inches(0.85)

footer(s, "웹 워크벤치 09 피드백 시뮬레이터 탭 — 브라우저에서 실시간 재계산")

# ===========================================================================
# SLIDE 14 -- 한계
# ===========================================================================
s = new_slide(DOMINANT)
header(s, "한계", "반드시 함께 읽을 것", dark=True)

limits = [
    ("수치의 출처", "O/S/D 등급은 SCANIA 트럭 함대의 실측(익명화·섭동)값. 보급소요의 리드타임·단가·가상 함대 규모는 방법론 예시를 위한 가정치일 뿐, 군 장비 실제 값이 아님"),
    ("단일 구성품", "이 데이터는 구성품이 하나뿐 — 3~5개 고장모드 비교가 아니라 “1개 고장모드 × 4개 사양군” 구조로 대체함"),
    ("채널 의미 비공개", "8개 계측 채널의 물리적 정의가 전부 익명화되어 “이상치 유무”까지만 판단, 원인 설명은 불가능"),
    ("소량·다품종 환경", "군 장비는 이보다 훨씬 적은 수량·다양한 형상이 혼재 — O 등급 신뢰구간이 넓어지고 표본 변동에 취약해짐"),
    ("자체조치·미보고 고장", "이 데이터는 모든 수리가 기록된다고 가정 — 야전 자체 조치·미보고 결함은 발생도(O)를 체계적으로 과소평가하게 만듦"),
    ("보안 승인 절차", "실제 군 데이터는 정보 등급 분류·반출 승인 등 이 예시에 없던 절차를 거쳐야 함"),
]
cw = Inches(5.9); gap = Inches(0.35); ch = Inches(1.5)
for i, (title, desc) in enumerate(limits):
    col = i % 2; row = i // 2
    x = Inches(0.6) + col * (cw + gap)
    y = Inches(1.75) + row * (ch + Inches(0.2))
    add_rect(s, x, y, cw, ch, RGBColor(0x1D, 0x40, 0x3A), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    add_text(s, x + Inches(0.25), y + Inches(0.14), cw - Inches(0.5), Inches(0.35), [[(title, 13.5, RGBColor(0xE3, 0xA0, 0x65), True, HEAD_FONT)]])
    add_text(s, x + Inches(0.25), y + Inches(0.52), cw - Inches(0.5), Inches(0.9), [[(desc, 11, CREAM_TEXT, False, BODY_FONT)]])

footer(s, "05_ips_impact.md §5", dark=True)

# ===========================================================================
# SLIDE 15 -- 맺음말
# ===========================================================================
s = new_slide(DOMINANT)
add_oval(s, Inches(10.6), Inches(-1.2), Inches(4.6), Inches(4.6), RGBColor(0x1D, 0x40, 0x3A))
add_oval(s, Inches(-1.4), Inches(5.6), Inches(3.6), Inches(3.6), RGBColor(0x1D, 0x40, 0x3A))

add_text(s, Inches(0.9), Inches(1.5), Inches(11), Inches(0.4),
         [[("맺음말", 14, RGBColor(0x9F, 0xD8, 0xDC), True, BODY_FONT)]])
add_text(s, Inches(0.85), Inches(1.9), Inches(11), Inches(1.4),
         [[("실측 데이터로도, 방법론은 동작했다", 32, WHITE, True, HEAD_FONT)]])

bullet_block(s, Inches(0.9), Inches(3.15), Inches(11), Inches(2.4), [
    "원시 계측·정비 로그 → O/S/D 등급 → RCM/LORA/보급소요/IETM/설계개선까지, 실측 데이터에서 전 과정이 실제로 계산됨",
    "탐지 신호가 약하다는 “불편한 결과”까지 숨기지 않았고, 그 결과가 RCM·ECP 결정에 그대로 반영됨을 확인",
    "설계개선(ECP) 적용 시 O·D·RPN·RCM이 실제로 재계산되는 피드백 루프를 수치로 시연",
], size=14.5, color=CREAM_TEXT, marker_color=AMBER)

add_rect(s, Inches(0.9), Inches(5.55), Inches(11.1), Inches(1.35), RGBColor(0x1D, 0x40, 0x3A), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
add_text(s, Inches(1.2), Inches(5.75), Inches(10.5), Inches(1.0),
         [[("웹 워크벤치 (전체 10개 탭, 실시간 재계산)", 12, CREAM_DIM, True, BODY_FONT)],
          [("claude.ai/code/artifact/7c5a27c2-d582-48db-a00b-f4c421afe933", 13.5, WHITE, False, "Consolas")]])

footer(s, "FMECA–IPS 연계체계 실증 연구  ·  전량 실측(CC BY 4.0)·가정치 구분 명시", dark=True)

prs.save("FMECA_IPS_SCANIA.pptx")
print("Saved FMECA_IPS_SCANIA.pptx, slides:", len(prs.slides))
