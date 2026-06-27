# -*- coding: utf-8 -*-
"""
연세대 CFMBA 졸업이수 시뮬레이터
데이터: data/master.json, data/offerings.json (build_data.py로 생성)
"""
import json
import os
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")


@st.cache_data
def load_data():
    with open(os.path.join(DATA_DIR, "master.json"), encoding="utf-8") as fp:
        master = json.load(fp)
    with open(os.path.join(DATA_DIR, "offerings.json"), encoding="utf-8") as fp:
        offerings = json.load(fp)
    return master, offerings


st.set_page_config(
    page_title="연세 MBA 졸업이수 시뮬레이터",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 커스텀 CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 카드형 과목 행 */
.course-row { padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
/* 태그 뱃지 */
.badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-right: 4px;
}
.badge-eng  { background:#e8f4fd; color:#1a6fa8; }
.badge-ld   { background:#fdf3e8; color:#b05a00; }
.badge-conc { background:#edf7ed; color:#1e6e1e; }
.badge-req  { background:#fdecea; color:#a01010; }
/* 진도 라벨 */
.prog-label { font-size: 0.82rem; color: #555; margin-bottom: 2px; }
/* 섹션 헤더 */
.section-title {
    font-size: 1rem; font-weight: 700;
    color: #333; margin: 16px 0 6px;
    padding-left: 8px;
    border-left: 4px solid #4C72FF;
}
</style>
""", unsafe_allow_html=True)

try:
    MASTER, OFFERINGS = load_data()
except FileNotFoundError:
    st.error("⚠️ 데이터 파일이 없습니다. 터미널에서 `python build_data.py`를 실행하세요.")
    st.stop()

# ── 세션 상태 ─────────────────────────────────────────────────────────
if "taken" not in st.session_state:
    st.session_state.taken = {}  # code -> {name, credits, kind, is_english, is_leadership, cmba_track, fmba_track}


def set_course(code, **fields):
    rec = st.session_state.taken.get(code, {})
    rec.update(fields)
    st.session_state.taken[code] = rec


def drop_course(code):
    st.session_state.taken.pop(code, None)


taken = st.session_state.taken

# ── 사이드바: 과정 선택 + 실시간 요건 현황 ───────────────────────────
with st.sidebar:
    st.markdown("## 🎓 졸업이수 시뮬레이터")
    program = st.radio("소속 과정", ["CMBA", "FMBA"], horizontal=True, label_visibility="collapsed")
    rules = MASTER["graduation_rules"][program]
    st.markdown(f"**{program}** 과정")

    st.markdown("---")

    # 실시간 집계
    total = sum(v["credits"] for v in taken.values())
    req_list = MASTER["required"][program]
    missing_req = [c for c in req_list if c["code"] not in taken]
    english = sum(v["credits"] for v in taken.values() if v.get("is_english"))
    leadership = sum(v["credits"] for v in taken.values() if v.get("is_leadership"))

    def pct(cur, goal):
        return min(int(cur / goal * 100), 100)

    def status_icon(ok):
        return "✅" if ok else "🔲"

    # 총 학점 프로그레스
    st.markdown(f'<div class="prog-label">총 이수학점 {total:g} / {rules["total_credits"]:g}</div>',
                unsafe_allow_html=True)
    st.progress(pct(total, rules["total_credits"]))

    st.markdown("---")
    st.markdown("**졸업요건 체크리스트**")

    req_ok = len(missing_req) == 0
    eng_ok = english >= rules["english_credits"]
    ld_ok  = leadership >= rules["leadership_credits"]

    st.markdown(f"{status_icon(req_ok)} 필수과목 {len(req_list)-len(missing_req)}/{len(req_list)}과목")
    if missing_req:
        with st.expander("미이수 필수과목"):
            for c in missing_req:
                st.caption(f"- {c['name']}")

    st.markdown(f"{status_icon(eng_ok)} 영어강의 {english:g} / {rules['english_credits']:g}학점")
    st.markdown(f"{status_icon(ld_ok)} 리더십개발 {leadership:g} / {rules['leadership_credits']:g}학점")

    # 심화과정 미니 현황
    st.markdown("---")
    st.markdown("**심화과정(Concentration)**")
    if program == "CMBA":
        idx = MASTER["concentration_index"]["CMBA"]
        conc = {}
        for code, v in taken.items():
            for tr in idx.get(code, []):
                conc[tr] = conc.get(tr, 0.0) + v["credits"]
        for tr in ["마케팅", "매니지먼트", "재무"]:
            cr = conc.get(tr, 0.0)
            ok = cr >= rules["concentration_credits"]
            st.markdown(f"{status_icon(ok)} {tr} {cr:g} / {rules['concentration_credits']:g}학점")
    else:
        idx = MASTER["concentration_index"]["FMBA"]
        sums = {"금융공학": 0.0, "자산운용/투자은행": 0.0, "공통트랙": 0.0}
        for code, v in taken.items():
            for tr in idx.get(code, []):
                sums[tr] += v["credits"]
        for tr, cr in sums.items():
            st.caption(f"{tr}: {cr:g}학점")

    st.markdown("---")
    if st.button("🗑️ 전체 초기화", use_container_width=True):
        st.session_state.taken = {}
        st.rerun()

# ── 메인 탭 ──────────────────────────────────────────────────────────
tab_req, tab_season, tab_report = st.tabs(
    ["📋 필수과목", "🗓️ 계절학기 과목", "📊 졸업진단 리포트"]
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────
def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'


def track_of(course, prog):
    return course.get("cmba_track") if prog == "CMBA" else course.get("fmba_track")


def categorize(courses, prog):
    buckets = {}
    for c in courses:
        if c["kind"] == "필수":
            if c["target"] in (prog, "CFMBA", "공통"):
                buckets.setdefault("📌 필수과목", []).append(c)
            continue
        tr = track_of(c, prog)
        if tr:
            buckets.setdefault(f"🎯 심화 · {tr}", []).append(c)
        elif c["is_leadership"] or c["is_english"]:
            buckets.setdefault("🌐 영어 / 리더십개발", []).append(c)
        else:
            buckets.setdefault("➕ 기타 선택", []).append(c)
    return buckets


# ──────────────────────────────────────────────────────────────────────
# 탭 ①: 필수과목
# ──────────────────────────────────────────────────────────────────────
with tab_req:
    st.markdown(f"### {program} 필수과목 이수 현황")
    st.caption("이수 완료한 과목에 체크하세요. 사이드바에서 진도가 실시간으로 갱신됩니다.")

    # 학기별로 그룹핑
    by_sem = {}
    for c in MASTER["required"][program]:
        by_sem.setdefault(c["semester"], []).append(c)

    for sem, courses in by_sem.items():
        st.markdown(f'<div class="section-title">{sem}</div>', unsafe_allow_html=True)
        for c in courses:
            code = c["code"]
            col_chk, col_info = st.columns([0.5, 9.5])
            with col_chk:
                checked = st.checkbox("", value=code in taken, key=f"req_{program}_{code}",
                                      label_visibility="collapsed")
            with col_info:
                label = f"**{c['name']}**　`{c['credits']}학점`　<span style='color:#888;font-size:0.82rem'>{code}</span>"
                st.markdown(label, unsafe_allow_html=True)

            if checked:
                set_course(code, name=c["name"], credits=c["credits"],
                           kind="필수", is_english=False, is_leadership=False)
            else:
                if taken.get(code, {}).get("kind") == "필수":
                    drop_course(code)


# ──────────────────────────────────────────────────────────────────────
# 탭 ②: 계절학기
# ──────────────────────────────────────────────────────────────────────
with tab_season:
    terms = list(OFFERINGS.keys())
    cols_top = st.columns([3, 7])
    with cols_top[0]:
        term = st.selectbox("학기", terms, index=len(terms) - 1, label_visibility="collapsed")
    info = OFFERINGS[term]
    with cols_top[1]:
        st.caption(f"📂 {info['source_file']} · 총 **{len(info['courses'])}과목** 개설")

    buckets = categorize(info["courses"], program)
    order = (["📌 필수과목"]
             + sorted(k for k in buckets if k.startswith("🎯"))
             + ["🌐 영어 / 리더십개발", "➕ 기타 선택"])

    for label in order:
        if label not in buckets:
            continue
        with st.expander(f"{label}  ({len(buckets[label])}과목)",
                         expanded="필수" in label or "심화" in label):
            for c in buckets[label]:
                code = c["code"]
                ctr, ftr = c.get("cmba_track"), c.get("fmba_track")
                mod = "·".join(c["modules"]) if c["modules"] else ""

                col_chk, col_info = st.columns([0.5, 9.5])
                with col_chk:
                    checked = st.checkbox("", value=code in taken,
                                          key=f"off_{term}_{code}",
                                          label_visibility="collapsed")
                with col_info:
                    # 과목명 + 학점 + 모듈
                    name_line = f"**{c['name']}**　`{c['credits']}학점`"
                    if mod:
                        name_line += f"　<span style='color:#888;font-size:0.8rem'>[{mod}]</span>"
                    st.markdown(name_line + f"　<span style='color:#aaa;font-size:0.78rem'>{code}</span>",
                                unsafe_allow_html=True)

                    # 뱃지 행
                    badges = ""
                    if c["is_english"]:
                        badges += badge("영어강의", "badge-eng")
                    if c["is_leadership"]:
                        badges += badge("리더십개발", "badge-ld")
                    if program == "CMBA" and ctr:
                        badges += badge(f"심화:{ctr}", "badge-conc")
                    if program == "FMBA" and ftr:
                        badges += badge(f"심화:{ftr}", "badge-conc")
                    if badges:
                        st.markdown(badges, unsafe_allow_html=True)
                    if c["note"]:
                        st.caption(f"ℹ️ {c['note']}")

                # 영어+리더십 동시 해당 → 인정 항목 선택
                count_as = None
                if checked and c["is_english"] and c["is_leadership"]:
                    count_as = st.radio(
                        "이 과목을 어느 항목으로 인정할까요?",
                        ["영어강의", "리더십개발"],
                        horizontal=True, key=f"as_{term}_{code}",
                    )

                if checked:
                    eng = c["is_english"]
                    ld  = c["is_leadership"]
                    if c["is_english"] and c["is_leadership"]:
                        eng = (count_as == "영어강의")
                        ld  = (count_as == "리더십개발")
                    set_course(code, name=c["name"], credits=c["credits"],
                               kind=c["kind"], is_english=eng, is_leadership=ld,
                               cmba_track=ctr, fmba_track=ftr)
                else:
                    if taken.get(code, {}).get("kind") != "필수":
                        drop_course(code)


# ──────────────────────────────────────────────────────────────────────
# 탭 ③: 졸업진단 리포트
# ──────────────────────────────────────────────────────────────────────
with tab_report:
    st.markdown(f"### 📊 {program} 졸업요건 진단")

    total_r   = sum(v["credits"] for v in taken.values())
    req_list  = MASTER["required"][program]
    missing_r = [c for c in req_list if c["code"] not in taken]
    english_r = sum(v["credits"] for v in taken.values() if v.get("is_english"))
    ld_r      = sum(v["credits"] for v in taken.values() if v.get("is_leadership"))

    # 요약 지표 카드
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 이수학점", f"{total_r:g}", f"목표 {rules['total_credits']:g}학점")
    m2.metric("필수 미이수", f"{len(missing_r)}과목",
              f"{len(req_list)-len(missing_r)}/{len(req_list)} 완료")
    m3.metric("영어강의", f"{english_r:g}학점", f"기준 {rules['english_credits']:g}학점")
    m4.metric("리더십개발", f"{ld_r:g}학점", f"기준 {rules['leadership_credits']:g}학점")

    st.markdown("---")

    # 요건별 상세
    def req_row(ok, label, detail=""):
        icon = "✅" if ok else "❌"
        color = "#1a7a1a" if ok else "#c0392b"
        bg = "#f0faf0" if ok else "#fdf0f0"
        st.markdown(
            f'<div style="background:{bg};border-radius:8px;padding:10px 14px;margin:6px 0;">'
            f'<span style="font-size:1.1rem">{icon}</span> '
            f'<span style="font-weight:600;color:{color}">{label}</span>'
            + (f'<span style="color:#666;font-size:0.85rem;margin-left:8px">{detail}</span>' if detail else "")
            + "</div>",
            unsafe_allow_html=True,
        )

    req_row(total_r >= rules["total_credits"],
            f"총 이수학점 {total_r:g} / {rules['total_credits']:g}학점")
    req_row(len(missing_r) == 0,
            f"필수과목 {len(req_list)-len(missing_r)}/{len(req_list)}과목 이수",
            ("미이수: " + ", ".join(c["name"] for c in missing_r)) if missing_r else "")
    req_row(english_r >= rules["english_credits"],
            f"영어강의 {english_r:g} / {rules['english_credits']:g}학점")
    req_row(ld_r >= rules["leadership_credits"],
            f"리더십개발 {ld_r:g} / {rules['leadership_credits']:g}학점")

    st.markdown("---")
    st.markdown("### 🎯 심화과정(Concentration)")

    if program == "CMBA":
        idx = MASTER["concentration_index"]["CMBA"]
        conc = {}
        for code, v in taken.items():
            for tr in idx.get(code, []):
                conc[tr] = conc.get(tr, 0.0) + v["credits"]
        for tr in ["마케팅", "매니지먼트", "재무"]:
            cr = conc.get(tr, 0.0)
            ok = cr >= rules["concentration_credits"]
            pv = min(int(cr / rules["concentration_credits"] * 100), 100)
            label = f"{'🏆 ' if ok else ''}{tr}　{cr:g} / {rules['concentration_credits']:g}학점"
            st.markdown(f'<div class="prog-label">{label}</div>', unsafe_allow_html=True)
            st.progress(pv)
    else:
        idx = MASTER["concentration_index"]["FMBA"]
        sums = {"금융공학": 0.0, "자산운용/투자은행": 0.0, "공통트랙": 0.0}
        for code, v in taken.items():
            for tr in idx.get(code, []):
                sums[tr] += v["credits"]
        for tr, cr in sums.items():
            pv = min(int(cr / rules["concentration_credits"] * 100), 100)
            st.markdown(f'<div class="prog-label">{tr}　{cr:g}학점</div>', unsafe_allow_html=True)
            st.progress(pv)

        fe, ib, common = sums["금융공학"], sums["자산운용/투자은행"], sums["공통트랙"]
        achieved = []
        if fe >= 9.0:
            achieved.append(f"금융공학 ({fe:g}학점)")
        elif fe + common >= 9.0 and fe > 0:
            achieved.append(f"금융공학 + 공통트랙 ({fe+common:g}학점)")
        if ib + common >= 9.0 and ib > 0:
            achieved.append(f"자산운용/투자은행 + 공통트랙 ({ib+common:g}학점)")
        if achieved:
            for a in achieved:
                st.success(f"🏆 심화과정 인정: {a}")
        else:
            st.info("아직 인정 기준을 충족한 조합이 없습니다.")
        st.caption("📖 " + MASTER["fmba_concentration_note"])

    st.markdown("---")
    st.markdown(f"### 📋 담은 과목 ({len(taken)}과목 · {total_r:g}학점)")
    if taken:
        rows = [
            {
                "학정번호": code,
                "과목명": v["name"],
                "학점": v["credits"],
                "종별": v.get("kind", ""),
                "영어": "✓" if v.get("is_english") else "",
                "리더십": "✓" if v.get("is_leadership") else "",
            }
            for code, v in taken.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("아직 담은 과목이 없습니다. 위 탭에서 과목을 선택하세요.")
