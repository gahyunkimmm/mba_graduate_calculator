# -*- coding: utf-8 -*-
"""
연세대 CFMBA 졸업이수 시뮬레이터
--------------------------------
데이터(필수/심화/개설과목)는 data/*.json 에서 로드합니다.
원천 데이터가 바뀌면 `python build_data.py` 로 JSON을 다시 생성하세요.
"""
import json
import os

import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")

GRADE_GPAS = {
    "A+": 4.3, "A0": 4.0, "A-": 3.7,
    "B+": 3.3, "B0": 3.0, "B-": 2.7,
    "C+": 2.3, "C0": 2.0, "C-": 1.7,
    "F": 0.0, "P": None,  # P/NP 는 평점 계산 제외
}
GRADE_OPTIONS = list(GRADE_GPAS.keys())


@st.cache_data
def load_data():
    with open(os.path.join(DATA_DIR, "master.json"), encoding="utf-8") as fp:
        master = json.load(fp)
    with open(os.path.join(DATA_DIR, "offerings.json"), encoding="utf-8") as fp:
        offerings = json.load(fp)
    return master, offerings


st.set_page_config(page_title="연세대 MBA 졸업이수 시뮬레이터", layout="wide")

try:
    MASTER, OFFERINGS = load_data()
except FileNotFoundError:
    st.error("데이터 파일이 없습니다. 먼저 터미널에서 `python build_data.py` 를 실행하세요.")
    st.stop()

# ── 세션 상태: 선택한 과목 {code: {...}} ──────────────────────────────
if "taken" not in st.session_state:
    st.session_state.taken = {}   # code -> dict(name, credits, grade, is_english, is_leadership, count_as)

taken = st.session_state.taken


def set_course(code, **fields):
    rec = taken.get(code, {})
    rec.update(fields)
    taken[code] = rec


def drop_course(code):
    taken.pop(code, None)


# ── 사이드바: 학생 설정 ──────────────────────────────────────────────
st.sidebar.header("👤 학생 정보")
program = st.sidebar.radio("소속 과정", ["CMBA", "FMBA"], horizontal=True)
rules = MASTER["graduation_rules"][program]

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ 선택 전체 초기화"):
    st.session_state.taken = {}
    st.rerun()

st.title("🎓 연세대 CFMBA 졸업이수 시뮬레이터")
st.caption("필수과목 이수 현황을 체크하고, 계절학기 개설과목을 골라 담으면 "
           "졸업요건과 심화과정 충족 여부를 실시간으로 계산합니다.")

tab_req, tab_season, tab_report = st.tabs(
    ["① 필수과목", "② 계절학기 과목 담기", "③ 졸업진단 리포트"]
)

# ──────────────────────────────────────────────────────────────────────
# ① 필수과목 이수 현황
# ──────────────────────────────────────────────────────────────────────
with tab_req:
    st.subheader(f"{program} 필수과목 이수 현황")
    st.caption("이수한 필수과목을 체크하고 성적을 입력하세요. (재수강은 동일 학정번호 기준)")
    for c in MASTER["required"][program]:
        code = c["code"]
        col1, col2, col3 = st.columns([5, 1.2, 1.5])
        with col1:
            checked = st.checkbox(
                f"**{code}**　{c['name']}　`{c['credits']}학점`　_{c['semester']}_",
                value=code in taken,
                key=f"req_{program}_{code}",
            )
        if checked:
            with col3:
                grade = st.selectbox(
                    "성적", GRADE_OPTIONS,
                    index=GRADE_OPTIONS.index(taken.get(code, {}).get("grade", "A0")),
                    key=f"reqgrade_{program}_{code}", label_visibility="collapsed",
                )
            set_course(code, name=c["name"], credits=c["credits"], grade=grade,
                       kind="필수", is_english=False, is_leadership=False, count_as=None)
        else:
            # 이 과정 필수로 담겼던 것만 해제 (선택과목 보존)
            if taken.get(code, {}).get("kind") == "필수":
                drop_course(code)

# ──────────────────────────────────────────────────────────────────────
# ② 계절학기 개설과목 (실제 시간표 기준 자동 분류)
# ──────────────────────────────────────────────────────────────────────
def track_of(course, program):
    """해당 과정 기준 이 과목의 심화 트랙명."""
    if program == "CMBA":
        return course.get("cmba_track")
    return course.get("fmba_track")


