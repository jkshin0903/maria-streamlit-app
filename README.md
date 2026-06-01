# R&S Entertainment — 오락기기 자산 추적·관리 시스템

**R&S Entertainment Services**의 오락기기(핀볼, 당구대, 주크박스, 비디오 게임 등)를 구매·설치·이동·수리·처분까지 추적하고, 현황 보고서와 수익성 분석을 제공하는 **Streamlit 웹 애플리케이션**입니다.

인디애나주 Lafayette, Fort Wayne, Rensselaer 지역의 본사·창고·고객 사업장(레스토랑, 바, 아케이드 등)을 대상으로 한 자산 관리 시나리오를 구현합니다. 백엔드 데이터베이스는 **MariaDB**(MySQL 호환)를 사용합니다.

---

## 팀 *Maria*

<table>
  <tr>
    <td align="center" width="150px">
      <a href="https://github.com/sh-byun" target="_blank">
        <img src="https://avatars.githubusercontent.com/u/266037836?v=4" alt="sh-byun 프로필" width="100px;" style="border-radius: 50%;"/>
        <br />
        <sub><b>sh-byun</b></sub>
      </a>
    </td>
    <td align="center" width="150px">
      <a href="https://github.com/jkshin0903" target="_blank">
        <img src="https://avatars.githubusercontent.com/u/217357056?v=4" alt="jkshin0903 프로필" width="100px;" style="border-radius: 50%;"/>
        <br />
        <sub><b>jkshin0903</b></sub>
      </a>
    </td>
        <td align="center" width="150px">
      <a href="https://github.com/Jungmin-yonsei" target="_blank">
        <img src="https://avatars.githubusercontent.com/u/243153797?v=4" alt="Jungmin-yonsei 프로필" width="100px;" style="border-radius: 50%;"/>
        <br />
        <sub><b>Jungmin-yonsei</b></sub>
      </a>
    </td>
    <td align="center" width="150px">
      <a href="https://github.com/hayoungju08" target="_blank">
        <img src="https://avatars.githubusercontent.com/u/289516006?v=4" alt="kimfield 프로필" width="100px;" style="border-radius: 50%;"/>
        <br />
        <sub><b>hayoungju08</b></sub>
      </a>
    </td>
  </tr>
</table>

<br/>

## 이 프로젝트에서 하려는 것

| 구분 | 화면 코드 | 설명 |
|------|-----------|------|
| **입력** | SCR-IN-01 | **구매 발주서(Purchase Order)** 작성·저장·팩스 전송 |
| **입력** | SCR-IN-02 | **설치 / 제거 지시서(Move Order)** — 기기 이동·설치·제거 스케줄링 |
| **보고서** | SCR-RPT-01 | **설치 기기 현황** — 사업장·유형·상태별 필터, Excel 내보내기 |
| **보고서** | SCR-RPT-02 | **연간 구매 목록** — 벤더·연도별 구매 집계 |
| **보고서** | SCR-RPT-03 | **수익성 · 수리 분석** — 매출 대비 수리비, ROI 등 |

추가로 다음 기능을 포함합니다.

- **역할 기반 접근 제어(RBAC)** — 사이드바에서 사용자를 전환하면 메뉴와 데이터 범위가 달라집니다 (본사 매니저, 사이트 매니저, 외부 회계사 등).
- **한/영 이중 언어** — 사이드바 토글 또는 진입점 파일로 기본 언어 선택.
- **Excel 내보내기** — 보고서 결과를 `.xlsx`로 다운로드.

---

## 프로젝트 구조

```
maria-streamlit/
├── app.py                 # 영어 기본 진입점
├── app_ko.py              # 한국어 기본 진입점
├── seed.py                # 스키마 확장 + 샘플 데이터 적재
├── requirements.txt       # Python 의존성
├── .streamlit/
│   └── config.toml        # Streamlit 테마·서버 설정
├── lib/                   # 공통 라이브러리
│   ├── app_main.py        # 앱 부트스트랩, 네비게이션, RBAC 라우팅
│   ├── db.py              # MariaDB 연결, 쿼리, 캐시된 마스터 데이터 조회
│   ├── ui.py              # 공통 UI(테마 CSS, 앱바, 사용자 디렉터리)
│   ├── i18n.py            # 한/영 번역 문자열
│   └── export.py          # DataFrame → Excel 변환
└── screens/               # 화면별 Streamlit 페이지
    ├── po_entry.py        # SCR-IN-01  구매 발주서
    ├── move_order.py      # SCR-IN-02  설치/제거 지시서
    ├── rpt_installed.py   # SCR-RPT-01 설치 기기 현황
    ├── rpt_purchases.py   # SCR-RPT-02 연간 구매 목록
    └── rpt_profitability.py  # SCR-RPT-03 수익성·수리 분석
```

