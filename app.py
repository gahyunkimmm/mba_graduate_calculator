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

# 학기별 순서 및 계절 매핑
# req_keys: master.json의 semester 필드값과 매칭
# season:   계절학기 선택과목 풀 (여름/겨울/None)
SEMESTER_CONFIG = {
    "CMBA": [
        {"label": "1학기 (봄)",          "req_keys": ["1학기(봄)"],   "season": None,  "regular": None},
        {"label": "여름 계절학기",        "req_keys": ["1학기(여름)"], "season": "여름", "regular": None},
        {"label": "2학기 (가을)",         "req_keys": ["2학기(가을)"], "season": None,  "regular": None},
        {"label": "겨울 계절학기",        "req_keys": ["2학기(겨울)"], "season": "겨울", "regular": None},
        {"label": "3학기 (봄)",          "req_keys": ["3학기(봄)"],   "season": None,  "regular": "봄학기"},
        {"label": "3학기 여름 계절학기",  "req_keys": ["3학기(여름)"], "season": "여름", "regular": None},
        {"label": "4학기 (가을)",         "req_keys": ["4학기(가을)"], "season": None,  "regular": "가을학기"},
        {"label": "4학기 겨울 계절학기",  "req_keys": ["4학기(겨울)"], "season": "겨울", "regular": None},
    ],
    "FMBA": [
        {"label": "1학기 (봄)",          "req_keys": ["1학기(봄)"],   "season": None,  "regular": None},
        {"label": "1학기 여름 계절학기",  "req_keys": ["1학기(여름)"], "season": "여름", "regular": None},
        {"label": "2학기 (가을)",         "req_keys": ["2학기(가을)"], "season": None,  "regular": None},
        {"label": "2학기 겨울 계절학기",  "req_keys": ["2학기(겨울)"], "season": "겨울", "regular": None},
        {"label": "3학기 (봄)",          "req_keys": ["3학기(봄)"],   "season": None,  "regular": "봄학기"},
        {"label": "3학기 여름 계절학기",  "req_keys": ["3학기(여름)"], "season": "여름", "regular": None},
        {"label": "4학기 (가을)",         "req_keys": ["4학기(가을)"], "season": None,  "regular": "가을학기"},
        {"label": "4학기 겨울 계절학기",  "req_keys": ["4학기(겨울)"], "season": "겨울", "regular": None},
    ],
}


# 봄/가을 학기 고정 리더십개발 과목 (각 과목 평생 1회만 수강 가능)
LEADERSHIP_COURSES = [
    {"code": "LDR001", "name": "리더십개발: 제주도",    "credits": 1.5,
     "is_leadership": True, "is_english": False, "kind": "선택", "once": True,
     "synthetic": True, "cmba_track": None, "fmba_track": None, "note": ""},
    {"code": "LDR002", "name": "리더십개발: 백두대간I",  "credits": 1.5,
     "is_leadership": True, "is_english": False, "kind": "선택", "once": True,
     "synthetic": True, "cmba_track": None, "fmba_track": None, "note": ""},
    {"code": "LDR003", "name": "리더십개발: 백두대간II", "credits": 1.5,
     "is_leadership": True, "is_english": False, "kind": "선택", "once": True,
     "synthetic": True, "cmba_track": None, "fmba_track": None, "note": ""},
]

# 여름학기 CKJ 과목 (계절학기 최대학점 별개)
CKJ_COURSE = {
    "code": "CKJ001", "name": "CKJ Asia Business Field Study", "credits": 3.0,
    "is_leadership": False, "is_english": True, "kind": "선택",
    "synthetic": True, "cmba_track": None, "fmba_track": None,
    "note": "계절학기 최대 수강학점과 별개",
}

# 계절학기 선택과목 학점 상한 (3.0학점) — 아래 코드는 상한 제외
SEASONAL_CREDIT_CAP = 3.0
SEASONAL_CAP_EXEMPT = {"CKJ001"}  # CKJ Asia Business Field Study 제외


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
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.badge { display:inline-block; padding:1px 8px; border-radius:10px;
         font-size:0.72rem; font-weight:600; margin-right:4px; }
