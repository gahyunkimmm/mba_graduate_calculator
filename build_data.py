# -*- coding: utf-8 -*-
"""
졸업이수 시뮬레이터 데이터 빌드 스크립트
------------------------------------------------
원천 데이터(학사 PDF + 학기별 시간표 Excel)를 읽어
앱이 사용하는 정규화된 JSON DB(data/*.json)를 생성합니다.

- master.json   : 학사 규정 마스터 (필수과목 / 심화과정 트랙) — PDF 기준, 정적
- offerings.json: 학기별 개설과목 — Excel '리스트형' 시트에서 자동 추출

학사 규정 PDF가 개정되면 아래 MASTER 딕셔너리를,
새 학기 시간표가 나오면 Excel 파일만 폴더에 넣고 이 스크립트를 다시 실행하세요.

    python build_data.py
"""
import json
import glob
import os
import re

import openpyxl

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")

# ──────────────────────────────────────────────────────────────────────
# 1. 졸업 요건 (학칙 기준 — 필요 시 학교 공지로 검증 후 수정)
# ──────────────────────────────────────────────────────────────────────
GRADUATION_RULES = {
    "CMBA": {
        "total_credits": 45.0,        # 졸업 총 이수학점
        "min_gpa": 2.7,               # 졸업 평량평균 하한
        "english_credits": 1.5,       # 영어강의 최소 이수학점
        "leadership_credits": 1.5,    # 리더십개발 최소 이수학점
        "concentration_credits": 9.0, # 심화과정 1개 트랙 인정 기준
    },
    "FMBA": {
        "total_credits": 45.0,
        "min_gpa": 2.7,
        "english_credits": 1.5,
        "leadership_credits": 1.5,
        "concentration_credits": 9.0,
    },
}

# ──────────────────────────────────────────────────────────────────────
# 2. 필수과목 (PDF "필수 과목" 표 기준)
#    (학정번호, 교과목명, 학점, 개설학기)
# ──────────────────────────────────────────────────────────────────────
REQUIRED = {
    "CMBA": [
        ("MBA6100", "기업경제학", 1.5, "1학기(봄)"),
        ("MBA6101", "경영통계학", 1.5, "1학기(봄)"),
        ("MBA6302", "재무회계", 3.0, "1학기(봄)"),
        ("MBA6303", "조직행동론", 3.0, "1학기(봄)"),
        ("MBA6108", "경영과학", 1.5, "1학기(여름)"),
        ("MBA6304", "재무관리", 3.0, "2학기(가을)"),
        ("MBA6309", "마케팅관리", 3.0, "2학기(가을)"),
        ("MBA6311", "경영전략", 3.0, "2학기(가을)"),
        ("MBA7167", "기업윤리와사회적책임", 1.5, "2학기(겨울)"),
        ("MBA6105", "관리회계", 1.5, "3학기(봄)"),
        ("MBA6110", "정보시스템과가치창조", 1.5, "3학기(봄)"),
        ("MBA6113", "오퍼레이션과공급망관리", 1.5, "3학기(봄)"),
        ("MBA6114", "글로벌경영전략", 1.5, "3학기(봄)"),
    ],
    "FMBA": [
        ("MBF6210", "금융경제학", 3.0, "1학기(봄)"),
        ("MBF6302", "재무회계", 3.0, "1학기(봄)"),
        ("MBF6304", "재무관리", 3.0, "1학기(봄)"),
        ("MBF6211", "금융통계학", 3.0, "1학기(여름)"),
        ("MBF6212", "금융수학", 3.0, "2학기(가을)"),
        ("MBF6214", "기업재무", 3.0, "2학기(가을)"),
        ("MBF6216", "투자론", 3.0, "2학기(가을)"),
        ("MBF6109", "마케팅", 1.5, "2학기(겨울)"),
        ("MBF6110", "ODI 매니지먼트", 1.5, "3학기(봄)"),
        ("MBF6111", "전략", 1.5, "3학기(봄)"),
        ("MBF6218", "파생상품론", 3.0, "3학기(봄)"),
        ("MBF6103", "조직행동", 1.5, "3학기(여름)"),
        ("MBF7523", "금융사례연구", 3.0, "4학기(가을)"),
    ],
}

