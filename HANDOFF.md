# 핸드오프 메모 — 연세 CFMBA 졸업이수 시뮬레이터

다른 환경(Claude Cowork 등)에서 이 작업을 그대로 이어받기 위한 컨텍스트 문서.

## 개요

- **목적**: 연세대 MBA(CMBA/FMBA) 졸업요건·심화과정 충족 여부를 실시간 점검하는 Streamlit 앱
- **저장소**: https://github.com/gahyunkimmm/mba_graduate_calculator (main)
- **배포**: https://mba-graduate-calculator.streamlit.app (main 푸시 시 자동 재배포)
- **로컬 경로**: `C:\Users\btkgh\Downloads\졸업이수시뮬레이션`

## 구조

```
app.py            # Streamlit UI (data/*.json 로드, 로직 분리)
build_data.py     # 원천 데이터(PDF·Excel) → data/*.json 생성
data/
  master.json     # 학사 마스터: 필수과목 + 심화과정 트랙 (PDF 기준, 정적)
  offerings.json  # 학기별 개설과목 (Excel '리스트형' 시트 자동 추출)
requirements.txt  # streamlit>=1.33, openpyxl>=3.1
*.xlsx, *.pdf     # 원천 데이터
```

데이터/코드 분리: 시간표가 바뀌면 새 `.xlsx`를 폴더에 넣고 `python build_data.py`만 다시 실행.

## 최근 완료된 작업

- **2화면 구성**: `학기별 이수계획` / `졸업진단 리포트` — 상단 버튼으로 전환,
  계획 화면 하단에 "입력 완료 → 리포트 보기" 버튼
- **과정 선택(CMBA/FMBA)을 메인 화면 상단에 배치** (사이드바가 모바일에서 접혀도 항상 보이도록)
- **FMBA 8개 학기 전부 표시**: 1봄 · 1여름 · 2가을 · 2겨울 · 3봄 · 3여름 · 4가을 · 4겨울
- **계절학기 4회 독립 선택**(1여름·2겨울·3여름·4겨울): 각 섹션에서 따로 선택,
  단 모든 과목은 평생 1회만 수강(한 학기에서 담으면 다른 학기에서 🔒 잠금)
- **고정 추가 과목**:
  - 리더십개발 3과목(제주도 / 백두대간 I / 백두대간 II) → 모든 봄·가을 학기 (각 평생 1회)
  - CKJ Asia Business Field Study (3학점) → 모든 여름 계절학기 (계절 최대학점과 별개)
- **한 줄 표시**: 과목명 + 뱃지(필수/영어/리더십/심화) + 학점 + 학정번호를 한 줄에
- **모바일**: 사이드바 기본 접힘(`initial_sidebar_state="collapsed"`)

## 핵심 구현 메모

- `taken` = `st.session_state.taken`, 과목코드(기본 코드) 기준 dict
- 위젯 키: 필수 `req_{program}_{code}`, 선택 `elec_s{sem_idx}_{code}` (섹션별 고유 → 중복 키 충돌 방지)
- 평생 1회 과목은 record에 `sem_idx` 기록 → 담은 학기 외에는 `disabled`로 잠금
- 합성 코드(리더십 `LDR00x`, CKJ `CKJ001`)는 `synthetic` 플래그로 학정번호 숨김
- 졸업요건: 총 45학점 / 평량 2.7 / 영어 1.5 / 리더십 1.5 / 심화 9.0 (학칙 추정치)

## 검증

`streamlit.testing.v1.AppTest`로 확인:
- FMBA 선택 시 8개 학기 모두 렌더, 예외 없음
- 한 계절학기에서 과목 체크 → 동일 과목이 다른 계절학기에서 `disabled`(반복 수강 차단)

## 다음 후보 작업

- 졸업요건 수치(총 45학점 등)를 소속 MBA 행정실 공지로 최종 검증
- 심화과정(Concentration) 트랙 과목 코드 최신 학칙 기준으로 재검토
- 필요 시 학기별 수강 학점 상한(계절학기 최대 등) 경고 표시 추가
