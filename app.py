# -*- coding: utf-8 -*-
"""
연세대 CFMBA 졸업이수 시뮬레이터
데이터: data/master.json, data/offerings.json (build_data.py로 생성)
"""
import json
import os
import streamlit as st
import streamlit.components.v1 as components

# Streamlit의 실제 스크롤 컨테이너(stMain)를 직접 타깃
_SCROLL_TOP = """<script>
(function(){
    var doc = window.parent.document;
    function _t() {
        var el = doc.querySelector('[data-testid="stMain"]') || doc.querySelector('.main');
        if (el) el.scrollTop = 0;
    }
    _t();
    setTimeout(_t, 100);
    setTimeout(_t, 300);
    setTimeout(_t, 600);
})();
</script>"""

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

    seasonal_elec: dict = {"여름": {}, "겨울": {}}
    for term in sorted(offerings.keys()):
        season = "여름" if "여름" in term else "겨울" if "겨울" in term else None
        if season:
            for c in offerings[term]["courses"]:
                if c["kind"] == "선택":
                    seasonal_elec[season][c["code"]] = c

    regular_elec: dict = {"봄학기": {}, "가을학기": {}}
    for term, data in offerings.items():
        if term in ("봄학기", "가을학기"):
            for c in data["courses"]:
                if c["kind"] == "선택":
                    regular_elec[term][c["code"]] = c

    return master, offerings, seasonal_elec, regular_elec


