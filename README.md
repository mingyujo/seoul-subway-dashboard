# 서울 지하철 승하차 대시보드

서울 열린데이터광장의 지하철 승하차 데이터를 Python으로 분석하고, 그 결과를 바닐라 웹 프런트엔드로 필터링·시각화하는 정적 대시보드입니다.

**Live Demo**: https://mingyujo.github.io/seoul-subway-dashboard/

## 사용 기술
- Python, pandas — 데이터 정제·집계
- HTML, CSS, JavaScript (ES Modules) — 웹 프런트엔드
- Chart.js — 차트 시각화

## 전체 구조
```
원본 CSV (data/raw/CARD_SUBWAY_MONTH_202608.csv)
    ↓ python scripts/analyze.py
data/processed/dashboard_data.json
    ↓ fetch (js/data.js)
HTML/JavaScript 대시보드 (index.html + js/app.js + Chart.js)
    ↓
GitHub Pages 배포
```
브라우저는 원본 CSV를 직접 읽거나 분석하지 않습니다. CSV 파싱·정제·집계는 전부 `scripts/analyze.py`(Python/pandas)에서 수행하며, 웹은 그 결과물인 `data/processed/dashboard_data.json`만 `fetch`합니다.

## 주요 기능
- 날짜 범위·노선 필터
- KPI 5개: 총 승차, 총 하차, 총 이용량, 평일 일평균, 주말 일평균
- 이용객 상위 10개 역 / 노선별 이용량 / 날짜별 이용량 추이 차트 3종
- 일자별 상세 데이터 표
- 반응형 레이아웃 및 다크모드(`prefers-color-scheme`) 지원

## 데이터 출처와 분석 기간
- 출처: 서울 열린데이터광장 "서울시 지하철호선별 역별 승하차 인원 정보"
- 원본 파일: `data/raw/CARD_SUBWAY_MONTH_202608.csv`
- 분석 기간: 2026년 8월 1일 ~ 2026년 8월 31일 (31일)
- 원본 CSV 값은 수정하지 않으며, 정제·타입 변환은 `scripts/analyze.py`가 메모리 상에서만 수행해 JSON으로 저장합니다.

## 검증된 기준값
`scripts/analyze.py`는 아래 값과 계산 결과가 다르면 JSON을 생성하지 않고 실패합니다(자세한 계산 과정은 `docs/ANALYSIS_BASELINE.md` 참고).

| 항목 | 값 |
|---|---|
| 유효 행 수 | 19,133 |
| 전체 승차 | 208,329,561 |
| 전체 하차 | 207,340,153 |
| 전체 이용량 | 415,669,714 |

## 로컬 실행 방법
```bash
pip install -r requirements.txt
python scripts/analyze.py
python -m http.server 8000
```
`data/processed/dashboard_data.json`이 생성/갱신된 뒤, 안내된 주소(`http://localhost:8000`)를 브라우저로 열면 대시보드가 표시됩니다. 브라우저의 `fetch`로 로컬 JSON을 읽기 때문에 `index.html`을 `file://`로 직접 열면 로드가 차단될 수 있어 정적 서버 사용을 권장합니다.

## 테스트 방법
```bash
python -m unittest discover -s tests -p "test_*.py"
npm test
```
Python 테스트는 `scripts/analyze.py`(CSV 정제·집계·기준값 대조)를, `npm test`는 `js/analysis.js`(화면 표시용 날짜·노선 필터, KPI, 상위 역, 노선별·날짜별 집계)를 검증합니다. 웹 실행 자체에는 Node.js/npm이 필요하지 않으며, `npm test`는 선택 사항입니다.

## GitHub Pages 배포 방식
GitHub Pages는 **Python을 실행하지 않습니다**. `scripts/analyze.py`로 미리 생성해 커밋해 둔 `data/processed/dashboard_data.json`을 그대로 정적 파일로 서빙할 뿐이며, 저장소의 `main` 브랜치 루트(`/`)를 그대로 배포합니다. 원본 데이터를 갱신하려면 로컬(또는 CI)에서 `python scripts/analyze.py`를 다시 실행해 JSON을 갱신한 뒤 커밋·push해야 합니다.

## 요구사항 관리
프로젝트 요구사항은 Notion 페이지에서 먼저 확인한 뒤, 그 내용을 그대로 `docs/REQUIREMENTS.md`에 동기화해 저장소 안에서 추적합니다(비공개 Notion URL이나 개인정보는 포함하지 않음).

## 개발 과정에서 사용한 도구
UI/UX 개선 단계에서 `ui-ux-pro-max`라는 Claude Code Skill을 참고용으로 사용했습니다. 이는 개발자의 로컬 작업 환경에서만 쓰인 디자인 참고 도구이며, **배포된 사이트의 실행 의존성이 아닙니다** — 사이트는 순수 HTML/CSS/JavaScript와 Chart.js만으로 동작합니다.

## 파일 구성
- `scripts/analyze.py` — CSV 정제·집계·JSON 생성 (Python/pandas)
- `tests/test_analysis.py` — Python 분석 파이프라인 단위/통합 테스트
- `data/raw/` — 원본 CSV (수정하지 않음)
- `data/processed/dashboard_data.json` — 웹이 fetch하는 분석 결과
- `index.html` — 화면 뼈대와 필터 UI
- `css/style.css` — 레이아웃, 반응형, 다크모드 스타일
- `js/data.js` — JSON 로딩(fetch) 및 데이터 계약(필수 키/필드) 검증
- `js/analysis.js` — DOM에 의존하지 않는 순수 함수(화면 표시용 날짜·노선 필터, KPI, 상위 역, 노선별·날짜별 집계)
- `js/app.js` — 필터 이벤트 처리, KPI/차트/표 갱신
- `tests/analysis.test.js` — `js/analysis.js` 단위 테스트(선택 사항, Node 필요)
- `docs/REQUIREMENTS.md` — Notion에서 동기화한 요구사항 원문
- `docs/PLAN.md` — 구현 계획 이력
- `docs/ANALYSIS_BASELINE.md` — 원본 CSV 독립 분석 기준값
