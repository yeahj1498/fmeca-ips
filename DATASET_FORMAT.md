# 데이터셋 형식 (Dataset Contract)

이 저장소의 파이프라인(`scripts/01_pipeline.py` → `02_lifecycle.py` → `04_export_transform_sample.py` → `03_export_app_data.py`)과
웹앱(`app/index.html`)은 **특정 데이터셋(SCANIA)에 하드코딩되어 있지 않다.** 아래 형식에 맞는
`config.yaml` 하나를 `datasets/<이름>/` 폴더에 넣으면 그대로 실행된다.

실제 예시: [`datasets/scania_component_x/config.yaml`](datasets/scania_component_x/config.yaml)

## 1. 고장모드(failure mode)가 여러 개인 체계

한 config.yaml은 **여러 개의 고장모드**를 가질 수 있다. 예를 들어 엔진·변속기·유압계통처럼
서로 다른 구성품이 서로 다른 센서 세트를 쓰는 체계라면, `failure_modes:` 리스트에 항목을 하나씩
추가한다 — 각 고장모드는 **자기만의 CSV 3개, 자기만의 컬럼명, 자기만의 카운터 목록**을 가진다.
SCANIA Component X처럼 구성품이 하나뿐인 데이터셋은 `failure_modes:`에 항목을 1개만 넣는다.

최종 FMECA 워크시트는 `failure_mode`와 `group` 두 축으로 행이 생긴다 — "고장모드 M, 그룹 G"가
하나의 FMECA 행이다. 즉 고장모드 3개 × 그룹 4개짜리 체계면 워크시트에 최대 12행이 나온다.

## 2. 고장모드 하나가 필요로 하는 입력 파일 3개

| 논리적 역할 | 설명 | 최소 컬럼 |
|---|---|---|
| **events** | 자산별 1행 — 관측기간(노출시간)과 고장 라벨 | 자산ID, 노출시간(숫자), 고장라벨(0/1) |
| **readouts** | 자산×시점별 1행 — 시계열 계측값(긴 포맷) | 자산ID, 시점(숫자, 자산별 오름차순), 카운터 컬럼 1개 이상 |
| **groups** | 자산별 1행 — FMECA 행을 나눌 그룹 속성 | 자산ID, 그룹 컬럼 |

- **readouts의 카운터**는 "누적값"이어야 한다(시간이 지날수록 단조증가하는 계측치 — 누적 경고횟수, 누적 가동시간 등). 파이프라인이 내부적으로 증분율(rate)·z-정규화를 계산하기 때문이다. 순간값(온도, 속도 등)을 그대로 쓰려면 `01_pipeline.py`의 드리프트 제거 로직을 데이터 성격에 맞게 고쳐야 한다.
- **events의 고장라벨**은 이진(0/1)이어야 한다. 같은 고장모드 안에서 사양·형상이 여러 개면 `groups`의 그룹 컬럼으로 나눠라(= "동일 고장모드가 그룹마다 어떻게 다른가"를 보는 구조).
- 행 수가 많아도 된다 — SCANIA 예시는 readouts 112만 행/23,550대다.

## 3. `config.yaml` 스키마

