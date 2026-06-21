# 연세대 CFMBA 졸업이수 시뮬레이터

연세대 MBA(CMBA/FMBA) 졸업요건과 심화과정(Concentration) 충족 여부를
실시간으로 점검하는 Streamlit 앱입니다.

## 주요 기능

- **필수과목 이수 현황** 체크 및 성적 입력 (재수강 = 동일 학정번호 기준)
- **계절학기 개설과목 자동 분류** — 실제 시간표(Excel) 기준으로
  필수 / 심화트랙(마케팅·매니지먼트·재무 / 금융공학·공통트랙·자산운용) /
  영어·리더십개발 / 기타 선택으로 자동 분류
- **졸업진단 리포트** — 총학점·평량평균·영어·리더십·필수·심화과정 충족 여부
  (FMBA 심화 인정 규칙 반영)

## 구조

```
app.py            # Streamlit UI (데이터/로직 분리, data/*.json 로드)
build_data.py     # 원천 데이터(PDF·Excel) → data/*.json 생성
data/
  master.json     # 학사 마스터: 필수과목 + 심화과정 트랙 (PDF 기준)
  offerings.json  # 학기별 개설과목 (Excel '리스트형' 시트 자동 추출)
requirements.txt
*.xlsx, *.pdf     # 원천 데이터
```

데이터와 코드를 분리해, 학사규정이나 시간표가 바뀌어도
원천 파일만 교체 후 `build_data.py`만 다시 돌리면 됩니다.

## 실행 방법

```bash
pip install -r requirements.txt

# (원천 데이터가 바뀌었을 때만) JSON DB 재생성
python build_data.py

# 앱 실행
streamlit run app.py
```

## 데이터 갱신

- **새 학기 시간표**: 해당 `.xlsx`(‘리스트형’ 시트 포함)를 폴더에 넣고
  `python build_data.py` 실행 → `offerings.json` 자동 갱신
- **학사규정 개정**: `build_data.py` 상단의 `REQUIRED` / `CONCENTRATION` /
  `GRADUATION_RULES` 수정 후 재실행

> 졸업요건 수치(총 45학점 등)는 학칙 기준 추정치이며,
> 실제 졸업 사정은 소속 MBA 행정실 공지로 최종 확인하시기 바랍니다.
