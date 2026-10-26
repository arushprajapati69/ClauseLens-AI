"""
ClauseLens AI — Professional Policy Understanding Assistant
Fully functional public release.
"""

import os
import sys
import time
import streamlit as st

# Ensure clauselens-ai directory is on path when run from parent dir
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import config
from ingest import extract_text_from_file, chunk_document
from store import PolicyIndex
from pipeline import answer_question, Result
from llm import LLMClient

# ─────────────────────────────────────────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClauseLens — Policy Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
#  CSS — Professional dark-sidebar + clean white content
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ───────────── Fonts ───────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;1,9..144,300&display=swap');

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
}

/* ───────────── Animations ───────────── */
@keyframes fadeUp {
    from { opacity:0; transform:translateY(16px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
@keyframes shimmerText {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
}
@keyframes pulse {
    0%,100% { opacity:1; }
    50%      { opacity:.6; }
}
@keyframes slideRight {
    from { opacity:0; transform:translateX(-12px); }
    to   { opacity:1; transform:translateX(0); }
}
@keyframes popScale {
    0%   { opacity:0; transform:scale(.85); }
    70%  { transform:scale(1.03); }
    100% { opacity:1; transform:scale(1); }
}
@keyframes drawLine {
    from { width:0; }
    to   { width:100%; }
}
@keyframes borderGlow {
    0%,100% { box-shadow: 0 0 0 0 rgba(79,70,229,.3); }
    50%      { box-shadow: 0 0 0 6px rgba(79,70,229,0); }
}

/* ───────────── Hide default chrome ───────────── */
#MainMenu, footer, header          { display:none !important; }
.stDeployButton                    { display:none !important; }
[data-testid="stToolbar"]          { display:none !important; }

/* ───────────── Page background ───────────── */
.stApp { background:#f8fafc; }

/* ───────────── Sidebar ───────────── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] strong { color:#f1f5f9 !important; }
[data-testid="stSidebar"] .stButton>button {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 8px 14px !important;
    transition: all .18s ease !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton>button:hover {
    background: #334155 !important;
    border-color: #475569 !important;
    color: #fff !important;
}
[data-testid="stSidebar"] .stFileUploader {
    border: 1.5px dashed #334155 !important;
    border-radius: 10px !important;
    background: #1e293b !important;
    padding: 12px !important;
}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
    background: #1e293b !important;
    border-color: #334155 !important;
}

/* ───────────── Main content wrapper ───────────── */
.block-container {
    padding: 2rem 2.5rem !important;
    max-width: 900px !important;
}

/* ───────────── Logo / brand ───────────── */
.brand-block {
    padding: 20px 20px 12px;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 4px;
}
.brand-name {
    font-family: 'Fraunces', serif;
    font-size: 1.35rem;
    font-weight: 600;
    color: #f8fafc !important;
    letter-spacing: -.01em;
}
.brand-tag {
    font-size: 11px;
    color: #64748b !important;
    margin-top: 2px;
}

/* ───────────── Section labels in sidebar ───────────── */
.sb-section {
    padding: 14px 20px 6px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #475569 !important;
}

/* ───────────── Doc item in sidebar ───────────── */
.doc-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 20px;
    border-radius: 0;
    transition: background .15s;
    cursor: default;
}
.doc-item:hover { background: #1e293b; }
.doc-icon {
    width: 28px; height: 28px;
    background: #1e40af;
    border-radius: 6px;
    display: flex; align-items:center; justify-content:center;
    font-size: 13px; flex-shrink:0;
}
.doc-icon.md  { background: #065f46; }
.doc-icon.txt { background: #92400e; }
.doc-name {
    font-size: 12.5px;
    font-weight: 500;
    color: #e2e8f0 !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
}
.doc-meta {
    font-size: 10.5px;
    color: #64748b !important;
    flex-shrink:0;
}
.doc-ok { color: #34d399 !important; }

/* ───────────── Page header ───────────── */
.page-header {
    margin-bottom: 1.8rem;
    animation: fadeUp .5s ease both;
}
.page-title {
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    font-weight: 600;
    color: #0f172a;
    letter-spacing: -.02em;
    line-height: 1.2;
    margin-bottom: .35rem;
}
.page-title span {
    background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmerText 5s linear infinite;
}
.page-sub {
    font-size: 14px;
    color: #64748b;
    font-weight: 400;
}

/* ───────────── Question card ───────────── */
.q-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
    animation: fadeUp .4s ease .1s both;
}
.q-card label { font-weight:600; color:#0f172a; font-size:14px; }

/* ───────────── Scenario strip ───────────── */
.scenario-strip {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: .8rem 1rem;
    margin-top: .7rem;
    font-size: 13px;
}

/* ───────────── Submit button override ───────────── */
.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 11px 28px !important;
    letter-spacing: .01em !important;
    transition: opacity .2s ease, transform .15s ease !important;
    animation: borderGlow 2.5s ease infinite !important;
}
.stButton>button[kind="primary"]:hover {
    opacity: .88 !important;
    transform: translateY(-1px) !important;
}

/* ───────────── Verdict banner ───────────── */
.verdict-banner {
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin: .5rem 0 1.2rem;
    display: flex;
    align-items: center;
    gap: 14px;
    animation: popScale .45s cubic-bezier(.36,.07,.19,.97) both;
}
.verdict-dot {
    width:44px; height:44px;
    border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:1.35rem;
    flex-shrink:0;
}
.verdict-text-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 2px;
}
.verdict-text-title {
    font-family:'Fraunces',serif;
    font-size: 1.15rem;
    font-weight: 600;
    margin-bottom: 2px;
}
.verdict-text-sub { font-size:13px; opacity:.85; }

.v-supported   { background:#f0fdf4; border:1.5px solid #86efac; }
.v-supported .verdict-dot { background:#dcfce7; }
.v-supported .verdict-text-label { color:#166534; }
.v-supported .verdict-text-title { color:#14532d; }
.v-supported .verdict-text-sub   { color:#166534; }

.v-conflict    { background:#fff7ed; border:1.5px solid #fdba74; }
.v-conflict .verdict-dot { background:#ffedd5; }
.v-conflict .verdict-text-label { color:#9a3412; }
.v-conflict .verdict-text-title { color:#7c2d12; }
.v-conflict .verdict-text-sub   { color:#9a3412; }

.v-partial     { background:#fffbeb; border:1.5px solid #fcd34d; }
.v-partial .verdict-dot { background:#fef3c7; }
.v-partial .verdict-text-label { color:#92400e; }
.v-partial .verdict-text-title { color:#78350f; }
.v-partial .verdict-text-sub   { color:#92400e; }

.v-insufficient { background:#f8fafc; border:1.5px solid #cbd5e1; }
.v-insufficient .verdict-dot { background:#f1f5f9; }
.v-insufficient .verdict-text-label { color:#475569; }
.v-insufficient .verdict-text-title { color:#1e293b; }
.v-insufficient .verdict-text-sub   { color:#475569; }

.v-error       { background:#fff1f2; border:1.5px solid #fecdd3; }
.v-error .verdict-dot { background:#ffe4e6; }
.v-error .verdict-text-label { color:#9f1239; }
.v-error .verdict-text-title { color:#881337; }
.v-error .verdict-text-sub   { color:#9f1239; }

/* ───────────── Result section cards ───────────── */
.res-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
    animation: fadeUp .4s ease both;
}
.res-card-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .07em;
    color: #64748b;
    margin-bottom: .7rem;
    display: flex;
    align-items: center;
    gap: 7px;
}
.res-card-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #f1f5f9;
}

/* ───────────── Bottom-line answer ───────────── */
.answer-text {
    font-family: 'Fraunces', serif;
    font-size: 1.08rem;
    font-weight: 300;
    font-style: italic;
    color: #1e293b;
    line-height: 1.7;
    padding: .8rem 1.1rem;
    border-left: 3px solid #6366f1;
    background: #fafbff;
    border-radius: 0 8px 8px 0;
}

/* ───────────── Condition chips ───────────── */
.chips-wrap { display:flex; flex-wrap:wrap; gap:7px; }
.chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    transition: transform .12s ease, box-shadow .12s ease;
    cursor: default;
    animation: popScale .3s ease both;
}
.chip:hover { transform:scale(1.05); box-shadow:0 2px 8px rgba(0,0,0,.12); }
.chip-fee         { background:#fff1f2; color:#be123c; border:1px solid #fecdd3; }
.chip-deadline    { background:#fffbeb; color:#b45309; border:1px solid #fde68a; }
.chip-exclusion   { background:#fff7ed; color:#c2410c; border:1px solid #fdba74; }
.chip-eligibility { background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; }
.chip-condition   { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }
.chip-other       { background:#f8fafc; color:#475569; border:1px solid #e2e8f0; }

/* ───────────── Source citations ───────────── */
.citation {
    padding: .85rem 1rem;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-bottom: .7rem;
    background: #fafafa;
    animation: slideRight .35s ease both;
    transition: border-color .15s;
}
.citation:hover { border-color:#a5b4fc; }
.cit-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: .5rem;
}
.cit-num {
    width:22px; height:22px;
    background:#4f46e5;
    border-radius:50%;
    color:#fff;
    font-size:11px;
    font-weight:700;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
}
.cit-doc  { font-size:12.5px; font-weight:600; color:#1e293b; }
.cit-clause { font-size:11px; color:#94a3b8; margin-left:auto; }
.cit-quote {
    font-style:italic;
    font-size:13px;
    color:#334155;
    line-height:1.6;
    padding: .5rem .8rem;
    background:#fff;
    border-left:3px solid #818cf8;
    border-radius:0 6px 6px 0;
}

/* ───────────── Conflict panel ───────────── */
.conflict-intro {
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-radius: 10px;
    padding: .8rem 1rem;
    margin-bottom: .8rem;
    font-size: 13px;
    color: #78350f;
}
.conflict-col {
    background:#fff;
    border:1px solid #e2e8f0;
    border-radius:10px;
    padding:1rem;
}
.conflict-col.cola { border-top:3px solid #818cf8; }
.conflict-col.colb { border-top:3px solid #f87171; }
.conflict-doc-label {
    font-size:11px; font-weight:700; text-transform:uppercase;
    letter-spacing:.06em; color:#64748b; margin-bottom:.4rem;
}
.conflict-quote {
    font-style:italic; font-size:13px; color:#334155;
    line-height:1.6; padding:.5rem .8rem;
    background:#fafafa; border-left:3px solid #e2e8f0;
    border-radius:0 6px 6px 0; margin-bottom:.6rem;
}
.calc-result {
    background:#f8fafc; border:1px solid #e2e8f0;
    border-radius:8px; padding:.7rem .9rem; font-size:13px;
}
.calc-big {
    font-family:'Fraunces',serif;
    font-size:1.5rem; font-weight:600; display:block; margin-top:3px;
}
.green { color:#059669; }
.red   { color:#dc2626; }

/* ───────────── Precedence note ───────────── */
.precedence-note {
    background:#f0fdf4; border:1px solid #86efac;
    border-radius:10px; padding:.8rem 1rem;
    font-size:13px; color:#166534; margin-top:.7rem;
    animation: fadeIn .4s ease both;
}

/* ───────────── Support draft ───────────── */
.draft-wrap {
    background:#fafafa;
    border:1px dashed #cbd5e1;
    border-radius:10px;
    padding:1rem 1.2rem;
    font-size:13px; color:#334155;
    line-height:1.75;
    white-space:pre-wrap;
    font-family:'Inter',monospace;
}

/* ───────────── Empty state ───────────── */
.empty-state {
    text-align:center;
    padding: 4rem 1rem 2rem;
    animation: fadeIn .7s ease both;
}
.empty-icon { font-size:3rem; margin-bottom:.8rem; }
.empty-title {
    font-family:'Fraunces',serif;
    font-size:1.4rem;font-weight:600;
    color:#334155;margin-bottom:.5rem;
}
.empty-desc { font-size:13.5px; color:#94a3b8; line-height:1.6; }

/* ───────────── Onboarding steps ───────────── */
.how-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:1.2rem 0; }
.how-item {
    background:#fff; border:1px solid #e2e8f0;
    border-radius:12px; padding:1rem .9rem;
    text-align:center; transition:box-shadow .2s, transform .2s;
    animation: fadeUp .5s ease both;
}
.how-item:hover { box-shadow:0 4px 16px rgba(79,70,229,.1); transform:translateY(-2px); }
.how-num {
    width:28px;height:28px;
    background:#4f46e5;border-radius:50%;
    color:#fff;font-size:12px;font-weight:700;
    display:inline-flex;align-items:center;justify-content:center;
    margin-bottom:.6rem;
}
.how-label { font-size:12.5px;font-weight:600;color:#1e293b;margin-bottom:.3rem; }
.how-desc  { font-size:11.5px;color:#94a3b8;line-height:1.5; }

/* ───────────── Audit log ───────────── */
.audit-item {
    display:flex; align-items:flex-start; gap:10px;
    padding:.5rem 0;
    border-bottom:1px solid #f1f5f9;
    animation:slideRight .3s ease both;
    font-size:13px;
}
.audit-icon { font-size:1rem;flex-shrink:0;margin-top:2px; }
.audit-body { color:#475569;line-height:1.5;flex:1; }
.audit-pill {
    display:inline-block; padding:2px 8px;
    border-radius:4px; font-size:11px;font-weight:700;
    margin-left:6px; vertical-align:middle;
}
.pill-ok   { background:#dcfce7;color:#166534; }
.pill-warn { background:#fef9c3;color:#713f12; }
.pill-fail { background:#fee2e2;color:#991b1b; }
.pill-info { background:#e0e7ff;color:#3730a3; }

/* ───────────── Misc ───────────── */
.divider {
    height:1px;background:#f1f5f9;margin:1.2rem 0;
}
.privacy-bar {
    display:inline-flex;align-items:center;gap:6px;
    background:#f0fdf4;border:1px solid #86efac;
    border-radius:999px;padding:4px 12px;
    font-size:11px;font-weight:600;color:#166534;
    margin-bottom:.9rem;
}
.loading-step {
    display:flex;align-items:center;gap:10px;
    padding:.5rem .8rem;
    background:#fafafe;border:1px solid #e0e7ff;
    border-radius:8px;margin-bottom:.5rem;
    font-size:13px;color:#4338ca;font-weight:500;
    animation:fadeIn .35s ease both;
}
.spinner-dot {
    width:8px;height:8px;background:#6366f1;border-radius:50%;
    animation:pulse .8s ease infinite;flex-shrink:0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Session state — safe initialization + migration from old set-based state
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    if "index" not in st.session_state:
        st.session_state.index = PolicyIndex(cache_dir=".cache")
    if "indexed_docs" not in st.session_state:
        st.session_state.indexed_docs = {}   # {display_name: {"file":fname, "chunks":n, "ext":ext}}
    if isinstance(st.session_state.indexed_docs, set):
        # migrate old format
        st.session_state.indexed_docs = {n: {"file": n, "chunks": 0, "ext": ""} for n in st.session_state.indexed_docs}
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "model" not in st.session_state:
        st.session_state.model = config.GEN_MODEL

_init_state()


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _ext_icon(ext: str) -> tuple[str, str]:
    ext = ext.lower().lstrip(".")
    if ext == "pdf":  return "📄", "pdf"
    if ext == "md":   return "📝", "md"
    return "📃", "txt"


def _index_file(file_path: str, display_name: str) -> int:
    """
    Indexes a file using its actual path for extension detection,
    but stores display_name in chunks for presentation.
    Returns chunk count.
    """
    pages  = extract_text_from_file(file_path)           # extension from real path
    chunks = chunk_document(display_name, pages)          # doc_name = display label
    raw    = "\n".join(p["text"] for p in pages)
    st.session_state.index.add_document(display_name, raw, chunks)
    return len(chunks)


def _fmt_inr(amount) -> str:
    try:   return f"₹{int(amount):,}"
    except: return str(amount)


def _chip(claim: dict, delay: int = 0) -> str:
    t    = claim.get("type", "other").lower()
    text = claim.get("text", "")[:90]
    icon = {"fee":"💸","deadline":"⏰","exclusion":"⛔","eligibility":"✅","condition":"📋"}.get(t,"📌")
    lbl  = {"fee":"Fee","deadline":"Deadline","exclusion":"Excluded","eligibility":"Required","condition":"Condition"}.get(t,"Note")
    sty  = f"animation-delay:{delay}ms;"
    return f'<span class="chip chip-{t}" style="{sty}">{icon} <b>{lbl}:</b> {text}</span>'


# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown("""
    <div class="brand-block">
      <div class="brand-name">🔍 ClauseLens</div>
      <div class="brand-tag">Policy Understanding Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Documents section ──────────────────────────────
    st.markdown('<div class="sb-section">Documents</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    os.makedirs(".cache", exist_ok=True)

    if uploaded:
        for uf in uploaded:
            if uf.name not in st.session_state.indexed_docs:
                tmp = os.path.join(".cache", uf.name)
                with open(tmp, "wb") as f:
                    f.write(uf.getbuffer())
                try:
                    with st.spinner(f"Reading {uf.name}…"):
                        n = _index_file(tmp, uf.name)
                    ext = os.path.splitext(uf.name)[1].lstrip(".")
                    st.session_state.indexed_docs[uf.name] = {"file": uf.name, "chunks": n, "ext": ext}
                    st.toast(f"✅ {uf.name} ready", icon="📄")
                except Exception as e:
                    st.error(f"Could not read **{uf.name}**: {e}")

    if st.button("📚 Load Example Policies", use_container_width=True):
        # Map: display_label → actual file path (so ext is extracted from real path)
        samples = [
            ("StayEasy Hotel — Terms & Conditions", os.path.join(_here, "sample_docs", "stayeasy_terms.md")),
            ("StayEasy Hotel — FAQ",                os.path.join(_here, "sample_docs", "stayeasy_faq.md")),
            ("VoltEdge Earbuds — Warranty",         os.path.join(_here, "sample_docs", "voltedge_warranty.md")),
            ("ClipStream — Subscription Terms",     os.path.join(_here, "sample_docs", "clipstream_subscription.md")),
        ]
        loaded = 0
        for label, fpath in samples:
            if not os.path.exists(fpath):
                st.warning(f"File not found: {fpath}")
                continue
            if label not in st.session_state.indexed_docs:
                with st.spinner(f"Loading {label}…"):
                    n = _index_file(fpath, label)
                ext = os.path.splitext(fpath)[1].lstrip(".")
                st.session_state.indexed_docs[label] = {"file": fpath, "chunks": n, "ext": ext}
                loaded += 1
        if loaded:
            st.toast(f"📚 {loaded} policies loaded!", icon="✅")
        st.rerun()

    # Loaded docs list
    if st.session_state.indexed_docs:
        st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
        for name, meta in st.session_state.indexed_docs.items():
            icon, cls = _ext_icon(meta.get("ext", ""))
            short = name if len(name) <= 30 else name[:28] + "…"
            st.markdown(
                f'<div class="doc-item">'
                f'<div class="doc-icon {cls}">{icon}</div>'
                f'<div style="flex:1;min-width:0;">'
                f'<div class="doc-name">{short}</div>'
                f'<div class="doc-meta">{meta.get("chunks",0)} sections</div>'
                f'</div>'
                f'<span class="doc-ok">✓</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('<div style="margin:8px 20px 0;">', unsafe_allow_html=True)
        if st.button("🗑 Clear all documents", use_container_width=True):
            st.session_state.index.clear()
            st.session_state.indexed_docs = {}
            st.session_state.last_result  = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="padding:8px 20px;font-size:12px;color:#475569;">'
            'Upload a file or load the examples to begin.</div>',
            unsafe_allow_html=True
        )

    # ── Settings section ───────────────────────────────
    st.markdown('<div class="sb-section" style="margin-top:12px;">Settings</div>', unsafe_allow_html=True)

    model_opts = {
        config.GEN_MODEL:         "🔥 Best quality  (needs ~8 GB RAM)",
        config.LOW_RAM_GEN_MODEL: "⚡ Faster  (needs ~4 GB RAM)",
    }
    chosen = st.selectbox(
        "AI model",
        options=list(model_opts.keys()),
        format_func=lambda m: model_opts[m],
        index=0,
        label_visibility="collapsed",
    )
    st.session_state.model = chosen

    st.markdown(
        '<div style="padding:6px 0 14px;font-size:11px;color:#475569;">'
        '🔒 Both models run 100% on your device — nothing is sent online.'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Tips ───────────────────────────────────────────
    st.markdown('<div class="sb-section">Tips</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding:6px 20px 16px;font-size:12px;color:#64748b;line-height:1.65;">'
        '• Be specific: <i>"Can I cancel 2 days before?"</i><br>'
        '• Add dates + amount for exact refund math<br>'
        '• Upload multiple docs to find contradictions<br>'
        '• Copy the support draft to email the company'
        '</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Main — header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <div class="privacy-bar">🔒 100% Private — your documents never leave this device</div>
  <div class="page-title">Ask anything about<br><span>your policy document</span></div>
  <div class="page-sub">Upload any terms & conditions, warranty, subscription, or refund policy — then ask questions in plain English.</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Onboarding — when no docs loaded
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.indexed_docs:
    st.markdown("""
    <div class="how-grid">
      <div class="how-item" style="animation-delay:0s">
        <div class="how-num">1</div>
        <div class="how-label">Upload a document</div>
        <div class="how-desc">PDF, text file, or Markdown. Warranty cards, terms, FAQs — anything works.</div>
      </div>
      <div class="how-item" style="animation-delay:.08s">
        <div class="how-num">2</div>
        <div class="how-label">Ask your question</div>
        <div class="how-desc">Type naturally — like texting a knowledgeable friend.</div>
      </div>
      <div class="how-item" style="animation-delay:.16s">
        <div class="how-num">3</div>
        <div class="how-label">We find the clauses</div>
        <div class="how-desc">The relevant sections are pulled out and checked automatically.</div>
      </div>
      <div class="how-item" style="animation-delay:.24s">
        <div class="how-num">4</div>
        <div class="how-label">Get a clear answer</div>
        <div class="how-desc">Plain English answer + exact quote from the document, so you can verify it.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.info("👈 **Get started:** Upload a policy in the sidebar, or click **\"Load Example Policies\"** to try with sample documents.", icon="ℹ️")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  Question form
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="q-card">', unsafe_allow_html=True)
with st.form("qform", clear_on_submit=False):
    question = st.text_area(
        "**What would you like to know?**",
        placeholder=(
            "e.g.  Can I get a refund if I cancel 3 days before check-in?\n"
            "       Is water damage covered under my warranty?\n"
            "       What fees apply if I cancel my subscription mid-month?"
        ),
        height=95,
        max_chars=config.MAX_QUESTION_CHARS,
    )
    with st.expander("📅 Add dates or payment amount for exact calculations", expanded=False):
        st.markdown(
            '<div style="font-size:13px;color:#64748b;margin-bottom:.7rem;">'
            'Fill these in if you want us to calculate an exact refund amount or count the days of notice.</div>',
            unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns(3)
        with c1: start_date  = st.date_input("Start / check-in date", value=None)
        with c2: action_date = st.date_input("Action / cancellation date", value=None)
        with c3: amount_paid = st.number_input("Amount paid (₹)", min_value=0, value=0, step=100)

    col_btn, col_hint = st.columns([2, 5])
    with col_btn:
        submitted = st.form_submit_button("🔍  Analyse Policy", type="primary", use_container_width=True)
    with col_hint:
        st.markdown(
            '<div style="font-size:12px;color:#94a3b8;padding-top:.6rem;">'
            'Runs entirely on your computer — no internet required after setup.</div>',
            unsafe_allow_html=True
        )
st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Run pipeline
# ─────────────────────────────────────────────────────────────────────────────
if submitted:
    if not question.strip():
        st.warning("Please type a question first.")
    else:
        scenario = {}
        if start_date and action_date:
            scenario["start_date"]  = str(start_date)
            scenario["action_date"] = str(action_date)
        if amount_paid > 0:
            scenario["amount_paid"] = int(amount_paid)

        steps = [
            ("📖", "Reading through your documents…"),
            ("🔍", "Finding the most relevant clauses…"),
            ("✅", "Verifying every quote against the original text…"),
            ("⚖️",  "Checking for contradictions between documents…"),
            ("💬", "Writing your plain-English answer…"),
        ]
        ph = st.empty()
        for i, (icon, msg) in enumerate(steps):
            ph.markdown(
                f'<div class="loading-step" style="animation-delay:{i*60}ms">'
                f'<div class="spinner-dot"></div><span>{icon} {msg}</span></div>',
                unsafe_allow_html=True
            )
            time.sleep(0.38)

        with st.spinner(""):
            client = LLMClient(model=st.session_state.model)
            res    = answer_question(
                question=question,
                index=st.session_state.index,
                scenario=scenario,
                client=client,
                model=st.session_state.model,
            )
        ph.empty()
        st.session_state.last_result = res
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  Results
# ─────────────────────────────────────────────────────────────────────────────
res: Result = st.session_state.last_result

if not res:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">🔎</div>
      <div class="empty-title">Ready when you are</div>
      <div class="empty-desc">Type your question above and click <b>Analyse Policy</b>.<br>
      We'll find the answer in your uploaded documents.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Verdict banner ────────────────────────────────────────────────────────────
if res is not None:
    VERDICTS = {
        "SUPPORTED":            ("v-supported",   "✅", "SUPPORTED",          "Your policy clearly covers this", "We found solid evidence that directly answers your question."),
        "CONFLICT":             ("v-conflict",    "⚠️", "CONFLICT DETECTED",  "Two parts of your policy disagree", "We found a contradiction between documents. Both versions are shown below so you can decide what to do."),
        "PARTIAL":              ("v-partial",     "ℹ️", "PARTIAL ANSWER",     "It depends on certain conditions", "The policy answers your question, but only under specific circumstances. Read the conditions carefully."),
        "INSUFFICIENT_EVIDENCE":("v-insufficient","🤷","NOT FOUND",           "This topic isn't in your document", "We couldn't find anything covering this in the uploaded policy. Contact the company and ask them to point you to the exact clause."),
        "ERROR":                ("v-error",       "😕", "SOMETHING WENT WRONG","We hit a snag", "Try rephrasing your question, or check that Ollama is running and the model is downloaded."),
    }

    vkey = res.verdict.value if hasattr(res.verdict, "value") else str(res.verdict)
    vcls, vicon, vlabel, vtitle, vsub = VERDICTS.get(
        vkey, ("v-insufficient", "❓", vkey, "Unknown", "")
    )
    st.markdown(
        f'<div class="verdict-banner {vcls}">'
        f'<div class="verdict-dot">{vicon}</div>'
        f'<div><div class="verdict-text-label">{vlabel}</div>'
        f'<div class="verdict-text-title">{vtitle}</div>'
        f'<div class="verdict-text-sub">{vsub}</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ── 1. The Answer ──────────────────────────────────────────────────────────────
if res.bottom_line and res.verdict not in ("INSUFFICIENT_EVIDENCE", "ERROR"):
    st.markdown(
        '<div class="res-card" style="animation-delay:.05s">'
        '<div class="res-card-title">💬 The Answer</div>'
        f'<div class="answer-text">{res.bottom_line}</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ── 2. Things to watch out for ────────────────────────────────────────────────
if res.verified_claims:
    chips = "".join(_chip(c, i * 55) for i, c in enumerate(res.verified_claims))
    st.markdown(
        '<div class="res-card" style="animation-delay:.1s">'
        '<div class="res-card-title">⚠️ Key Conditions & Restrictions</div>'
        f'<div class="chips-wrap">{chips}</div>'
        '<div style="font-size:11.5px;color:#94a3b8;margin-top:.7rem;">'
        'The most important conditions, fees, deadlines, and exclusions we found in your document.'
        '</div></div>',
        unsafe_allow_html=True
    )


# ── 3. Sources ────────────────────────────────────────────────────────────────
if res.verified_claims:
    n_src = len(res.verified_claims)
    st.markdown(
        f'<div class="res-card" style="animation-delay:.15s">'
        f'<div class="res-card-title">📖 Sources &nbsp;<span style="background:#e0e7ff;color:#4338ca;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:700;">{n_src}</span></div>',
        unsafe_allow_html=True
    )
    for i, c in enumerate(res.verified_claims, 1):
        page_txt = f" · Page {c['page']}" if c.get("page") else ""
        clause   = c.get("clause_label") or "General Terms"
        st.markdown(
            f'<div class="citation" style="animation-delay:{i*80}ms">'
            f'<div class="cit-header">'
            f'<div class="cit-num">{i}</div>'
            f'<span class="cit-doc">{c.get("doc_name","")}{page_txt}</span>'
            f'<span class="cit-clause">{clause}</span>'
            f'</div>'
            f'<div class="cit-quote">"{c.get("quote","")}"</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── 4. Conflict panel ─────────────────────────────────────────────────────────
if res.conflicts:
    st.markdown(
        f'<div class="res-card" style="animation-delay:.2s">'
        f'<div class="res-card-title">⚔️ Contradiction Found &nbsp;<span style="background:#fef3c7;color:#b45309;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:700;">{len(res.conflicts)}</span></div>',
        unsafe_allow_html=True
    )
    for conf in res.conflicts:
        st.markdown(
            f'<div class="conflict-intro">'
            f'<b>📌 {conf.topic}</b><br>'
            f'<span style="font-size:12.5px;">{conf.explanation}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="conflict-col cola">'
                f'<div class="conflict-doc-label">📄 {conf.doc_a}</div>'
                f'<div style="font-size:11.5px;color:#94a3b8;margin-bottom:.4rem;">{conf.clause_label_a}</div>'
                f'<div class="conflict-quote">"{conf.quote_a}"</div>',
                unsafe_allow_html=True
            )
            if "terms_calc" in res.calculations and res.calculations["terms_calc"]:
                tc  = res.calculations["terms_calc"]
                amt = _fmt_inr(tc.get("refund_amount", 0))
                pct = tc.get("refund_percent", 0)
                days = res.calculations.get("days_notice", "?")
                st.markdown(
                    f'<div class="calc-result">'
                    f'<b>If this version applies:</b> {days} days notice, {pct}% back'
                    f'<span class="calc-big green">{amt}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown(
                f'<div class="conflict-col colb">'
                f'<div class="conflict-doc-label">📄 {conf.doc_b}</div>'
                f'<div style="font-size:11.5px;color:#94a3b8;margin-bottom:.4rem;">{conf.clause_label_b}</div>'
                f'<div class="conflict-quote">"{conf.quote_b}"</div>',
                unsafe_allow_html=True
            )
            if "faq_calc" in res.calculations and res.calculations["faq_calc"]:
                fc  = res.calculations["faq_calc"]
                amt = _fmt_inr(fc.get("refund_amount", 0))
                pct = fc.get("refund_percent", 0)
                days = res.calculations.get("days_notice", "?")
                st.markdown(
                    f'<div class="calc-result">'
                    f'<b>If this version applies:</b> {days} days notice, {pct}% back'
                    f'<span class="calc-big red">{amt}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

    if res.precedence_hint:
        h = res.precedence_hint
        st.markdown(
            f'<div class="precedence-note">'
            f'💡 <b>Which one legally wins?</b> {h.get("hint","")}<br>'
            f'<i style="font-size:12px;opacity:.8;">From the document: "{h.get("quote","")}"</i>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── 5. Standalone refund calculation ──────────────────────────────────────────
if res.calculations and res.calculations.get("days_notice") and "terms_calc" not in res.calculations and "standard_calc" in res.calculations:
    sc   = res.calculations["standard_calc"]
    amt  = _fmt_inr(sc.get("refund_amount", 0))
    pct  = sc.get("refund_percent", "?")
    days = res.calculations.get("days_notice", "?")
    st.markdown(
        f'<div class="res-card" style="animation-delay:.22s">'
        f'<div class="res-card-title">🧮 Your Estimated Refund</div>'
        f'<div style="font-size:13px;color:#64748b;margin-bottom:.4rem;">Based on {days} days notice:</div>'
        f'<span style="font-family:Fraunces,serif;font-size:2rem;font-weight:600;color:#059669;">{amt}</span>'
        f'<span style="font-size:13px;color:#94a3b8;margin-left:8px;">({pct}% of what you paid)</span>'
        f'</div>',
        unsafe_allow_html=True
    )


# ── 6. Support email draft ────────────────────────────────────────────────────
if res.support_draft:
    st.markdown(
        '<div class="res-card" style="animation-delay:.25s">'
        '<div class="res-card-title">✉️ Ready-to-Send Support Message</div>'
        '<div style="font-size:13px;color:#64748b;margin-bottom:.7rem;">'
        'Copy this into the company\'s support chat or email. '
        'It quotes the exact policy clauses so they can\'t ignore you.'
        '</div>',
        unsafe_allow_html=True
    )
    st.code(res.support_draft, language=None)
    st.markdown('</div>', unsafe_allow_html=True)


# ── 7. What to do (insufficient evidence) ────────────────────────────────────
if res.verdict == "INSUFFICIENT_EVIDENCE":
    st.markdown(
        '<div class="res-card" style="animation-delay:.1s">'
        '<div class="res-card-title">💡 What to Do Next</div>'
        '<div style="font-size:13.5px;color:#334155;line-height:1.7;">'
        '1. <b>Check other documents</b> — there may be a separate addendum or FAQ that covers this.<br>'
        '2. <b>Contact the company directly</b> — ask them to point you to the specific clause <i>in writing</i>.<br>'
        '3. <b>For significant money</b> — consider consulting a consumer rights organisation or solicitor.'
        '</div></div>',
        unsafe_allow_html=True
    )


# ── 8. Error details ──────────────────────────────────────────────────────────
if res.verdict == "ERROR" and res.error:
    with st.expander("🔧 Technical details", expanded=False):
        st.code(res.error)
        st.caption("Make sure Ollama is running (`ollama serve`) and the model is downloaded. Try selecting the lighter model in the sidebar if you're low on memory.")


# ── 9. Audit log ──────────────────────────────────────────────────────────────
with st.expander("🛡️ How we verified this answer", expanded=False):
    st.markdown(
        '<div style="font-size:13px;color:#64748b;margin-bottom:.7rem;">'
        'ClauseLens never blindly trusts the AI. Here\'s every check that ran on your answer:'
        '</div>',
        unsafe_allow_html=True
    )
    step_map = {
        "gate_0":     ("🚧", "Input check",         "Your question was validated."),
        "Gate 0":     ("🚧", "Input check",         "Your question was validated."),
        "retrieval":  ("🔍", "Clause search",        "The most relevant sections were found."),
        "Retrieval":  ("🔍", "Clause search",        "The most relevant sections were found."),
        "gate_1":     ("📋", "Format check",         "The AI's output matched the required structure."),
        "Gate 1":     ("📋", "Format check",         "The AI's output matched the required structure."),
        "gate_2":     ("✅", "Quote verification",   "Every quote was checked word-for-word."),
        "Gate 2":     ("✅", "Quote verification",   "Every quote was checked word-for-word."),
        "gate_2b":    ("🔢", "Number check",         "Any numbers or amounts were verified against source text."),
        "Gate 2b":    ("🔢", "Number check",         "Any numbers or amounts were verified against source text."),
        "conflict":   ("⚔️", "Contradiction scan",   "Documents were compared for conflicting rules."),
        "Conflict":   ("⚔️", "Contradiction scan",   "Documents were compared for conflicting rules."),
        "verdict":    ("⚖️", "Verdict",              "The outcome was decided by rules — not by the AI."),
        "Verdict":    ("⚖️", "Verdict",              "The outcome was decided by rules — not by the AI."),
    }
    ok_set   = {"PASS","FINAL","CONSISTENT","ABSTAIN","VERIFIED","SUPPORTED","PARTIAL","FOUND"}
    warn_set = {"WARN","CONFLICT_FOUND","EVALUATE","DROPPED","FALLBACK"}

    for i, ev in enumerate(res.trace):
        raw_gate = ev.get("gate", "")
        # normalise key
        key      = raw_gate.split(":")[0].strip()
        icon, label, desc = step_map.get(key, ("📌", raw_gate, ""))
        status   = ev.get("status", "")

        if status in ok_set:   pill_cls, pill_txt = "pill-ok",   "✓ passed"
        elif status in warn_set: pill_cls, pill_txt = "pill-warn", "⚠ note"
        else:                   pill_cls, pill_txt = "pill-fail", "✗ failed"

        st.markdown(
            f'<div class="audit-item" style="animation-delay:{i*50}ms">'
            f'<div class="audit-icon">{icon}</div>'
            f'<div class="audit-body"><b>{label}</b> — {desc}'
            f'<span class="audit-pill {pill_cls}">{pill_txt}</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    if res.dropped_claims:
        st.markdown(
            '<div style="margin-top:.7rem;font-size:13px;color:#64748b;">'
            '<b>Claims we left out</b> (the quote didn\'t match the original text exactly):</div>',
            unsafe_allow_html=True
        )
        for d in res.dropped_claims:
            st.markdown(
                f'<div style="font-size:12.5px;color:#94a3b8;padding:.3rem .5rem;">'
                f'• <i>"{d.get("text","")}"</i> — from {d.get("doc_name","")}'
                f'</div>',
                unsafe_allow_html=True
            )

    if res.retrieved_chunks:
        with st.expander("📂 All document sections we scanned", expanded=False):
            for c, sc in res.retrieved_chunks:
                pct = int(sc * 100)
                bar_w = max(4, min(pct, 100))
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0;font-size:12.5px;">'
                    f'<div style="width:40px;color:#6366f1;font-weight:700;text-align:right;">{pct}%</div>'
                    f'<div style="flex:1;height:4px;background:#f1f5f9;border-radius:4px;">'
                    f'<div style="width:{bar_w}%;height:100%;background:#6366f1;border-radius:4px;"></div></div>'
                    f'<div style="color:#334155;flex:2;">{c.doc_name} — {c.clause_label or "General"}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ─────────────────────────────────────────────────────────────────────────────
#  Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;font-size:11.5px;color:#94a3b8;padding:.5rem 0 1.5rem;">'
    '⚖️ ClauseLens helps you understand what a policy says — it is not legal advice. '
    'For decisions involving significant money or legal rights, consult a qualified professional.'
    '&nbsp;&nbsp;·&nbsp;&nbsp;'
    '🔒 All processing happens on your device. No data is sent anywhere.'
    '</div>',
    unsafe_allow_html=True
)