def categorize(courses, program):
    """개설과목을 분류 버킷으로 묶는다."""
    buckets = {}  # 라벨 -> list
    def add(label, c):
        buckets.setdefault(label, []).append(c)

    for c in courses:
        if c["kind"] == "필수":
            # 내 과정 필수 또는 공통 필수만
            if c["target"] in (program, "CFMBA", "공통"):
                add("📌 필수과목", c)
            continue
        tr = track_of(c, program)
        if tr:
            add(f"🎯 심화 · {tr}", c)
        elif c["is_leadership"] or c["is_english"]:
            add("🌐 영어 / 리더십개발", c)
        else:
            add("➕ 기타 선택", c)
    return buckets


with tab_season:
    st.subheader("계절학기 개설과목")
    terms = list(OFFERINGS.keys())
    term = st.selectbox("학기 선택", terms, index=len(terms) - 1)
    info = OFFERINGS[term]
    badge = "계절학기" if info["seasonal"] else "정규학기"
    st.caption(f"`{badge}` · 출처: {info['source_file']} · 총 {len(info['courses'])}과목 개설")

    buckets = categorize(info["courses"], program)
    # 보기 좋은 순서
    order = ["📌 필수과목"] \
        + sorted([k for k in buckets if k.startswith("🎯")]) \
        + ["🌐 영어 / 리더십개발", "➕ 기타 선택"]

    for label in order:
        if label not in buckets:
            continue
        with st.expander(f"{label}  ({len(buckets[label])}과목)",
                         expanded=label.startswith("🎯") or label == "📌 필수과목"):
            for c in buckets[label]:
                code = c["code"]
                tags = []
                if c["is_english"]:
                    tags.append("🔤영어")
                if c["is_leadership"]:
                    tags.append("🎒리더십")
                ctr, ftr = c.get("cmba_track"), c.get("fmba_track")
                if program == "CMBA" and ctr:
                    tags.append(f"C심화:{ctr}")
                if program == "FMBA" and ftr:
                    tags.append(f"F심화:{ftr}")
                mod = "·".join(c["modules"]) if c["modules"] else ""
                tagstr = "　".join(tags)

                col1, col2 = st.columns([5, 1.6])
                with col1:
                    checked = st.checkbox(
                        f"**{code}**　{c['name']}　`{c['credits']}학점`"
                        + (f"　[{mod}]" if mod else ""),
                        value=code in taken,
                        key=f"off_{term}_{code}",
                    )
                    if tagstr:
                        st.caption("　" + tagstr + (f"　— {c['note']}" if c["note"] else ""))
                    elif c["note"]:
                        st.caption("　— " + c["note"])

                # 영어/리더십 동시 인정 과목 → 둘 중 하나만 선택
                count_as = None
                if checked and c["is_english"] and c["is_leadership"]:
                    with col1:
                        count_as = st.radio(
                            "이 과목 인정 항목 (둘 중 하나만)",
                            ["영어", "리더십개발"],
                            horizontal=True, key=f"as_{term}_{code}",
                        )

                if checked:
                    with col2:
                        grade = st.selectbox(
                            "성적", GRADE_OPTIONS,
                            index=GRADE_OPTIONS.index(taken.get(code, {}).get("grade", "P")),
                            key=f"offgrade_{term}_{code}", label_visibility="collapsed",
                        )
                    eng = c["is_english"]
                    ld = c["is_leadership"]
                    if c["is_english"] and c["is_leadership"]:
                        eng = (count_as == "영어")
                        ld = (count_as == "리더십개발")
                    set_course(code, name=c["name"], credits=c["credits"], grade=grade,
                               kind=c["kind"], is_english=eng, is_leadership=ld,
                               cmba_track=ctr, fmba_track=ftr, count_as=count_as)
                else:
                    if taken.get(code, {}).get("kind") != "필수":
                        drop_course(code)

# ──────────────────────────────────────────────────────────────────────
# 졸업진단 계산
# ──────────────────────────────────────────────────────────────────────
def credits_of(code):
    return MASTER["course_credits"].get(code, taken.get(code, {}).get("credits", 1.5))


