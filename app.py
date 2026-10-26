"""
ClauseLens AI — Policy Understanding Assistant
Public-facing, fully functional, human-feeling Streamlit app.
"""

import os
import time
import streamlit as st
import config
from ingest import extract_text_from_file, chunk_document
from store import PolicyIndex
from pipeline import answer_question, Result
from llm import LLMClient

# ─────────────────────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClauseLens — Understand Any Policy in Seconds",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/clauselens-ai",
        "Report a bug": "https://github.com/clauselens-ai/issues",
        "About": "ClauseLens AI — plain-English policy assistant. 100% private, runs on your device."
    }
)

# ─────────────────────────────────────────────────────────
#  Full CSS with animations & human-design feel
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Nunito:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');

html, body, [class*="css"], .stMarkdown, p, li, span {
    font-family: 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── Keyframe animations ── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.25); }
    50%       { box-shadow: 0 0 0 10px rgba(99, 102, 241, 0); }
}
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
}
@keyframes spin {
    to { transform: rotate(360deg); }
}
@keyframes floatBadge {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-4px); }
}
@keyframes revealBar {
    from { width: 0%; }
    to   { width: var(--bar-width); }
}
@keyframes popIn {
    0%   { opacity: 0; transform: scale(0.8); }
    60%  { opacity: 1; transform: scale(1.05); }
    100% { opacity: 1; transform: scale(1); }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-20px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes bounceIn {
    0%   { transform: scale(0.6); opacity: 0; }
    70%  { transform: scale(1.08); opacity: 1; }
    100% { transform: scale(1); }
}

/* ── Global page background ── */
.stApp {
    background: linear-gradient(135deg, #f0f4ff 0%, #faf9ff 50%, #f5f0ff 100%);
    min-height: 100vh;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Hero title area ── */
.hero-section {
    animation: fadeSlideUp 0.7s ease both;
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.hero-title {
    font-family: 'Lora', serif;
    font-size: 3rem;
    font-weight: 600;
    background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 40%, #db2777 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite;
    margin-bottom: 0.3rem;
    line-height: 1.2;
}
.hero-sub {
    font-size: 1.1rem;
    color: #6b7280;
    font-weight: 400;
    margin-bottom: 1.2rem;
    font-family: 'Nunito', sans-serif;
    animation: fadeIn 1s ease 0.4s both;
}
.privacy-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    background: rgba(16, 185, 129, 0.08);
    border: 1.5px solid rgba(16, 185, 129, 0.35);
    border-radius: 999px;
    color: #059669;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    animation: floatBadge 3s ease-in-out infinite, fadeIn 1s ease 0.6s both;
}

/* ── Search bar area ── */
.search-wrap {
    animation: fadeSlideUp 0.7s ease 0.2s both;
}

/* ── Verdict cards ── */
.verdict-wrap {
    animation: bounceIn 0.55s cubic-bezier(0.36,0.07,0.19,0.97) both;
}
.verdict-card {
    border-radius: 18px;
    padding: 1.6rem 2rem;
    margin: 1.5rem 0 1rem;
    color: #fff;
    position: relative;
    overflow: hidden;
}
.verdict-card::before {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0) 60%);
    pointer-events: none;
}
.verdict-SUPPORTED   { background: linear-gradient(135deg, #059669 0%, #34d399 100%); }
.verdict-CONFLICT    { background: linear-gradient(135deg, #b91c1c 0%, #f59e0b 100%); }
.verdict-PARTIAL     { background: linear-gradient(135deg, #d97706 0%, #fbbf24 100%); }
.verdict-INSUFFICIENT_EVIDENCE { background: linear-gradient(135deg, #374151 0%, #6b7280 100%); }
.verdict-ERROR       { background: linear-gradient(135deg, #7f1d1d 0%, #dc2626 100%); }
.verdict-title {
    font-family: 'Lora', serif;
    font-size: 1.55rem;
    font-weight: 600;
    margin: 0 0 0.4rem;
    color: #fff;
}
.verdict-sub { font-size: 0.95rem; opacity: 0.88; margin: 0; }

/* ── Section cards ── */
.section-card {
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(226,232,240,0.8);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    animation: fadeSlideUp 0.5s ease both;
    transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.section-card:hover {
    box-shadow: 0 8px 32px rgba(99,102,241,0.12);
    transform: translateY(-2px);
}
.section-title {
    font-family: 'Lora', serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: #1e1b4b;
    margin-bottom: 0.7rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── Bottom line box ── */
.bottomline-box {
    background: linear-gradient(120deg, #eff6ff 0%, #f5f3ff 100%);
    border-left: 5px solid #6366f1;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    font-size: 1.05rem;
    color: #1e1b4b;
    line-height: 1.65;
    font-family: 'Lora', serif;
    font-style: italic;
}

/* ── Condition chips ── */
.chips-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 0.4rem; }
.chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 13px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 700;
    animation: popIn 0.4s ease both;
    cursor: default;
    transition: transform 0.15s ease;
}
.chip:hover { transform: scale(1.05); }
.chip-fee         { background: #fef2f2; color: #b91c1c; border: 1.5px solid #fecaca; }
.chip-deadline    { background: #fffbeb; color: #92400e; border: 1.5px solid #fde68a; }
.chip-exclusion   { background: #fff7ed; color: #c2410c; border: 1.5px solid #fed7aa; }
.chip-eligibility { background: #eff6ff; color: #1d4ed8; border: 1.5px solid #bfdbfe; }
.chip-condition   { background: #f0fdf4; color: #15803d; border: 1.5px solid #bbf7d0; }
.chip-other       { background: #f8fafc; color: #475569; border: 1.5px solid #e2e8f0; }

/* ── Quote blocks ── */
.quote-block {
    border-left: 4px solid #818cf8;
    background: rgba(99,102,241,0.05);
    border-radius: 0 10px 10px 0;
    padding: 0.7rem 1rem;
    margin: 0.6rem 0;
    font-style: italic;
    color: #312e81;
    font-size: 0.93rem;
    line-height: 1.6;
    transition: border-color 0.2s ease;
}
.quote-block:hover { border-color: #6366f1; }

.source-label {
    font-size: 0.8rem;
    font-weight: 700;
    color: #6366f1;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}

/* ── Conflict panel ── */
.conflict-header {
    background: linear-gradient(120deg, #fef3c7 0%, #fff7ed 100%);
    border: 1.5px solid #fde68a;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    animation: slideInLeft 0.4s ease both;
}
.conflict-col-a { border: 1.5px solid #ddd6fe; border-radius: 12px; padding: 1rem; }
.conflict-col-b { border: 1.5px solid #fecaca; border-radius: 12px; padding: 1rem; }
.doc-name-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.badge-a { background: #ede9fe; color: #5b21b6; }
.badge-b { background: #fee2e2; color: #991b1b; }

/* ── Calc boxes ── */
.calc-box {
    background: #fff;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    border: 1px solid #e5e7eb;
    margin-top: 0.7rem;
    font-size: 0.88rem;
}
.calc-amount {
    font-family: 'Lora', serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: #059669;
    display: block;
    margin-top: 0.2rem;
}
.calc-amount-warn { color: #b91c1c; }

/* ── Support draft box ── */
.draft-box {
    background: #f8fafc;
    border: 1.5px dashed #94a3b8;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    font-family: 'Nunito', sans-serif;
    font-size: 0.92rem;
    color: #334155;
    line-height: 1.7;
    white-space: pre-wrap;
}

/* ── Steps counter ── */
.step-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 0.5rem;
    animation: slideInLeft 0.4s ease both;
}
.step-dot {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 50%;
    color: #fff;
    font-weight: 800;
    font-size: 0.82rem;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}

/* ── How it works boxes ── */
.how-box {
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(226,232,240,0.9);
    border-radius: 14px;
    padding: 1.2rem;
    text-align: center;
    transition: box-shadow 0.2s, transform 0.2s;
    animation: fadeSlideUp 0.6s ease both;
}
.how-box:hover {
    box-shadow: 0 6px 24px rgba(99,102,241,0.14);
    transform: translateY(-3px);
}
.how-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.how-title { font-weight: 800; font-size: 0.95rem; color: #1e1b4b; margin-bottom: 0.3rem; }
.how-desc { font-size: 0.82rem; color: #6b7280; line-height: 1.55; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%) !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #e0e7ff !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label { color: #c7d2fe !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.12) !important;
    border: 1.5px solid rgba(255,255,255,0.2) !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    transition: background 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.22) !important;
}
[data-testid="stSidebar"] .stSelectbox > div { color: #fff !important; }

/* ── Spinner override ── */
[data-testid="stSpinner"] { animation: pulseGlow 1.5s ease infinite; }

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    animation: fadeIn 0.8s ease both;
}
.empty-icon { font-size: 4rem; margin-bottom: 1rem; animation: floatBadge 3s ease infinite; }
.empty-title { font-family: 'Lora', serif; font-size: 1.5rem; color: #374151; margin-bottom: 0.5rem; }
.empty-desc { color: #9ca3af; font-size: 0.95rem; }

/* ── Animate nth-child delays ── */
.section-card:nth-child(1) { animation-delay: 0.05s; }
.section-card:nth-child(2) { animation-delay: 0.12s; }
.section-card:nth-child(3) { animation-delay: 0.19s; }
.section-card:nth-child(4) { animation-delay: 0.26s; }
.section-card:nth-child(5) { animation-delay: 0.33s; }
.section-card:nth-child(6) { animation-delay: 0.40s; }

/* ── Precedence info ── */
.precedence-box {
    background: linear-gradient(120deg, #f0fdf4 0%, #ecfdf5 100%);
    border: 1.5px solid #6ee7b7;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin-top: 0.8rem;
    font-size: 0.9rem;
    color: #065f46;
}

/* ── Result count badge ── */
.result-count {
    display: inline-block;
    background: #ede9fe;
    color: #6d28d9;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 800;
    margin-left: 8px;
    vertical-align: middle;
}

/* ── Audit row ── */
.audit-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.85rem;
    animation: slideInLeft 0.3s ease both;
}
.audit-icon { font-size: 1rem; flex-shrink: 0; margin-top: 2px; }
.audit-text { color: #475569; line-height: 1.5; }
.audit-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-left: 5px;
}
.audit-pass { background: #d1fae5; color: #065f46; }
.audit-fail { background: #fee2e2; color: #991b1b; }
.audit-info { background: #e0e7ff; color: #3730a3; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
#  Session state
# ─────────────────────────────────────────────────────────
if "index" not in st.session_state:
    st.session_state.index = PolicyIndex(cache_dir=".cache")
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = {}          # name → chunk_count
# Migrate from old set-based session state (backwards compat)
if isinstance(st.session_state.indexed_docs, set):
    st.session_state.indexed_docs = {name: 0 for name in st.session_state.indexed_docs}
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "selected_model" not in st.session_state:
    st.session_state.selected_model = config.GEN_MODEL
if "show_how" not in st.session_state:
    st.session_state.show_how = True


# ─────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────
def _index_file(file_path: str, display_name: str):
    """Index one document and update session state. Returns chunk count."""
    pages = extract_text_from_file(file_path, filename=display_name)
    chunks = chunk_document(display_name, pages)
    raw_text = "\n".join(p["text"] for p in pages)
    st.session_state.index.add_document(display_name, raw_text, chunks)
    return len(chunks)


def _chip_html(claim: dict, delay_ms: int = 0) -> str:
    ctype = claim.get("type", "other").lower()
    text  = claim.get("text", "")
    icons = {"fee": "💸", "deadline": "⏰", "exclusion": "⛔", "eligibility": "✅", "condition": "📋"}
    icon  = icons.get(ctype, "📌")
    label = {"fee": "Fee", "deadline": "Deadline", "exclusion": "Excluded", "eligibility": "Requirement", "condition": "Condition"}.get(ctype, "Note")
    style = f"animation-delay: {delay_ms}ms;"
    return f'<span class="chip chip-{ctype}" style="{style}">{icon} <b>{label}:</b> {text}</span>'


def _format_inr(amount) -> str:
    try:
        return f"₹{int(amount):,}"
    except Exception:
        return str(amount)


# ─────────────────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 ClauseLens")
    st.markdown(
        '<div style="background:rgba(16,185,129,0.18);border:1.5px solid rgba(16,185,129,0.4);'
        'border-radius:10px;padding:8px 12px;font-size:0.8rem;font-weight:700;color:#6ee7b7;margin-bottom:1rem;">'
        '🔒 Your documents never leave this device</div>',
        unsafe_allow_html=True
    )

    st.markdown("### 📂 Your Documents")

    uploaded_files = st.file_uploader(
        "Upload a policy file",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Supports PDF, plain text (.txt), and Markdown (.md) files."
    )

    if uploaded_files:
        os.makedirs(".cache", exist_ok=True)
        for uf in uploaded_files:
            if uf.name not in st.session_state.indexed_docs:
                with st.spinner(f"Reading {uf.name}…"):
                    temp_path = os.path.join(".cache", uf.name)
                    with open(temp_path, "wb") as f:
                        f.write(uf.getbuffer())
                    try:
                        n = _index_file(temp_path, uf.name)
                        st.session_state.indexed_docs[uf.name] = n
                        st.toast(f"✅ {uf.name} is ready!", icon="📄")
                        st.session_state.show_how = False
                    except Exception as e:
                        st.error(f"Couldn't read {uf.name}: {e}")

    st.markdown("**— or try the built-in examples —**")
    if st.button("📚 Load Example Policies", use_container_width=True):
        samples = [
            ("stayeasy_terms.md",        "StayEasy Hotel — Terms & Conditions"),
            ("stayeasy_faq.md",           "StayEasy Hotel — FAQ"),
            ("voltedge_warranty.md",      "VoltEdge Earbuds — Warranty"),
            ("clipstream_subscription.md","ClipStream — Subscription & Cancellation"),
        ]
        loaded = 0
        for fname, label in samples:
            path = os.path.join("sample_docs", fname)
            if os.path.exists(path) and label not in st.session_state.indexed_docs:
                with st.spinner(f"Loading {label}…"):
                    n = _index_file(path, label)
                    st.session_state.indexed_docs[label] = n
                    loaded += 1
        if loaded:
            st.toast(f"📚 {loaded} example policies loaded!", icon="✅")
            st.session_state.show_how = False
        st.rerun()

    if st.session_state.indexed_docs:
        st.markdown("**Loaded:**")
        for name, n in st.session_state.indexed_docs.items():
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;padding:4px 0;">'
                f'<span style="font-size:1rem;">📄</span>'
                f'<span style="font-size:0.82rem;font-weight:600;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name}</span>'
                f'<span style="font-size:0.72rem;opacity:0.6;">{n} sections</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        if st.button("🗑️ Clear Everything", use_container_width=True, type="secondary"):
            st.session_state.index.clear()
            st.session_state.indexed_docs = {}
            st.session_state.last_result = None
            st.session_state.show_how = True
            st.rerun()
    else:
        st.caption("Upload a file above or load the examples to get started.")

    st.divider()
    st.markdown("### ⚙️ Settings")

    model_labels = {
        config.GEN_MODEL:         "🔥 Best results (needs 8 GB RAM)",
        config.LOW_RAM_GEN_MODEL: "⚡ Faster, lower memory",
    }
    chosen_model = st.selectbox(
        "AI Model",
        options=list(model_labels.keys()),
        format_func=lambda m: model_labels.get(m, m),
        index=0,
    )
    st.session_state.selected_model = chosen_model
    st.caption("Both models run 100% on your machine — nothing goes to the cloud.")

    st.divider()
    st.markdown("### 🙋 Quick Tips")
    st.markdown(
        "- Ask **specific** questions: *\"Can I cancel 2 days before?\"*\n"
        "- Add dates & amount for exact refund math\n"
        "- Upload multiple docs to catch contradictions\n"
        "- Copy the email draft to contact support fast"
    )


# ─────────────────────────────────────────────────────────
#  Hero
# ─────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <div class="hero-title">Understand Any Policy — Instantly</div>
    <div class="hero-sub">
        Stop squinting at the fine print.<br>
        Ask a question, get a plain-English answer with the exact lines from your document.
    </div>
    <div class="privacy-pill">🔒 100% Private &nbsp;·&nbsp; Runs on Your Device &nbsp;·&nbsp; No Cloud, Ever</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
#  "How it works" — shown when no docs loaded
# ─────────────────────────────────────────────────────────
if st.session_state.show_how and not st.session_state.indexed_docs:
    st.markdown("#### How it works")
    h1, h2, h3, h4 = st.columns(4)
    boxes = [
        (h1, "📂", "Upload your policy", "Drop any PDF, terms & conditions, warranty, or subscription agreement."),
        (h2, "❓", "Ask your question", "Type naturally — as if texting a friend who knows the law."),
        (h3, "🔍", "We find the right clauses", "The relevant parts are pulled from your document automatically."),
        (h4, "✅", "Get a clear answer", "Plain English, with the exact quote from the document so you can verify it yourself."),
    ]
    for col, icon, title, desc in boxes:
        with col:
            st.markdown(
                f'<div class="how-box"><div class="how-icon">{icon}</div>'
                f'<div class="how-title">{title}</div>'
                f'<div class="how-desc">{desc}</div></div>',
                unsafe_allow_html=True
            )
    st.markdown("")
    st.info("👈 **Get started:** Upload a policy or click \"Load Example Policies\" in the sidebar on the left.")
    st.stop()


# ─────────────────────────────────────────────────────────
#  Question Form
# ─────────────────────────────────────────────────────────
st.markdown('<div class="search-wrap">', unsafe_allow_html=True)
with st.form("question_form", clear_on_submit=False):
    question = st.text_area(
        "What would you like to know?",
        placeholder=(
            "e.g.  Can I get a refund if I cancel 3 days before check-in?\n"
            "       Is water damage covered under my warranty?\n"
            "       What happens if I miss a subscription payment?"
        ),
        height=100,
        max_chars=config.MAX_QUESTION_CHARS,
    )

    with st.expander("📅 I have specific dates or a payment amount (optional)", expanded=False):
        st.caption(
            "Filling this in lets us calculate the exact refund amount or number of days' notice — "
            "so you get a real number, not just a percentage."
        )
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            start_date = st.date_input("Start / Check-in date", value=None)
        with dc2:
            action_date = st.date_input("Cancellation / action date", value=None)
        with dc3:
            amount_paid = st.number_input("Amount you paid (₹)", min_value=0, value=0, step=100)

    submitted = st.form_submit_button(
        "🔍  Find My Answer",
        use_container_width=True,
        type="primary",
    )
st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
#  Run pipeline
# ─────────────────────────────────────────────────────────
if submitted:
    if not question.strip():
        st.warning("Please type a question first.")
    elif not st.session_state.indexed_docs:
        st.warning("Please load at least one policy document first (see the sidebar).")
    else:
        scenario = {}
        if start_date and action_date:
            scenario["start_date"]  = str(start_date)
            scenario["action_date"] = str(action_date)
        if amount_paid > 0:
            scenario["amount_paid"] = int(amount_paid)

        progress_messages = [
            "📖 Reading through your document…",
            "🔍 Finding the relevant clauses…",
            "✍️ Checking every quote against the original text…",
            "⚖️ Looking for any contradictions between documents…",
            "💡 Putting together your answer…",
        ]

        prog_container = st.empty()
        for i, msg in enumerate(progress_messages):
            prog_container.markdown(
                f'<div style="text-align:center;padding:1rem;color:#6366f1;font-weight:600;'
                f'font-size:1rem;animation:fadeIn 0.3s ease;">{msg}</div>',
                unsafe_allow_html=True
            )
            time.sleep(0.4)

        client = LLMClient(model=st.session_state.selected_model)
        with st.spinner("Almost there…"):
            res = answer_question(
                question=question,
                index=st.session_state.index,
                scenario=scenario,
                client=client,
                model=st.session_state.selected_model,
            )
        prog_container.empty()
        st.session_state.last_result = res
        st.rerun()


# ─────────────────────────────────────────────────────────
#  Results
# ─────────────────────────────────────────────────────────
res: Result = st.session_state.last_result

if not res:
    # No question asked yet — show a warm empty state
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">🔎</div>
        <div class="empty-title">Ready when you are</div>
        <div class="empty-desc">Type your question above and we'll find the answer in your policy documents.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown("---")

# ── 1. Verdict card ─────────────────────────────────────
verdict_meta = {
    "SUPPORTED": (
        "✅  Yes — your policy supports this",
        "We found clear evidence in your document that answers your question.",
        "#059669"
    ),
    "CONFLICT": (
        "⚠️  Heads up — we found a contradiction",
        "Two parts of your policy say different things. We've shown both so you can decide what to do.",
        "#b91c1c"
    ),
    "PARTIAL": (
        "ℹ️  It depends — there are conditions",
        "The policy answers your question, but only under certain circumstances. Read the conditions below.",
        "#d97706"
    ),
    "INSUFFICIENT_EVIDENCE": (
        "🤷  Not covered in your document",
        "We couldn't find anything about this in the uploaded policy. It's best to ask the company directly.",
        "#374151"
    ),
    "ERROR": (
        "😬  Something went wrong",
        "We hit a technical snag. Try re-wording your question or refreshing the page.",
        "#7f1d1d"
    ),
}

title_txt, sub_txt, _ = verdict_meta.get(res.verdict, (res.verdict, "", "#374151"))
verdict_class = f"verdict-{res.verdict}"

st.markdown(
    f'<div class="verdict-wrap">'
    f'<div class="verdict-card {verdict_class}">'
    f'<div class="verdict-title">{title_txt}</div>'
    f'<p class="verdict-sub">{sub_txt}</p>'
    f'</div></div>',
    unsafe_allow_html=True
)


# ── 2. Plain-language answer ──────────────────────────────
if res.bottom_line and res.verdict not in ("INSUFFICIENT_EVIDENCE", "ERROR"):
    st.markdown(
        '<div class="section-card">'
        '<div class="section-title">💬 The short answer</div>'
        f'<div class="bottomline-box">{res.bottom_line}</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ── 3. Things to watch out for ───────────────────────────
if res.verified_claims:
    chips_html = ""
    for i, c in enumerate(res.verified_claims):
        chips_html += _chip_html(c, delay_ms=i * 60)

    st.markdown(
        '<div class="section-card">'
        '<div class="section-title">⚠️ Things you should know</div>'
        f'<div class="chips-row">{chips_html}</div>'
        '<p style="font-size:0.8rem;color:#9ca3af;margin-top:0.7rem;margin-bottom:0;">'
        'These are the key conditions, deadlines, fees, and exclusions we found in your document.'
        '</p></div>',
        unsafe_allow_html=True
    )


# ── 4. Where we found it ─────────────────────────────────
if res.verified_claims:
    n = len(res.verified_claims)
    st.markdown(
        '<div class="section-card">'
        f'<div class="section-title">📖 Where we found it'
        f'<span class="result-count">{n} source{"s" if n != 1 else ""}</span></div>',
        unsafe_allow_html=True
    )
    for idx, c in enumerate(res.verified_claims, 1):
        page_txt = f" · Page {c['page']}" if c.get("page") else ""
        label = c.get("clause_label") or "General Terms"
        st.markdown(
            f'<div style="margin-bottom:0.9rem;">'
            f'<div class="source-label">[{idx}] {c.get("doc_name", "")}{page_txt} — {label}</div>'
            f'<div class="quote-block">"{c.get("quote", "")}"</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── 5. Contradictions between documents ─────────────────
if res.conflicts:
    n = len(res.conflicts)
    st.markdown(
        '<div class="section-card">'
        f'<div class="section-title">⚔️ We noticed a contradiction'
        f'<span class="result-count">{n} found</span></div>'
        '<p style="font-size:0.9rem;color:#6b7280;margin-bottom:0.8rem;">'
        'Different parts of your policy seem to say different things. '
        'We\'ve shown them side-by-side so you can see what they each say.'
        '</p>',
        unsafe_allow_html=True
    )

    for idx, conf in enumerate(res.conflicts, 1):
        st.markdown(
            f'<div class="conflict-header">'
            f'<b>📌 Topic: {conf.topic}</b><br/>'
            f'<span style="font-size:0.88rem;color:#92400e;">{conf.explanation}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        cola, colb = st.columns(2)
        with cola:
            st.markdown(
                f'<div class="conflict-col-a">'
                f'<div class="doc-name-badge badge-a">📄 {conf.doc_a}</div><br/>'
                f'<div class="source-label">{conf.clause_label_a}</div>'
                f'<div class="quote-block">"{conf.quote_a}"</div>',
                unsafe_allow_html=True
            )
            if "terms_calc" in res.calculations and res.calculations["terms_calc"]:
                tc = res.calculations["terms_calc"]
                days = res.calculations.get("days_notice", "?")
                amt  = _format_inr(tc.get("refund_amount", 0))
                pct  = tc.get("refund_percent", 0)
                st.markdown(
                    f'<div class="calc-box">'
                    f'<b>If this version applies:</b><br/>'
                    f'Notice given: {days} days &nbsp;·&nbsp; Refund rate: {pct}%'
                    f'<span class="calc-amount">{amt}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

        with colb:
            st.markdown(
                f'<div class="conflict-col-b">'
                f'<div class="doc-name-badge badge-b">📄 {conf.doc_b}</div><br/>'
                f'<div class="source-label">{conf.clause_label_b}</div>'
                f'<div class="quote-block">"{conf.quote_b}"</div>',
                unsafe_allow_html=True
            )
            if "faq_calc" in res.calculations and res.calculations["faq_calc"]:
                fc = res.calculations["faq_calc"]
                days = res.calculations.get("days_notice", "?")
                amt  = _format_inr(fc.get("refund_amount", 0))
                pct  = fc.get("refund_percent", 0)
                st.markdown(
                    f'<div class="calc-box">'
                    f'<b>If this version applies:</b><br/>'
                    f'Notice given: {days} days &nbsp;·&nbsp; Refund rate: {pct}%'
                    f'<span class="calc-amount calc-amount-warn">{amt}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

    if res.precedence_hint:
        hint  = res.precedence_hint.get("hint", "")
        quote = res.precedence_hint.get("quote", "")
        st.markdown(
            f'<div class="precedence-box">'
            f'💡 <b>Which one wins?</b> {hint}<br/>'
            f'<i style="font-size:0.85rem;opacity:0.8;">From the document: "{quote}"</i><br/>'
            f'<span style="font-size:0.8rem;color:#065f46;opacity:0.75;">'
            f'(We still recommend confirming with customer support before taking action.)</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ── 6. Refund / scenario calculation (standalone) ────────
if res.calculations and "terms_calc" not in res.calculations and res.calculations.get("days_notice"):
    calc = res.calculations
    days = calc.get("days_notice", "?")
    tc   = calc.get("terms_calc") or {}
    amt  = _format_inr(tc.get("refund_amount", 0)) if tc else "N/A"
    pct  = tc.get("refund_percent", "?") if tc else "?"
    st.markdown(
        '<div class="section-card">'
        '<div class="section-title">🧮 Your estimated refund</div>'
        f'<p style="font-size:0.9rem;color:#6b7280;">Based on {days} days\' notice and the policy rules we found:</p>'
        f'<span style="font-family:Lora,serif;font-size:2rem;font-weight:600;color:#059669;">{amt}</span>'
        f'<span style="font-size:0.9rem;color:#6b7280;margin-left:8px;">({pct}% of what you paid)</span>'
        '</div>',
        unsafe_allow_html=True
    )


# ── 7. Support email draft ───────────────────────────────
if res.support_draft:
    st.markdown(
        '<div class="section-card">'
        '<div class="section-title">✉️ Ready-to-send message for support</div>'
        '<p style="font-size:0.88rem;color:#6b7280;margin-bottom:0.7rem;">'
        'Copy this and paste it into the company\'s support chat or email. '
        'It mentions the exact clauses from the policy so they can\'t brush you off.'
        '</p>',
        unsafe_allow_html=True
    )
    st.code(res.support_draft, language=None)
    st.markdown('</div>', unsafe_allow_html=True)


# ── 8. Insufficient evidence → what to do ───────────────
if res.verdict == "INSUFFICIENT_EVIDENCE":
    st.markdown(
        '<div class="section-card">'
        '<div class="section-title">💬 What to do next</div>'
        '<div class="bottomline-box">'
        'The uploaded policy doesn\'t seem to cover this topic. Here\'s what we suggest:<br/><br/>'
        '1. Check if there is another document (e.g. a separate FAQ or addendum) that might cover it.<br/>'
        '2. Contact the company directly — ask them to point you to the specific clause in writing.<br/>'
        '3. If it involves a significant amount of money, consider getting formal legal advice.'
        '</div></div>',
        unsafe_allow_html=True
    )
    if res.support_draft:
        st.code(res.support_draft, language=None)


# ── 9. Error state ───────────────────────────────────────
if res.verdict == "ERROR" and res.error:
    with st.expander("🔧 Technical details (for troubleshooting)", expanded=False):
        st.code(res.error)
        st.caption(
            "Make sure Ollama is running (`ollama serve`) and the selected model is downloaded. "
            "If the error persists, try selecting the lighter model in the sidebar settings."
        )


# ── 10. Audit log (collapsed, human-friendly) ───────────
with st.expander("🛡️ How we checked this answer", expanded=False):
    st.markdown(
        '<p style="font-size:0.88rem;color:#6b7280;margin-bottom:0.8rem;">'
        'ClauseLens never just "trusts" the AI. Every quote it shows you is checked '
        'character-by-character against the actual document. Here\'s what happened under the hood:'
        '</p>',
        unsafe_allow_html=True
    )

    step_descs = {
        "gate_0":     ("🚧", "Input check", "Your question was checked — valid length and format."),
        "retrieval":  ("🔍", "Clause search", "The most relevant sections were pulled from your document."),
        "gate_1":     ("📋", "Format check", "The AI's response was checked to make sure it followed the required structure."),
        "gate_2":     ("✅", "Quote verification", "Every quote was checked word-for-word against the original document."),
        "gate_2b":    ("🔢", "Number check", "Any numbers or amounts were verified against the source text."),
        "conflict":   ("⚔️", "Contradiction scan", "Documents were compared for contradictions on the same topic."),
        "verdict":    ("⚖️", "Final answer", "The verdict was decided by the rules engine, not by the AI."),
    }

    for event in res.trace:
        gate  = event.get("gate", "event")
        status = event.get("status", "INFO")
        icon_default, label_default, desc_default = step_descs.get(gate, ("📌", gate.title(), ""))

        ok_statuses = {"PASS", "FINAL", "CONSISTENT", "ABSTAIN", "VERIFIED", "SUPPORTED", "PARTIAL"}
        warn_statuses = {"WARN", "CONFLICT_FOUND", "EVALUATE", "DROPPED"}
        if status in ok_statuses:
            badge_cls, badge_txt = "audit-pass", "✓ Passed"
        elif status in warn_statuses:
            badge_cls, badge_txt = "audit-info", "⚠ Note"
        else:
            badge_cls, badge_txt = "audit-fail", "✗ Failed"

        st.markdown(
            f'<div class="audit-row">'
            f'<div class="audit-icon">{icon_default}</div>'
            f'<div class="audit-text"><b>{label_default}</b> — {desc_default}'
            f'<span class="audit-badge {badge_cls}">{badge_txt}</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    if res.dropped_claims:
        st.markdown("**A few things the AI said that we couldn't verify:**")
        for d in res.dropped_claims:
            st.markdown(
                f"- *\"{d.get('text')}\"* — "
                f"the quote it gave didn't exactly match the document text, so we left it out."
            )

    if res.retrieved_chunks:
        with st.expander("🗂️ Document sections we read", expanded=False):
            for c, sc in res.retrieved_chunks:
                label = c.clause_label or "General"
                relevance = int(sc * 100)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                    f'<span style="font-size:0.8rem;color:#6366f1;font-weight:700;width:90px;flex-shrink:0;">{relevance}% match</span>'
                    f'<span style="font-size:0.82rem;color:#374151;">{c.doc_name} — {label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ─────────────────────────────────────────────────────────
#  Footer
# ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-size:0.8rem;color:#9ca3af;padding:0.5rem 0 1.5rem;">'
    '⚖️ ClauseLens helps you understand what a policy says — it\'s not legal advice. '
    'For decisions involving significant money or your rights, always consult a qualified professional.<br/>'
    '🔒 Your documents are processed entirely on your device and are never sent anywhere.'
    '</div>',
    unsafe_allow_html=True
)