### 모듈 역할

- **`app.py` / `app_ko.py`** — `lib.app_main.run()`을 호출하는 얇은 진입점입니다. 기본 언어만 다릅니다.
- **`lib/app_main.py`** — 페이지 설정, 사이드바(언어·사용자 선택), 역할에 따른 메뉴 구성, `st.navigation`으로 화면 라우팅.
- **`lib/db.py`** — `company` 데이터베이스에 PyMySQL로 연결합니다. 세션 단위 연결 풀링과 `@st.cache_data` 기반 마스터 데이터 캐시를 제공합니다.
- **`lib/ui.py`** — R&S 브랜드 스타일 CSS, 앱 헤더, 시뮬레이션 사용자 목록 및 권한(`scope`: `all` / `site` / `reports`).
- **`lib/i18n.py`** — `t("키")` 형태의 경량 i18n. 모든 UI 문자열이 `(English, 한국어)` 튜플로 정의되어 있습니다.
- **`screens/*`** — 각 업무 화면의 폼·검색·결과 표시·저장 로직.
- **`seed.py`** — 기존 `company` 스키마에 필요한 컬럼·테이블을 **멱등(idempotent)** 으로 추가한 뒤, GP3 요구 시나리오에 맞는 결정적(deterministic) 샘플 데이터를 적재합니다.

---

## 사전 요구 사항

- **Python 3.10+** (권장)
- **MariaDB** (또는 MySQL) — `company` 데이터베이스 및 기본 테이블(`vendor`, `product`, `machine`, `business_location` 등)이 이미 존재해야 합니다.
- `seed.py`는 누락된 컬럼·테이블을 추가하고 데이터를 다시 채웁니다.

---

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 데이터베이스 연결 설정

연결 정보는 `lib/db.py`와 `seed.py` 상단의 `DB_CONFIG` / `DB` 딕셔너리에 정의되어 있습니다. 로컬 MariaDB 환경에 맞게 `host`, `port`, `user`, `password`, `database`를 수정하세요.

기본값:

| 항목 | 값 |
|------|-----|
| host | `127.0.0.1` |
| port | `3306` |
| database | `company` |

### 3. 샘플 데이터 적재

```bash
python seed.py
```

스키마를 확장하고 기존 트랜잭션 데이터를 비운 뒤 샘플 데이터를 다시 넣습니다. **운영 DB에서는 실행하지 마세요.**

### 4. 앱 실행

```bash
# 영어 기본
streamlit run app.py

# 한국어 기본
streamlit run app_ko.py
```

브라우저에서 Streamlit UI가 열립니다. 사이드바에서 **언어**와 **로그인 사용자**를 변경할 수 있습니다.

---

## 사용자 역할 (시뮬레이션)

실제 인증은 없으며, 사이드바 선택으로 역할을 바꿉니다.

| 사용자 | 역할 | 접근 범위 |
|--------|------|-----------|
| Marge Brooks | 사업운영 매니저 | 전체 입력 + 보고서 |
| Reid Lewis | 대표 (President) | 전체 입력 + 보고서 |
| Mike Anderson | 사이트 매니저 — Lafayette | Move Order + 보고서 (Lafayette 사업장) |
| Mark Davis | 사이트 매니저 — Fort Wayne | Move Order + 보고서 (Fort Wayne 사업장) |
| Foster Reed | 사이트 매니저 — Rensselaer | Move Order + 보고서 (Rensselaer 사업장) |
| Sandra Cole (CPA) | 외부 회계사 | 보고서만 |

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| UI | [Streamlit](https://streamlit.io/) 1.51+ |
| DB | MariaDB / MySQL (`PyMySQL`) |
| 데이터 처리 | pandas |
| Excel | openpyxl |

---

## 참고

- `.streamlit/config.toml` — R&S 브랜드 컬러(`#0F2A4A`) 기반 테마, headless 서버, `runOnSave` 등 Streamlit 설정.
- `seed.py`의 `TODAY` 기준일(2026-05-29)과 `random.seed(42)`로 재현 가능한 샘플 데이터를 생성합니다.
- DB 비밀번호가 소스에 하드코딩되어 있습니다. 배포 시 환경 변수나 secrets로 분리하는 것을 권장합니다.