.badge-req  { background:#fdecea; color:#a01010; }
.badge-eng  { background:#e8f4fd; color:#1a6fa8; }
.badge-ld   { background:#fdf3e8; color:#b05a00; }
.badge-conc { background:#edf7ed; color:#1e6e1e; }
.sub-hd { font-size:0.83rem; font-weight:700; color:#444;
          margin:14px 0 6px; padding-left:8px; border-left:3px solid #4C72FF; }
.prog-label { font-size:0.82rem; color:#555; margin-bottom:2px; }
</style>
""", unsafe_allow_html=True)

try:
    MASTER, OFFERINGS = load_data()
except FileNotFoundError:
    st.error("⚠️ 데이터 파일 없음. 터미널에서 `python build_data.py`를 먼저 실행하세요.")
    st.stop()

# 계절학기 선택과목 풀 — 여름/겨울별로 통합, 연도 최신 우선
SEASONAL_ELEC: dict[str, dict] = {"여름": {}, "겨울": {}}
for _term in sorted(OFFERINGS.keys()):
    _season = "여름" if "여름" in _term else "겨울" if "겨울" in _term else None
    if _season:
        for _c in OFFERINGS[_term]["courses"]:
            if _c["kind"] == "선택":
                SEASONAL_ELEC[_season][_c["code"]] = _c

# 정규학기 선택과목 풀 — 봄학기/가을학기 파일에서 로드
REGULAR_ELEC: dict[str, dict] = {"봄학기": {}, "가을학기": {}}
for _term, _data in OFFERINGS.items():
    if _term == "봄학기":
        for _c in _data["courses"]:
            if _c["kind"] == "선택":
                REGULAR_ELEC["봄학기"][_c["code"]] = _c
    elif _term == "가을학기":
        for _c in _data["courses"]:
            if _c["kind"] == "선택":
                REGULAR_ELEC["가을학기"][_c["code"]] = _c

# ── 세션 상태 ─────────────────────────────────────────────────────────
if "taken" not in st.session_state:
    st.session_state.taken = {}

taken: dict = st.session_state.taken


def set_course(code, **fields):
    rec = taken.get(code, {})
    rec.update(fields)
    taken[code] = rec


def drop_course(code):
    taken.pop(code, None)


def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'


def render_badges(c, program, is_required=False):
    """뱃지 HTML 문자열 반환"""
    b = ""
    if is_required:
        b += badge("필수", "badge-req")
    if c.get("is_english"):
        b += badge("영어강의", "badge-eng")
    if c.get("is_leadership"):
        b += badge("리더십개발", "badge-ld")
    tr = c.get("cmba_track") if program == "CMBA" else c.get("fmba_track")
    if tr:
        b += badge(f"심화:{tr}", "badge-conc")
    return b


# ── 상단: 과정 선택 (사이드바가 접혀 있어도 항상 보이도록 메인 영역에 배치) ──
st.markdown("#### 🎓 연세 MBA 졸업이수 시뮬레이터")
program = st.radio("소속 과정", ["CMBA", "FMBA"], horizontal=True, key="program")
rules = MASTER["graduation_rules"][program]
st.markdown("---")

# ── 사이드바: 실시간 진도 ──────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 🎓 {program} 진도")
    st.markdown("---")

    total   = sum(v["credits"] for v in taken.values())
    rq_list = MASTER["required"][program]
    missing = [c for c in rq_list if c["code"] not in taken]
    english = sum(v["credits"] for v in taken.values() if v.get("is_english"))
    ldship  = sum(v["credits"] for v in taken.values() if v.get("is_leadership"))

    def pct(cur, goal): return min(int(cur / goal * 100), 100)
    def ok_icon(flag): return "✅" if flag else "🔲"

    st.markdown(f'<div class="prog-label">총 이수학점　{total:g} / {rules["total_credits"]:g}</div>',
                unsafe_allow_html=True)
    st.progress(pct(total, rules["total_credits"]))

    st.markdown("---")
    st.markdown("**졸업요건**")
    req_ok = len(missing) == 0
    st.markdown(f"{ok_icon(req_ok)} 필수과목  {len(rq_list) - len(missing)}/{len(rq_list)}과목")
    if missing:
        with st.expander("미이수 필수과목"):
            for c in missing:
                st.caption(f"- {c['name']}")
    st.markdown(f"{ok_icon(english >= rules['english_credits'])} 영어강의  {english:g}/{rules['english_credits']:g}학점")
    st.markdown(f"{ok_icon(ldship >= rules['leadership_credits'])} 리더십개발  {ldship:g}/{rules['leadership_credits']:g}학점")

    st.markdown("---")
    st.markdown("**심화과정(Concentration)**")
    if program == "CMBA":
        idx = MASTER["concentration_index"]["CMBA"]
        conc: dict = {}
        for _code, _v in taken.items():
            for _tr in idx.get(_code, []):
                conc[_tr] = conc.get(_tr, 0.0) + _v["credits"]
        for tr in ["마케팅", "매니지먼트", "재무"]:
            cr = conc.get(tr, 0.0)
            ok = cr >= rules["concentration_credits"]
            st.markdown(f"{ok_icon(ok)} {tr}  {cr:g}/{rules['concentration_credits']:g}학점")
    else:
        idx = MASTER["concentration_index"]["FMBA"]
        sums = {"금융공학": 0.0, "자산운용/투자은행": 0.0, "공통트랙": 0.0}
        for _code, _v in taken.items():
            for _tr in idx.get(_code, []):
                sums[_tr] = sums.get(_tr, 0.0) + _v["credits"]
        for tr, cr in sums.items():
            st.caption(f"{tr}: {cr:g}학점")

    st.markdown("---")
    if st.button("🗑️ 전체 초기화", use_container_width=True):
        st.session_state.taken = {}
        st.rerun()


# ── 화면 전환 (탭 대신 버튼으로 → 프로그램적 이동 가능) ────────────────
if "view" not in st.session_state:
    st.session_state.view = "plan"

nav1, nav2 = st.columns(2)
with nav1:
    if st.button("📋 학기별 이수계획", use_container_width=True,
                 type="primary" if st.session_state.view == "plan" else "secondary"):
        st.session_state.view = "plan"
        st.rerun()
with nav2:
    if st.button("📊 졸업진단 리포트", use_container_width=True,
                 type="primary" if st.session_state.view == "report" else "secondary"):
        st.session_state.view = "report"
        st.rerun()
st.markdown("---")


# ────────────────────────────────────────────────────────────────────
# 화면 1: 학기별 이수계획
# ────────────────────────────────────────────────────────────────────
if st.session_state.view == "plan":
    st.markdown(f"### {program} 학기별 이수계획")
    st.caption("각 학기를 펼쳐 필수과목과 계절학기 선택과목을 함께 확인하고 이수 여부를 체크하세요.")

    # 해당 과정의 필수과목 코드 집합 — 계절학기 선택과목에서 중복 제외
    req_set = {c["code"] for c in MASTER["required"][program]}

    for sem_idx, sem_cfg in enumerate(SEMESTER_CONFIG[program]):
        sem_label = sem_cfg["label"]
        season    = sem_cfg["season"]
        req_keys  = sem_cfg["req_keys"]

        # 이 학기의 필수과목
        sem_req = [c for c in MASTER["required"][program] if c["semester"] in req_keys]

        # 이 학기의 선택과목
        regular = sem_cfg.get("regular")  # "봄학기", "가을학기", or None
        sem_elec: list = []
        if season:
            # 계절학기: 여름/겨울 공통 선택과목 풀 (평생 1회)
            sem_elec = [{**c, "sem_idx": sem_idx, "once": True}
                        for code, c in SEASONAL_ELEC[season].items()
                        if code not in req_set]
            if season == "여름":
                sem_elec.append({**CKJ_COURSE, "sem_idx": sem_idx, "once": True})
        else:
            # 정규학기(봄/가을): 정규 선택과목(있는 경우) + 리더십개발 (평생 1회)
            if regular and REGULAR_ELEC.get(regular):
                sem_elec = [{**c, "sem_idx": sem_idx, "once": True}
                            for code, c in REGULAR_ELEC[regular].items()
                            if code not in req_set]
            sem_elec += [{**lc, "sem_idx": sem_idx} for lc in LEADERSHIP_COURSES]

        if not sem_req and not sem_elec:
            continue

        # 이 섹션에 '속한' 과목인지 (평생 1회 과목은 담은 학기에서만 카운트)
        def _here(c, _idx=sem_idx):
            rec = taken.get(c["code"])
            if rec is None:
                return False
            if c.get("once"):
                return rec.get("sem_idx") == _idx
            return True

        # 계절학기 선택과목 학점 사용량 (상한 제외 과목 제외)
        seasonal_cr_used = 0.0
        if season:
            seasonal_cr_used = sum(
                taken[c["code"]]["credits"]
                for c in sem_elec
                if _here(c) and c["code"] not in SEASONAL_CAP_EXEMPT
            )

        # 익스팬더 제목: 체크 현황
        checked_req   = sum(1 for c in sem_req  if c["code"] in taken)
        checked_elec  = sum(1 for c in sem_elec if _here(c))
        credits_done  = (sum(taken[c["code"]]["credits"] for c in sem_req  if c["code"] in taken)
                       + sum(taken[c["code"]]["credits"] for c in sem_elec if _here(c)))
        elec_suffix   = f" + 선택 {checked_elec}과목" if sem_elec else ""
        exp_title     = (f"{sem_label}　｜　"
                         f"필수 {checked_req}/{len(sem_req)}{elec_suffix}　"
                         f"· {credits_done:g}학점")

        # 모든 학기 기본 펼침 (선택 시에도 닫히지 않게)
        with st.expander(exp_title, expanded=True):

            # ── 필수과목 ─────────────────────────────────────────────
            if sem_req:
                st.markdown('<div class="sub-hd">📌 필수과목</div>', unsafe_allow_html=True)
                for c in sem_req:
                    code    = c["code"]
                    chk_key = f"req_{program}_{code}"
                    col_chk, col_info = st.columns([0.5, 9.5])
                    with col_chk:
                        checked = st.checkbox("", value=code in taken, key=chk_key,
                                              label_visibility="collapsed")
                    with col_info:
                        st.markdown(
                            f"**{c['name']}** {badge('필수', 'badge-req')}"
                            f"　`{c['credits']}학점`　<span style='color:#aaa;font-size:0.78rem'>{code}</span>",
                            unsafe_allow_html=True,
                        )

                    if checked:
                        set_course(code, name=c["name"], credits=c["credits"],
                                   kind="필수", is_english=False, is_leadership=False)
                    else:
                        if taken.get(code, {}).get("kind") == "필수":
                            drop_course(code)

            # ── 선택과목 (계절학기만) ────────────────────────────────
            if sem_elec:
                st.markdown('<div class="sub-hd">🗂️ 선택과목</div>', unsafe_allow_html=True)
                if season:
                    cap_remaining = max(0.0, SEASONAL_CREDIT_CAP - seasonal_cr_used)
                    st.caption(
                        f"실제 개설 시간표 기준 · {len(sem_elec)}과목 "
                        f"· 선택 {seasonal_cr_used:g}/3.0학점 사용"
                        + (f" · 잔여 {cap_remaining:g}학점" if cap_remaining > 0 else " · ⚠️ 학점 상한 도달")
                    )
                elif regular and REGULAR_ELEC.get(regular):
                    st.caption(f"실제 개설 시간표 기준 · {len(sem_elec)}과목")
                else:
                    st.caption(f"{len(sem_elec)}과목")

                # 트랙별 분류
                buckets: dict = {}
                for c in sem_elec:
                    tr = c.get("cmba_track") if program == "CMBA" else c.get("fmba_track")
                    if tr:
                        buckets.setdefault(f"심화 · {tr}", []).append(c)
                    elif c.get("is_leadership") or c.get("is_english"):
                        buckets.setdefault("영어 / 리더십개발", []).append(c)
                    else:
                        buckets.setdefault("기타 선택", []).append(c)

                track_order = (
                    sorted(k for k in buckets if k.startswith("심화"))
                    + ["영어 / 리더십개발", "기타 선택"]
                )

                for tr_label in track_order:
                    if tr_label not in buckets:
                        continue
                    cnt_taken = sum(1 for c in buckets[tr_label] if _here(c))
                    hdr = f"**{tr_label}** ({cnt_taken}/{len(buckets[tr_label])}과목)"
                    st.markdown(hdr)

                    for c in buckets[tr_label]:
                        code = c["code"]
                        once = c.get("once")
                        rec  = taken.get(code)
                        # 다른 학기에서 이미 수강 → 잠금
                        once_locked = bool(once and rec is not None
                                           and rec.get("sem_idx") != sem_idx)
                        # 계절학기 3.0학점 상한 초과 → 미선택 과목 잠금
                        cap_locked = (
                            season is not None
                            and code not in SEASONAL_CAP_EXEMPT
                            and not _here(c)
                            and seasonal_cr_used + c["credits"] > SEASONAL_CREDIT_CAP
                        )
                        locked = once_locked or cap_locked
                        # 위젯 키: 섹션별 고유 (학기마다 같은 과목이 나오므로 sem_idx 포함)
                        chk_key = f"elec_s{sem_idx}_{code}"

                        col_chk, col_info = st.columns([0.5, 9.5])
                        with col_chk:
                            checked = st.checkbox(
                                "", value=_here(c), key=chk_key, disabled=locked,
                                label_visibility="collapsed",
                            )
                        with col_info:
                            bgs = render_badges(c, program)
                            note_html = (f"　<span style='color:#888;font-size:0.76rem'>{c['note']}</span>"
                                         if c.get("note") else "")
                            lock_html = ""
                            if once_locked:
                                tk_label = SEMESTER_CONFIG[program][rec["sem_idx"]]["label"]
                                lock_html = (f"　<span style='color:#c0392b;font-size:0.74rem'>"
                                             f"🔒 {tk_label}에 이미 수강</span>")
                            elif cap_locked:
                                lock_html = (f"　<span style='color:#e67e22;font-size:0.74rem'>"
                                             f"⚠️ 계절학기 3.0학점 초과</span>")
                            # 리더십/CKJ 등 합성 코드는 숨기고, 실제 학정번호만 표시
                            code_html = ("" if c.get("synthetic")
                                         else f"　<span style='color:#aaa;font-size:0.78rem'>{code}</span>")
                            st.markdown(
                                f"**{c['name']}** {bgs}　`{c['credits']}학점`"
                                f"{code_html}{note_html}{lock_html}",
                                unsafe_allow_html=True,
                            )

                        if locked:
                            continue  # 다른 학기 소유 → 이 섹션에서 변경 금지

                        # 영어+리더십 동시 해당 → 인정 항목 선택
                        count_as = None
                        if checked and c.get("is_english") and c.get("is_leadership"):
                            count_as = st.radio(
                                "인정 항목 (하나만 선택)",
                                ["영어강의", "리더십개발"],
                                horizontal=True, key=f"as_s{sem_idx}_{code}",
                            )

                        if checked:
                            eng = c.get("is_english", False)
                            ld  = c.get("is_leadership", False)
                            if eng and ld:
                                eng = (count_as == "영어강의")
                                ld  = (count_as == "리더십개발")
                            set_course(code, name=c["name"], credits=c["credits"],
                                       kind="선택", is_english=eng, is_leadership=ld,
                                       once=bool(once), sem_idx=sem_idx,
                                       cmba_track=c.get("cmba_track"),
                                       fmba_track=c.get("fmba_track"))
                        else:
                            if taken.get(code, {}).get("kind") == "선택":
                                drop_course(code)

    # ── 입력 완료 → 리포트 이동 버튼 ──────────────────────────────────
    st.markdown("---")
    if st.button("✅ 입력 완료 · 졸업진단 리포트 보기 →",
                 type="primary", use_container_width=True):
        st.session_state.view = "report"
        st.rerun()


# ────────────────────────────────────────────────────────────────────
# 화면 2: 졸업진단 리포트
# ────────────────────────────────────────────────────────────────────
if st.session_state.view == "report":
    st.markdown(f"### 📊 {program} 졸업요건 진단")

    total_r   = sum(v["credits"] for v in taken.values())
    rq_list_r = MASTER["required"][program]
    missing_r = [c for c in rq_list_r if c["code"] not in taken]
    english_r = sum(v["credits"] for v in taken.values() if v.get("is_english"))
    ld_r      = sum(v["credits"] for v in taken.values() if v.get("is_leadership"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 이수학점",  f"{total_r:g}",           f"목표 {rules['total_credits']:g}학점")
    m2.metric("필수 미이수",  f"{len(missing_r)}과목",  f"{len(rq_list_r)-len(missing_r)}/{len(rq_list_r)} 완료")
    m3.metric("영어강의",     f"{english_r:g}학점",     f"기준 {rules['english_credits']:g}학점")
    m4.metric("리더십개발",   f"{ld_r:g}학점",          f"기준 {rules['leadership_credits']:g}학점")

    st.markdown("---")

    def req_row(ok, label, detail=""):
        color = "#1a7a1a" if ok else "#c0392b"
        bg    = "#f0faf0" if ok else "#fdf0f0"
        icon  = "✅" if ok else "❌"
        detail_html = (f'<span style="color:#666;font-size:0.85rem;margin-left:8px">{detail}</span>'
                       if detail else "")
        st.markdown(
            f'<div style="background:{bg};border-radius:8px;padding:10px 14px;margin:5px 0">'
            f'{icon} <span style="font-weight:600;color:{color}">{label}</span>{detail_html}</div>',
            unsafe_allow_html=True,
        )

    req_row(total_r  >= rules["total_credits"],
            f"총 이수학점  {total_r:g} / {rules['total_credits']:g}학점")
    req_row(len(missing_r) == 0,
            f"필수과목  {len(rq_list_r)-len(missing_r)}/{len(rq_list_r)}과목 이수",
            ("미이수: " + ", ".join(c["name"] for c in missing_r)) if missing_r else "")
    req_row(english_r >= rules["english_credits"],
            f"영어강의  {english_r:g} / {rules['english_credits']:g}학점")
    req_row(ld_r      >= rules["leadership_credits"],
            f"리더십개발  {ld_r:g} / {rules['leadership_credits']:g}학점")

    st.markdown("---")
    st.markdown("### 🎯 심화과정(Concentration)")

    if program == "CMBA":
        idx = MASTER["concentration_index"]["CMBA"]
        conc_r: dict = {}
        for code, v in taken.items():
            for tr in idx.get(code, []):
                conc_r[tr] = conc_r.get(tr, 0.0) + v["credits"]
        for tr in ["마케팅", "매니지먼트", "재무"]:
            cr = conc_r.get(tr, 0.0)
            ok = cr >= rules["concentration_credits"]
            label = f"{'🏆 ' if ok else ''}{tr}　{cr:g} / {rules['concentration_credits']:g}학점"
            st.markdown(f'<div class="prog-label">{label}</div>', unsafe_allow_html=True)
            st.progress(min(int(cr / rules["concentration_credits"] * 100), 100))
    else:
        idx = MASTER["concentration_index"]["FMBA"]
        sums_r = {"금융공학": 0.0, "자산운용/투자은행": 0.0, "공통트랙": 0.0}
        for code, v in taken.items():
            for tr in idx.get(code, []):
                sums_r[tr] = sums_r.get(tr, 0.0) + v["credits"]
        for tr, cr in sums_r.items():
            st.markdown(f'<div class="prog-label">{tr}　{cr:g}학점</div>', unsafe_allow_html=True)
            st.progress(min(int(cr / rules["concentration_credits"] * 100), 100))
        fe, ib, common = sums_r["금융공학"], sums_r["자산운용/투자은행"], sums_r["공통트랙"]
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
        st.dataframe(
            [{"학정번호": code, "과목명": v["name"], "학점": v["credits"],
              "종별": v.get("kind",""), "영어": "✓" if v.get("is_english") else "",
              "리더십": "✓" if v.get("is_leadership") else ""}
             for code, v in taken.items()],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("아직 담은 과목이 없습니다. 학기별 이수계획 탭에서 과목을 선택하세요.")

    st.markdown("---")
    if st.button("🔄 이수과목 다시 선택하기", use_container_width=True):
        st.session_state.taken = {}
        st.session_state.view = "plan"
        st.rerun()