st.set_page_config(
    page_title="연세 MBA 졸업이수 시뮬레이터",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.sub-hd { font-size:0.83rem; font-weight:700; color:#444;
          margin:10px 0 2px; padding-left:8px; border-left:3px solid #4C72FF; }
.prog-label { font-size:0.82rem; color:#555; margin-bottom:2px; }
.course-blocked { color:#bbb; font-size:0.86rem; padding:1px 0 1px 4px;
                  line-height:1.4; }
.track-hd { font-size:0.76rem; font-weight:600; color:#999;
            margin:8px 0 2px; padding-left:6px;
            border-left:2px solid #ddd; letter-spacing:0.02em; }

/* ── 과목 목록 여백 최소화 ── */
div[data-testid="stCheckbox"] {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
div[data-testid="stCheckbox"] > label {
    display: flex !important;
    flex-wrap: nowrap !important;
    align-items: flex-start !important;
    gap: 6px !important;
    line-height: 1.3 !important;
    min-height: 22px !important;
    padding: 0 !important;
}
/* 체크박스 바로 다음에 체크박스가 올 때만 간격 축소 (서브헤더 제외) */
[data-testid="element-container"]:has([data-testid="stCheckbox"])
+ [data-testid="element-container"]:has([data-testid="stCheckbox"]) {
    margin-top: -22px !important;
}
/* 컬럼: 항상 수평 배치 */
div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: stretch !important;
}
div[data-testid="stColumn"] {
    min-width: 0 !important;
    overflow: hidden !important;
}

/* ── 모바일 반응형 ── */
@media (max-width: 768px) {
    /* 컨테이너 오버플로 방지 */
    section[data-testid="stMain"] { overflow-x: hidden !important; }
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    /* 네비 버튼: 텍스트 줄바꿈 허용, 크기 축소 */
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"] {
        font-size: 0.74rem !important;
        padding: 0.3rem 0.3rem !important;
        min-height: 2rem !important;
        height: auto !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }
    /* 엑스팬더 제목 */
    .streamlit-expanderHeader p { font-size: 0.8rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.0rem !important; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    /* 체크박스 텍스트 */
    div[data-testid="stCheckbox"] > label { font-size: 0.82rem !important; }
    /* 컬럼 gap 축소 */
    div[data-testid="stHorizontalBlock"] { gap: 0.4rem !important; }
}
</style>
""", unsafe_allow_html=True)

try:
    MASTER, OFFERINGS, SEASONAL_ELEC, REGULAR_ELEC = load_data()
except FileNotFoundError:
    st.error("⚠️ 데이터 파일 없음. 터미널에서 `python build_data.py`를 먼저 실행하세요.")
    st.stop()

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


def compute_stats(prog):
    """taken을 한 번만 순회해 총학점·영어·리더십·미이수필수 반환."""
    total = english = ldship = 0.0
    for v in taken.values():
        total += v["credits"]
        if v.get("is_english"):    english += v["credits"]
        if v.get("is_leadership"): ldship  += v["credits"]
    missing = [c for c in MASTER["required"][prog] if c["code"] not in taken]
    return total, english, ldship, missing


st.markdown("#### 🎓 연세 MBA 졸업이수 시뮬레이터")
program = st.session_state.get("program", "CMBA")
rules = MASTER["graduation_rules"][program]
st.markdown("---")

# ── 사이드바: 실시간 진도 ──────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 🎓 {program} 진도")
    st.markdown("---")

    total, english, ldship, missing = compute_stats(program)
    rq_list = MASTER["required"][program]

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
    if "confirm_reset" not in st.session_state:
        st.session_state.confirm_reset = False
    if st.session_state.confirm_reset:
        st.warning("정말 초기화할까요?")
        c1, c2 = st.columns(2)
        if c1.button("예, 초기화", use_container_width=True):
            st.session_state.taken = {}
            st.session_state.confirm_reset = False
            st.rerun()
        if c2.button("취소", use_container_width=True):
            st.session_state.confirm_reset = False
            st.rerun()
    else:
        if st.button("🗑️ 전체 초기화", use_container_width=True):
            st.session_state.confirm_reset = True
            st.rerun()


# ── 화면 전환 (탭 대신 버튼으로 → 프로그램적 이동 가능) ────────────────
if "view" not in st.session_state:
    st.session_state.view = "plan"

nav1, nav2 = st.columns(2)
with nav1:
    if st.button("📋 학기별 이수계획", use_container_width=True,
                 type="primary" if st.session_state.view == "plan" else "secondary"):
        st.session_state.view = "plan"
        st.session_state.scroll_top = True
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
    _do_scroll = st.session_state.get("scroll_top", False)
    if _do_scroll:
        st.session_state.scroll_top = False

    program = st.radio("소속 과정", ["CMBA", "FMBA"], horizontal=True, key="program")
    rules = MASTER["graduation_rules"][program]
    st.caption(
        "각 학기를 펼쳐 필수과목과 선택과목을 확인하고 이수 여부를 체크하세요.  \n"
        "📱 이수 과목 확인: 모바일 LearnUs YONSEI → 나의강좌 → 과거강좌조회"
    )

    # ── 상단 고정 학점 헤더 (position:fixed, smooth animation) ────────
    _total_now = sum(v["credits"] for v in taken.values())
    _pct_now   = min(_total_now / rules["total_credits"] * 100, 100)
    _hdr_color = "#1a7a1a" if _total_now >= rules["total_credits"] else "#4C72FF"
    components.html(f"""<script>
    (function(){{
        var doc = window.parent.document;
        var pct   = {_pct_now:.2f};
        var color = '{_hdr_color}';
        var text  = '{_total_now:g} / {rules["total_credits"]:g} 학점';
        var bar   = doc.getElementById('sc-credit-bar');
        if (!bar) {{
            bar = doc.createElement('div');
            bar.id = 'sc-credit-bar';
            bar.style.cssText = 'position:fixed;top:50px;left:50%;transform:translateX(-50%);' +
                'width:min(780px,calc(100vw - 3rem));z-index:9999;background:white;' +
                'border:1px solid #dee2e6;border-radius:0 0 10px 10px;' +
                'padding:10px 18px;box-shadow:0 3px 10px rgba(0,0,0,0.12)';
            bar.innerHTML =
                '<div style="display:flex;align-items:center;gap:10px">' +
                '<div style="flex:1;min-width:0;overflow:hidden">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;gap:6px;flex-wrap:nowrap">' +
                '<span style="font-size:0.76rem;color:#666;white-space:nowrap;flex-shrink:1;overflow:hidden;text-overflow:ellipsis">📊 이수학점</span>' +
                '<span id="sc-credit-text" style="font-weight:800;font-size:0.92rem;color:' + color + ';white-space:nowrap;flex-shrink:0">' + text + '</span>' +
                '</div>' +
                '<div style="background:#e9ecef;border-radius:4px;height:6px">' +
                '<div id="sc-credit-fill" style="background:' + color + ';width:0%;height:100%;border-radius:4px;transition:width 0.45s ease"></div>' +
                '</div>' +
                '</div>' +
                '<div style="width:1px;height:30px;background:#dee2e6;flex-shrink:0"></div>' +
                '<button id="sc-report-nav-btn" style="font-size:0.75rem;padding:5px 10px;border-radius:8px;border:none;background:linear-gradient(135deg,#FF4B4B,#d93025);color:white;cursor:pointer;white-space:nowrap;font-weight:700;box-shadow:0 2px 8px rgba(255,75,75,0.4);flex-shrink:0">📋 리포트</button>' +
                '</div>';
            doc.body.appendChild(bar);
            setTimeout(function() {{
                var f = doc.getElementById('sc-credit-fill');
                if (f) f.style.width = pct + '%';
            }}, 60);
        }} else {{
            var fill = doc.getElementById('sc-credit-fill');
            if (fill) {{ fill.style.width = pct + '%'; fill.style.background = color; }}
            var txt = doc.getElementById('sc-credit-text');
            if (txt) {{ txt.innerHTML = text; txt.style.color = color; }}
        }}
    }})();
    </script>""", height=1)

    # 고정바 리포트 버튼 리스너
    # - polling: bar보다 먼저 실행돼도 100ms마다 재시도
    # - 텍스트로만 탐색: data-testid="stBaseButton-primary"는 상단 '학기별 이수계획'도 걸림
    components.html("""<script>
(function() {
    function attach() {
        var rb = window.parent.document.getElementById('sc-report-nav-btn');
        if (!rb) { setTimeout(attach, 100); return; }
        if (rb._scFn) rb.removeEventListener('click', rb._scFn);
        rb._scFn = function() {
            var p = window.parent.document;
            var all = p.querySelectorAll('button');
            var f = null;
            for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent || '';
                if (t.indexOf('졸업진단') > -1 || t.indexOf('입력 완료') > -1) {
                    f = all[i]; break;
                }
            }
            if (f) {
                f.scrollIntoView({behavior: 'smooth', block: 'center'});
                setTimeout(function() { f.click(); }, 200);
            }
        };
        rb.addEventListener('click', rb._scFn);
    }
    attach();
})();
</script>""", height=1)

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
        sub_stat      = f"필수 {checked_req}/{len(sem_req)}{elec_suffix} · {credits_done:g}학점"
        exp_title     = f"{sem_label}\n{sub_stat}"

        # 모든 학기 기본 펼침 (선택 시에도 닫히지 않게)
        with st.expander(exp_title, expanded=True):

            # ── 필수과목 ─────────────────────────────────────────────
            if sem_req:
                st.markdown('<div class="sub-hd">📌 필수과목</div>', unsafe_allow_html=True)
                for c in sem_req:
                    code    = c["code"]
                    chk_key = f"req_{program}_{code}"
                    checked = st.checkbox(
                        f"**{c['name']}**  ·  {c['credits']}학점",
                        value=code in taken, key=chk_key,
                    )
                    if checked:
                        set_course(code, name=c["name"], credits=c["credits"],
                                   kind="필수", is_english=False, is_leadership=False)
                    else:
                        if taken.get(code, {}).get("kind") == "필수":
                            drop_course(code)

            # ── 선택과목 ────────────────────────────────────────────
            if sem_elec:
                # 계절학기: 상한 도달 여부를 소제목에 표시
                if season and seasonal_cr_used >= SEASONAL_CREDIT_CAP:
                    st.markdown('<div class="sub-hd">🗂️ 선택과목 · ⚠️ 3.0학점 상한 도달</div>',
                                unsafe_allow_html=True)
                elif season:
                    cap_remaining = SEASONAL_CREDIT_CAP - seasonal_cr_used
                    st.markdown(f'<div class="sub-hd">🗂️ 선택과목 · 잔여 {cap_remaining:g}학점</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown('<div class="sub-hd">🗂️ 선택과목</div>', unsafe_allow_html=True)

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
                    st.markdown(
                        f'<div class="track-hd">{tr_label} · {cnt_taken}/{len(buckets[tr_label])}과목</div>',
                        unsafe_allow_html=True,
                    )

                    for c in buckets[tr_label]:
                        code = c["code"]
                        once = c.get("once")
                        rec  = taken.get(code)
                        # 다른 학기에서 이미 수강 → 잠금
                        once_locked = bool(once and rec is not None
                                           and rec.get("sem_idx") != sem_idx)
                        # 계절학기 3.0학점 상한 초과 → 미선택 과목 즉시 잠금
                        cap_locked = (
                            season is not None
                            and code not in SEASONAL_CAP_EXEMPT
                            and not _here(c)
                            and seasonal_cr_used + c["credits"] > SEASONAL_CREDIT_CAP
                        )
                        locked = once_locked or cap_locked
                        chk_key = f"elec_s{sem_idx}_{code}"

                        type_tag = ""
                        if c.get("is_english") and c.get("is_leadership"):
                            type_tag = "  (영어/리더십)"
                        elif c.get("is_english"):
                            type_tag = "  (영어강의)"
                        elif c.get("is_leadership"):
                            type_tag = "  (리더십개발)"

                        if locked:
                            # cap_locked 또는 once_locked → disabled 체크박스 + 🔒
                            lock_tag = "  🔒"
                            chk_label = f"**{c['name']}**  ·  {c['credits']}학점{type_tag}{lock_tag}"
                            st.checkbox(chk_label, value=_here(c) and not cap_locked,
                                        key=chk_key, disabled=True)
                            checked = False
                        else:
                            chk_label = f"**{c['name']}**  ·  {c['credits']}학점{type_tag}"
                            checked = st.checkbox(
                                chk_label, value=_here(c), key=chk_key, disabled=False,
                            )

                        if locked:
                            continue  # 이 섹션에서 변경 금지

                        # 영어+리더십 동시 해당 → 인정 항목 선택
                        count_as = None
                        if checked and c.get("is_english") and c.get("is_leadership"):
                            count_as = st.radio(
                                "어느 요건으로 인정할까요?",
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

    # ── 뷰 맨 아래에서 스크롤 ───────────────────────────────────────────
    if _do_scroll:
        components.html(_SCROLL_TOP, height=1)


# ────────────────────────────────────────────────────────────────────
# 화면 2: 졸업진단 리포트
# ────────────────────────────────────────────────────────────────────
if st.session_state.view == "report":
    # 학기계획 뷰에서 주입한 고정 바 제거
    components.html("""<script>
    var b = window.parent.document.getElementById('sc-credit-bar');
    if (b) b.remove();
    </script>""", height=1)
    st.markdown("### 📊 졸업요건 진단")

    total_r, english_r, ld_r, missing_r = compute_stats(program)
    rq_list_r = MASTER["required"][program]

    _grad_ok = (
        total_r   >= rules["total_credits"]
        and len(missing_r) == 0
        and english_r >= rules["english_credits"]
        and ld_r      >= rules["leadership_credits"]
    )
    if _grad_ok:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);'
            'border:2px solid #2e7d32;border-radius:12px;padding:16px 20px;margin:8px 0 16px">'
            '<div style="font-size:1.25rem;font-weight:800;color:#1b5e20">🎓 졸업 요건 충족!</div>'
            '<div style="font-size:0.88rem;color:#2e7d32;margin-top:4px">모든 졸업 요건을 충족했습니다.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        _issues = []
        if total_r   < rules["total_credits"]:
            _issues.append(f"학점 {rules['total_credits']-total_r:g}학점 부족")
        if missing_r:
            _issues.append(f"필수과목 {len(missing_r)}개 미이수")
        if english_r < rules["english_credits"]:
            _issues.append(f"영어강의 {rules['english_credits']-english_r:g}학점 부족")
        if ld_r      < rules["leadership_credits"]:
            _issues.append(f"리더십개발 {rules['leadership_credits']-ld_r:g}학점 부족")
        st.markdown(
            '<div style="background:#fdf0f0;border:2px solid #c0392b;border-radius:12px;'
            f'padding:16px 20px;margin:8px 0 16px">'
            '<div style="font-size:1.1rem;font-weight:800;color:#c0392b">❌ 졸업 요건 미충족</div>'
            f'<div style="font-size:0.86rem;color:#888;margin-top:4px">미충족: {" · ".join(_issues)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    def _mcard(col, label, value, sub, ok):
        vc  = "#1a7a1a" if ok else "#c0392b"
        bgs = "#f0faf0" if ok else "#fdf0f0"
        col.markdown(
            f'<div style="background:#f8f9fa;border-radius:8px;padding:8px 3px;text-align:center">'
            f'<div style="font-size:0.65rem;color:#666;margin-bottom:3px;word-break:keep-all">{label}</div>'
            f'<div style="font-size:1.1rem;font-weight:800;color:#111;line-height:1.1">{value}</div>'
            f'<div style="display:inline-block;background:{bgs};border-radius:4px;'
            f'padding:2px 5px;font-size:0.6rem;font-weight:600;color:{vc};margin-top:4px;word-break:keep-all">{sub}</div>'
            f'</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    _mcard(m1, "총 이수학점",  f"{total_r:g}학점",
           f"목표 {rules['total_credits']:g}학점",   total_r  >= rules["total_credits"])
    _mcard(m2, "필수 미이수",  f"{len(missing_r)}과목",
           f"{len(rq_list_r)-len(missing_r)}/{len(rq_list_r)} 완료", len(missing_r) == 0)
    _mcard(m3, "영어강의",     f"{english_r:g}학점",
           f"기준 {rules['english_credits']:g}학점",  english_r >= rules["english_credits"])
    _mcard(m4, "리더십개발",   f"{ld_r:g}학점",
           f"기준 {rules['leadership_credits']:g}학점", ld_r >= rules["leadership_credits"])

    st.markdown("---")

    def req_row(ok, label, detail=""):
        color = "#1a7a1a" if ok else "#c0392b"
        bg    = "#f0faf0" if ok else "#fdf0f0"
        icon  = "✅" if ok else "❌"
        detail_html = (f'<div style="color:#888;font-size:0.82rem;margin-top:5px;padding-left:20px">{detail}</div>'
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
            if ok:
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);'
                    f'border:2px solid #2e7d32;border-radius:10px;padding:12px 16px;margin:6px 0">'
                    f'<div style="font-weight:800;font-size:1rem;color:#1b5e20">🏆 {tr} 심화과정 인정</div>'
                    f'<div style="font-size:0.85rem;color:#2e7d32;margin-top:3px">'
                    f'{cr:g} / {rules["concentration_credits"]:g}학점 달성</div></div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="prog-label">{tr}　{cr:g} / {rules["concentration_credits"]:g}학점</div>',
                            unsafe_allow_html=True)
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
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);'
                    f'border:2px solid #2e7d32;border-radius:10px;padding:12px 16px;margin:6px 0">'
                    f'<div style="font-weight:800;font-size:1rem;color:#1b5e20">🏆 심화과정 인정</div>'
                    f'<div style="font-size:0.85rem;color:#2e7d32;margin-top:3px">{a}</div></div>',
                    unsafe_allow_html=True)
        else:
            st.info("아직 인정 기준을 충족한 조합이 없습니다.")
        st.caption("📖 " + MASTER["fmba_concentration_note"])

    st.markdown("---")
    with st.expander(f"📋 담은 과목 전체 보기  ({len(taken)}과목 · {total_r:g}학점)"):
        if taken:
            st.dataframe(
                [{"학정번호": code, "과목명": v["name"], "학점": v["credits"],
                  "종별": v.get("kind",""), "영어": "✓" if v.get("is_english") else "",
                  "리더십": "✓" if v.get("is_leadership") else ""}
                 for code, v in taken.items()],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("아직 담은 과목이 없습니다. 학기별 이수계획에서 과목을 선택하세요.")

    st.markdown("---")
    _bc1, _bc2 = st.columns(2)
    with _bc1:
        if st.button("← 이수계획으로 돌아가기", use_container_width=True, type="primary"):
            st.session_state.view = "plan"
            st.session_state.scroll_top = True
            st.rerun()
    with _bc2:
        if st.button("🗑️ 전체 초기화", use_container_width=True):
            st.session_state.taken = {}
            st.session_state.view = "plan"
            st.session_state.scroll_top = True
            st.rerun()

    # ── 리포트 뷰 맨 아래에서 스크롤 ──────────────────────────────────
    components.html(_SCROLL_TOP, height=1)