# ──────────────────────────────────────────────────────────────────────
# 3. 심화과정(Concentration) 트랙별 과목 (PDF 심화과정 표 기준)
#    학정번호만 보관 — 학점/과목명은 OFFERINGS 또는 기본 1.5학점으로 보강
# ──────────────────────────────────────────────────────────────────────
CONCENTRATION = {
    "CMBA": {
        "마케팅": [
            "MBA7021", "MBA7110", "MBA7120", "MBA7121", "MBA7124", "MBA7128",
            "MBA7130", "MBA7157", "MBA7158", "MBA7162", "MBA7170", "MBA7197",
            "MBA7211", "MBA7212", "MBA7218", "MBA7252", "MBA7255", "MBA7256",
            "MBA7260", "MBA7262", "MBA7265", "MBA7267", "MBA7277", "MBA7279",
            "MBA7288", "MBA7290", "MBA7291", "MBA7304", "MBA7363", "MBA7364",
            "MBA7365", "MBA7378", "MBA7600", "MBA7612", "MBA7618", "MBA7621",
            "MBG6114", "MBG7120", "MBG7128", "MBG7170", "MBG7218", "MBG7219",
            "MBG7279", "MBG7288", "MBG7363", "MBG7464", "MBG7465", "MBG7466",
            "MBG7509", "MBG7618", "MBG7619", "MBG7622", "MBG7623", "MBG7629",
        ],
        "매니지먼트": [
            "MBA7101", "MBA7102", "MBA7122", "MBA7131", "MBA7132", "MBA7151",
            "MBA7152", "MBA7161", "MBA7169", "MBA7193", "MBA7205", "MBA7209",
            "MBA7210", "MBA7251", "MBA7254", "MBA7261", "MBA7263", "MBA7274",
            "MBA7278", "MBA7286", "MBA7301", "MBA7367", "MBA7382",
            "MBG7101", "MBG7122", "MBG7131", "MBG7151", "MBG7161", "MBG7193",
            "MBG7254", "MBG7367", "YJD7807",
        ],
        "재무": [
            "MBA7133", "MBA7134", "MBA7135", "MBA7136", "MBA7137", "MBA7138",
            "MBA7139", "MBA7141", "MBA7142", "MBA7147", "MBA7148", "MBA7165",
            "MBA7179", "MBA7180", "MBA7185", "MBA7186", "MBA7199", "MBA7200",
            "MBA7237", "MBA7280", "MBA7281", "MBG7237", "MBG7283",
        ],
    },
    "FMBA": {
        "금융공학": ["MBA7135", "MBA7136", "MBA7141", "MBA7142"],
        "자산운용/투자은행": ["MBA7139", "MBA7147", "MBA7185", "MBA7186"],
        "공통트랙": [
            "MBA7133", "MBA7134", "MBA7137", "MBA7138", "MBA7148", "MBA7165",
            "MBA7179", "MBA7180", "MBA7199", "MBA7200", "MBA7280", "MBA7281",
            "MBG7283",
        ],
    },
}

# FMBA 심화 인정 규칙 (PDF 안내문)
FMBA_CONCENTRATION_NOTE = (
    "① 금융공학 9학점 → 금융공학 인정  "
    "② 금융공학 + 공통트랙 합산 9학점↑ → 금융공학 인정  "
    "③ 자산운용/투자은행 + 공통트랙 합산 9학점↑ → 자산운용/투자은행 인정  "
    "※ 공통트랙 과목만 9학점은 심화과정으로 인정하지 않음"
)

# 3학점 예외 과목 (그 외 심화과목은 1.5학점)
CREDIT_OVERRIDES = {"MBG7509": 3.0, "YJD7807": 3.0}


def build_master():
    course_credits = {}
    course_names = {}

    required = {}
    for prog, rows in REQUIRED.items():
        required[prog] = []
        for code, name, cr, sem in rows:
            required[prog].append(
                {"code": code, "name": name, "credits": cr, "semester": sem}
            )
            course_credits[code] = cr
            course_names[code] = name

    # 심화과목 코드 → 트랙 역인덱스 (과정별)
    concentration_index = {"CMBA": {}, "FMBA": {}}
    for prog, tracks in CONCENTRATION.items():
        for track, codes in tracks.items():
            for code in codes:
                concentration_index[prog].setdefault(code, []).append(track)
                course_credits.setdefault(code, CREDIT_OVERRIDES.get(code, 1.5))

    return {
        "graduation_rules": GRADUATION_RULES,
        "required": required,
        "concentration": CONCENTRATION,
        "concentration_index": concentration_index,
        "fmba_concentration_note": FMBA_CONCENTRATION_NOTE,
        "course_credits": course_credits,
        "course_names": course_names,
    }


