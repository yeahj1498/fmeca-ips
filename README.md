# FMECA-IPS

실측 데이터 위에서 **FMECA(고장모드영향분석) → RCM → LORA → 보급소요 → IETM → 설계개선(ECP)**
으로 이어지는 IPS(종합군수지원) 연계 방법론을 시연하는 프로젝트입니다. 특정 데이터셋에
하드코딩되어 있지 않고, [`DATASET_FORMAT.md`](DATASET_FORMAT.md)에 정의된 형식만 맞으면
어떤 시계열 계측 + 고장기록 데이터셋이든 그대로 실행됩니다.

- **웹 워크벤치(라이브 데모)**: [SCANIA Component X 연계체계](https://claude.ai/code/artifact/7c5a27c2-d582-48db-a00b-f4c421afe933)
- **현재 실행 예시**: [SCANIA Component X](https://doi.org/10.5878/jvb5-d390) — CC BY 4.0, 실제 트럭 23,550대의 엔진계통 구성품 수리기록·계측데이터 (Kharazian et al., *Scientific Data*, 2025)

> 이 데이터로 계산한 O/S/D·RPN·RCM·LORA·보급소요·IETM·ECP 수치는 실측 기반이지만,
> 리드타임·단가·함대규모 같은 IPS 파라미터는 방법론 시연을 위한 가정치입니다.
> 실제 군 장비에 적용 가능함을 주장하는 것이 아니라, **방법론과 연계 구조 자체를
> 검증하는 것**이 목적입니다.

## 빠른 시작

```bash
pip install pandas numpy scipy pyyaml
python scripts/run_pipeline.py --dataset datasets/scania_component_x
```

`data_raw/` 원본 CSV(SCANIA Component X, 1.2GB — 라이선스상 이 저장소에는 포함하지
않음, [01_dataset_card.md](datasets/scania_component_x/01_dataset_card.md)에서
다운로드 경로 확인)만 채워 넣으면 O/S/D 계산부터 IPS 연계, 웹앱용 JSON 생성까지
한 번에 실행됩니다. 실행 후 `app/index.html`을 열면 그 결과를 바로 볼 수 있습니다.

## 다른 데이터셋 넣기

`datasets/<이름>/config.yaml` 하나로 컬럼 매핑·그룹·임계값·IPS 가정치·웹앱 서술문을
전부 정의합니다. 고장모드가 여러 개(엔진/변속기/유압계통처럼 센서 종류부터 다른 구성품들)인
체계도 `failure_modes:` 리스트로 지원하며, 모든 IPS 가정치는 값과 함께 "왜 이 값을
가정했는지"(rationale)를 반드시 명시합니다. 자세한 스키마와 이유는 [DATASET_FORMAT.md](DATASET_FORMAT.md) 참고.

## 저장소 구조

```
DATASET_FORMAT.md          데이터셋 형식(계약) 문서
scripts/
  dataset_config.py        config.yaml 로더 (공통)
  01_pipeline.py            정제 6단계 + O/S/D + RPN/RI 계산 (고장모드 여러 개면 순회 후 결합)
  02_lifecycle.py            RCM/LORA/보급소요/IETM/ECP 연계
  04_export_transform_sample.py   고장모드별 원본→전처리 비교 샘플 자동 선정
  03_export_app_data.py      웹앱용 JSON 생성
  run_pipeline.py            위 4개를 순서대로 실행하는 오케스트레이터
  03_ips_feedback_linkage.js 웹앱의 피드백 재계산 로직(참고용 추출본)
datasets/scania_component_x/
  config.yaml               SCANIA 데이터셋 계약 인스턴스
  data_raw/                 원본 CSV (gitignore, 라이선스상 미포함)
  outputs/                  파이프라인 계산 결과 (CSV/JSON)
  app_data/                 웹앱이 읽는 JSON
app/index.html              데이터셋 무관 웹 워크벤치 (11개 탭)
doc/                        수식 정리 Word 문서 (HAZOP guide word 포함)
ppt/                        15슬라이드 발표자료
flow2/, tree/               표준 프로그래밍 플로우차트 · 파일트리 SVG
captures/                   핵심 코드 스니펫 스크린샷
```

## 방법론 요약

- **O(발생도)**: 그룹별 수리율(수리건수÷노출시간)을 log 스케일 10등급화, Poisson exact 신뢰구간으로 검증
- **S(심각도, 근사)**: 결과심각도(안전/가동중단/비용) 기록이 없는 데이터셋이 대부분이라, 고장 직전 신호이탈 강도를 대리지표로 사용 — HAZOP guide word(MORE/LESS)와 오차율(%)로 "무엇을 대신 측정했는지" 투명하게 표기
- **D(검출도)**: 조기경보 리드타임 + 이항검정으로 우연 수준과의 통계적 유의성 검증
- **RPN/RI**: 곱셈식(O×S×D)과 가중합산식(0.4O+0.4S+0.2D) 둘 다 계산해 극단값 왜곡 여부 비교
- **RCM→LORA→보급소요→IETM→ECP**: 위 등급값을 그대로 if/else 결정로직에 대입 — 코드가 곧 방법론

전체 수식과 "왜 이렇게 계산하는가" 논리 설명은 [doc/FMECA_IPS_공식정리.docx](doc/FMECA_IPS_공식정리.docx)에 정리되어 있습니다.

## 라이선스

- 코드: 별도 명시 없는 한 이 저장소의 코드는 자유롭게 사용 가능
- 데이터: SCANIA Component X 데이터셋은 [CC BY 4.0](https://doi.org/10.5878/jvb5-d390), Kharazian et al. (2025) 인용 필요