def diagnose():
    items = taken
    total = sum(v["credits"] for v in items.values())

    # 필수
    req_codes = [c["code"] for c in MASTER["required"][program]]
    done_req = [c for c in req_codes if c in items]
    missing_req = [c for c in MASTER["required"][program] if c["code"] not in items]
    req_credits = sum(items[c]["credits"] for c in done_req)

    # GPA (P 제외, F 포함)
    gpa_num = gpa_den = 0.0
    for v in items.values():
        g = GRADE_GPAS.get(v["grade"])
        if g is None:
            continue
        gpa_num += g * v["credits"]
        gpa_den += v["credits"]
    gpa = gpa_num / gpa_den if gpa_den else 0.0

    english = sum(v["credits"] for v in items.values() if v.get("is_english"))
    leadership = sum(v["credits"] for v in items.values() if v.get("is_leadership"))

    # 심화과정
    conc = {}
    if program == "CMBA":
        idx = MASTER["concentration_index"]["CMBA"]
        for code, v in items.items():
            for tr in idx.get(code, []):
                conc[tr] = conc.get(tr, 0.0) + v["credits"]
    else:
        idx = MASTER["concentration_index"]["FMBA"]
        sums = {"금융공학": 0.0, "자산운용/투자은행": 0.0, "공통트랙": 0.0}
        for code, v in items.items():
            for tr in idx.get(code, []):
                sums[tr] += v["credits"]
        conc = sums

    return dict(total=total, missing_req=missing_req, req_credits=req_credits,
                gpa=gpa, english=english, leadership=leadership, conc=conc)


def fmba_concentration_status(s):
    """FMBA 심화 인정 규칙 적용 → (인정 트랙 리스트, 설명)"""
    fe, ib, common = s["금융공학"], s["자산운용/투자은행"], s["공통트랙"]
    achieved = []
    if fe >= 9.0:
        achieved.append(f"금융공학 ({fe}학점)")
    elif fe + common >= 9.0 and fe > 0:
        achieved.append(f"금융공학+공통트랙 ({fe + common}학점)")
    if ib + common >= 9.0 and ib > 0:
        achieved.append(f"자산운용/투자은행+공통트랙 ({ib + common}학점)")
    return achieved


# ──────────────────────────────────────────────────────────────────────
# ③ 졸업진단 리포트
# ──────────────────────────────────────────────────────────────────────
with tab_report:
    d = diagnose()
    st.subheader(f"📊 {program} 졸업요건 진단")

    c1, c2, c3 = st.columns(3)
    c1.metric("총 이수학점", f"{d['total']:g}", f"기준 {rules['total_credits']:g}")
    c2.metric("평량평균(GPA)", f"{d['gpa']:.2f}", f"기준 {rules['min_gpa']}")
    c3.metric("필수 미이수", f"{len(d['missing_req'])}과목")

    def line(ok, text):
        (st.success if ok else st.error)(text)

    line(d["total"] >= rules["total_credits"],
         f"총 이수학점 {d['total']:g} / {rules['total_credits']:g}")
    line(len(d["missing_req"]) == 0,
         f"필수과목 이수 {d['req_credits']:g}학점 "
         f"({len(MASTER['required'][program]) - len(d['missing_req'])}"
         f"/{len(MASTER['required'][program])}과목)")
    if d["missing_req"]:
        st.caption("미이수: " + ", ".join(f"{c['code']} {c['name']}" for c in d["missing_req"]))
    line(d["gpa"] >= rules["min_gpa"], f"평량평균 {d['gpa']:.2f} / {rules['min_gpa']}")
    line(d["english"] >= rules["english_credits"],
         f"영어강의 {d['english']:g} / {rules['english_credits']:g}학점")
    line(d["leadership"] >= rules["leadership_credits"],
         f"리더십개발 {d['leadership']:g} / {rules['leadership_credits']:g}학점")

    st.markdown("---")
    st.subheader("🎯 심화과정(Concentration)")
    if program == "CMBA":
        any_done = False
        for tr in ["마케팅", "매니지먼트", "재무"]:
            cr = d["conc"].get(tr, 0.0)
            ok = cr >= rules["concentration_credits"]
            any_done = any_done or ok
            (st.success if ok else st.info)(
                f"{'🏆 ' if ok else ''}{tr}: {cr:g} / {rules['concentration_credits']:g}학점")
        if not any_done:
            st.caption("아직 9학점을 충족한 트랙이 없습니다.")
    else:
        s = d["conc"]
        for tr in ["금융공학", "자산운용/투자은행", "공통트랙"]:
            st.info(f"{tr}: {s[tr]:g}학점")
        done = fmba_concentration_status(s)
        if done:
            for t in done:
                st.success(f"🏆 인정: {t}")
        else:
            st.caption("아직 인정 기준을 충족한 조합이 없습니다.")
        st.caption("📖 " + MASTER["fmba_concentration_note"])

    st.markdown("---")
    st.subheader(f"📋 담은 과목 ({len(taken)}과목 · {d['total']:g}학점)")
    if taken:
        rows = [{
            "학정번호": code, "과목명": v["name"], "학점": v["credits"],
            "종별": v.get("kind", ""), "성적": v["grade"],
            "영어": "✓" if v.get("is_english") else "",
            "리더십": "✓" if v.get("is_leadership") else "",
        } for code, v in taken.items()]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("아직 담은 과목이 없습니다.")