# ──────────────────────────────────────────────────────────────────────
# 4. Excel '리스트형' 시트 → 학기별 개설과목
# ──────────────────────────────────────────────────────────────────────
def term_key_from_filename(fname):
    """파일명에서 '2026-여름학기' 같은 학기 키와 계절 여부를 추출."""
    m = re.search(r"(20\d{2})[-\s]*([가-힣]+학기)", fname)
    if m:
        year, term = m.group(1), m.group(2)
        seasonal = ("여름" in term) or ("겨울" in term)
        return f"{year}-{term}", seasonal
    # 연도 없는 봄학기/가을학기 파일 처리
    if "봄학기" in fname or ("봄" in fname and "가을" not in fname):
        return "봄학기", False
    if "가을" in fname:
        return "가을학기", False
    return os.path.splitext(os.path.basename(fname))[0], False


def find_list_sheet(wb):
    for ws in wb.worksheets:
        if "리스트" in ws.title:
            return ws
    return None


def parse_offerings_sheet(ws):
    rows = list(ws.iter_rows(values_only=True))
    # 헤더 행 탐색: 'NO'와 '학정번호'가 같이 있는 행
    header_idx = None
    for i, row in enumerate(rows):
        vals = [str(c).strip() if c is not None else "" for c in row]
        if "NO" in vals and "학정번호" in vals:
            header_idx = i
            break
    if header_idx is None:
        return []

    header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    idx = {name: header.index(name) for name in header if name}

    def cell(row, name):
        i = idx.get(name)
        if i is None or i >= len(row) or row[i] is None:
            return ""
        return str(row[i]).strip()

    offered = {}
    for row in rows[header_idx + 1:]:
        code = cell(row, "학정번호")
        if not re.match(r"^[A-Z]{3}\d{4}$", code):
            continue
        name = re.sub(r"\s+", " ", cell(row, "교과목명")).strip()
        try:
            credits = float(cell(row, "학점"))
        except ValueError:
            credits = 1.5
        is_english = "영어" in cell(row, "강의언어")
        leadership = bool(cell(row, "리더십개발"))
        cmba_track = cell(row, "CMBA심화") or None
        fmba_track = cell(row, "FMBA심화") or None
        kind = cell(row, "종별")          # 필수 / 선택
        target = cell(row, "과정")        # CMBA / FMBA / CFMBA
        module = cell(row, "모듈")
        day = cell(row, "요일")
        note_raw = cell(row, "비고") or cell(row, "기타사항")
        note = re.sub(r"\s+", " ", note_raw).strip()
        if "폐강" in note:
            continue

        if code in offered:
            # 동일 과목 다른 분반 → 모듈만 병합
            if module and module not in offered[code]["modules"]:
                offered[code]["modules"].append(module)
            continue

        offered[code] = {
            "code": code,
            "name": name,
            "credits": credits,
            "kind": kind,
            "target": target,
            "is_english": is_english,
            "is_leadership": leadership,
            "cmba_track": cmba_track,
            "fmba_track": fmba_track,
            "modules": [module] if module else [],
            "day": day,
            "note": note,
        }

    return list(offered.values())


def build_offerings():
    offerings = {}
    for f in sorted(glob.glob(os.path.join(BASE, "*.xlsx"))):
        if os.path.basename(f).startswith("~$"):
            continue
        term, seasonal = term_key_from_filename(os.path.basename(f))
        wb = openpyxl.load_workbook(f, data_only=True)
        ws = find_list_sheet(wb)
        if ws is None:
            print(f"  ! '리스트형' 시트 없음: {f}")
            continue
        courses = parse_offerings_sheet(ws)
        offerings[term] = {
            "term": term,
            "seasonal": seasonal,
            "source_file": os.path.basename(f),
            "courses": courses,
        }
        print(f"  - {term}: {len(courses)}과목 ({os.path.basename(f)})")
    return offerings


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("[1/2] 학사 마스터 생성...")
    master = build_master()
    with open(os.path.join(DATA_DIR, "master.json"), "w", encoding="utf-8") as fp:
        json.dump(master, fp, ensure_ascii=False, indent=2)
    print(f"      필수: CMBA {len(master['required']['CMBA'])} / "
          f"FMBA {len(master['required']['FMBA'])}과목")

    print("[2/2] 학기별 개설과목 추출...")
    offerings = build_offerings()
    with open(os.path.join(DATA_DIR, "offerings.json"), "w", encoding="utf-8") as fp:
        json.dump(offerings, fp, ensure_ascii=False, indent=2)

    print("완료 → data/master.json, data/offerings.json")


if __name__ == "__main__":
    main()