```yaml
dataset:
  short_id: <폴더명과 동일한 영문 id>
  name: <사람이 읽는 데이터셋 이름>
  component_label: <분석대상 구성품/자산 종류 이름>
  license: <라이선스>
  citation: <출처 논문/기관>
  source_url: <원본 링크>

# IPS 연계에 필요하지만 데이터에는 없는 값들. value(가정값)와 rationale(왜 이
# 값을 가정했는지)을 반드시 같이 적는다 -- 근거 없는 가정치는 신뢰할 수 없다는 게
# 이 프로젝트의 원칙이다.
assumptions:
  lead_days: {value: <조달 리드타임(일)>, rationale: "<왜 이 값인가>"}
  unit_cost_krw: {value: <단가>, rationale: "..."}
  repair_complexity: {value: <수리복잡도 등급>, rationale: "..."}
  fleet_size: {value: <가상 함대 규모>, rationale: "..."}
  daily_op_timesteps: {value: <일일 가동 time_step 환산>, rationale: "..."}

failure_modes:
  - id: <영문 id, 파일명 접두어로도 씀>
    label: <사람이 읽는 고장모드 이름>
    cause: <근본 고장원인 설명 — 데이터로 알 수 없으면 "산출 불가"라고 명시>

    files:            # 이 config.yaml 파일 기준 상대경로
      events: data_raw/xxx.csv
      readouts: data_raw/yyy.csv
      groups: data_raw/zzz.csv

    columns:
      asset_id: <자산ID 컬럼명>
      exposure_time: <노출시간 컬럼명>
      failure_label: <고장라벨 컬럼명(0/1)>
      readout_time: <시점 컬럼명>
      counters: [<카운터 컬럼명 목록>, ...]
      group_col: <FMECA 행을 나눌 주 그룹 컬럼명>
      bonus_group_col: <선택: 보조 드릴다운용 그룹 컬럼명>

    groups:            # group_col의 각 값 -> 화면표시 라벨
      <값1>: "<라벨1>"
      <값2>: "<라벨2>"

    params:
      lookback_steps: <검출 룩백 윈도, readout_time 단위>
      z_thresh: <이상치 플래그 z 임계값>
      tail_readouts_for_severity: <심각도용 "고장직전" 판독 개수>
      bonus_group_min_size: <bonus_group_col 그룹 최소 표본수>

  - id: <두 번째 고장모드가 있다면 여기에 반복>
    ...

content:           # 웹앱에 노출되는 서술형 텍스트 (사람이 직접 채워야 하는 부분)
  banner: "..."          # {name} {license} 등 치환 가능
  overview_lede: "..."   # {name} {n_vehicles} {component_label} {group_col} {n_groups} 치환 가능
  fmeca_finding: "..."   # FMECA 결과 전체에 대한 한 줄 해석(순위역전 여부 등)
  bonus_case_note: "..." # bonus_group_col을 쓴다면 그 취지 설명
  mapping_rows: [[필드, 원본파일, 의미, FMECA대응, 비고], ...]
  gap_rows: [[공백항목, 이유, 영향], ...]
```

## 4. 실행

```bash
python scripts/run_pipeline.py --dataset datasets/scania_component_x
```

내부적으로 `01_pipeline.py`(모든 고장모드를 순회하며 정제+O/S/D 계산) → `02_lifecycle.py`(RCM/LORA/보급소요/IETM/ECP) →
`04_export_transform_sample.py`(고장모드별 원본↔전처리 비교 샘플 자동선정) → `03_export_app_data.py`(웹앱용 JSON)
순서로 실행하고, `datasets/<이름>/outputs/`와 `datasets/<이름>/app_data/`를 만든 뒤
`app_data/`를 `app/data/`로 복사해 웹앱이 그 데이터셋을 바로 읽도록 만든다.

## 5. 왜 이런 구조인가

- **O/S/D 계산 로직 자체는 데이터셋과 무관하다** — "그룹별 발생률 → log 등급화", "고장직전 이상지수 → min-max 등급화", "리드타임+통계검정 → 검출력 등급화"라는 방법론은 counters/exposure/failure_label만 있으면 어떤 자산 데이터에도 적용된다.
- **고장모드를 리스트로 분리한 이유**: 실제 무기체계·설비는 구성품마다 완전히 다른 센서를 쓴다. 하나의 평평한 스키마에 모든 고장모드를 욱여넣으면 "고장모드 A엔 있고 B엔 없는 센서"를 표현할 수 없다. 그래서 각 고장모드가 자기만의 files/columns/counters를 갖게 했다 — RCM·LORA 등 IPS 연계 로직은 고장모드와 무관하게 공통이므로 `assumptions:`는 여전히 시스템(함대) 전체 공통값으로 하나만 둔다.
- **가정치(assumptions)에 rationale이 필수인 이유**: 조달 리드타임 같은 값은 어떤 데이터셋을 넣어도 저절로 나오지 않는다. 숫자만 있고 "왜 이 값인가"가 없으면 그 가정이 타당한지 아무도 검증할 수 없다 — 그래서 스키마 자체가 값과 근거를 한 쌍으로 강제한다. 웹앱 LORA/보급소요 탭에 그대로 노출된다.
- **failure_modes[].cause가 있는 이유**: FMECA는 원래 고장모드(Failure Mode)뿐 아니라 고장원인(Failure Cause)도 명시하는 게 정석이다. 실제로는 원인을 알 수 없는 익명화 데이터셋이 많으므로, 이 필드는 "모른다"고 쓰는 것도 정답이다 — 실제로 SCANIA 예시는 "산출 불가"라고 명시한다.
- **content(서술형 텍스트)는 자동화하지 않았다** — "이 데이터에 무슨 공백이 있는지", "결과를 어떻게 해석해야 하는지"는 통계로 뽑을 수 없고 사람이 도메인 판단으로 써야 하는 부분이라, 일부러 config에 사람이 채우는 자리로 남겨뒀다.
