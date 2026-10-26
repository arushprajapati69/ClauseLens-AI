"""Streamlit Web Application for ClauseLens AI.

Customer-facing policy understanding assistant with:
- Strict local-only privacy guarantee
- 7-section structured output
- Side-by-side conflict visualization & dual financial calculations
- Trust panel displaying verifiable gate traces
"""

import os
import streamlit as st
import config
from ingest import extract_text_from_file, chunk_document
from store import PolicyIndex
from pipeline import answer_question, Result
from llm import LLMClient

st.set_page_config(
    page_title="ClauseLens AI — Customer Policy Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    h1, h2, h3, .main-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .main-title {
        font-size: 2.2rem;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .privacy-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 9999px;
        color: #10b981;
        font-size: 0.8rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }

    .verdict-card {
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        color: #ffffff;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    .verdict-SUPPORTED {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
    }
    .verdict-CONFLICT {
        background: linear-gradient(135deg, #dc2626 0%, #f59e0b 100%);
    }
    .verdict-PARTIAL {
        background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
    }
    .verdict-INSUFFICIENT_EVIDENCE {
        background: linear-gradient(135deg, #475569 0%, #64748b 100%);
    }
    .verdict-ERROR {
        background: linear-gradient(135deg, #991b1b 0%, #b91c1c 100%);
    }

    .chip {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .chip-fee { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
    .chip-deadline { background-color: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
    .chip-exclusion { background-color: #ffedd5; color: #c2410c; border: 1px solid #fed7aa; }
    .chip-eligibility { background-color: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }
    .chip-other { background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

    .source-quote {
        border-left: 4px solid #3b82f6;
        padding: 0.6rem 1rem;
        background: rgba(59, 130, 246, 0.05);
        border-radius: 0 8px 8px 0;
        font-style: italic;
        margin: 0.5rem 0;
    }
    
    .dual-calc-box {
        background: rgba(248, 250, 252, 0.8);
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.8rem 0;
    }
</style>
""", unsafe_allow_html=True)


# Session state initialization
if "index" not in st.session_state:
    st.session_state.index = PolicyIndex(cache_dir=".cache")
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = set()
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "selected_model" not in st.session_state:
    st.session_state.selected_model = config.GEN_MODEL


# Sidebar: Documents & Settings
with st.sidebar:
    st.markdown("### 🔍 ClauseLens AI")
    st.markdown('<div class="privacy-badge">🔒 100% On-Device & Private</div>', unsafe_allow_html=True)
    st.caption("Uploaded documents never leave your machine. Embeddings and structured analysis run locally via Ollama.")

    st.markdown("---")
    st.subheader("1. Policy Documents")
    uploaded_files = st.file_uploader(
        "Upload Policies (PDF, TXT, MD)",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for uf in uploaded_files:
            if uf.name not in st.session_state.indexed_docs:
                with st.spinner(f"Indexing '{uf.name}'..."):
                    temp_path = os.path.join(".cache", uf.name)
                    with open(temp_path, "wb") as f:
                        f.write(uf.getbuffer())
                    try:
                        pages = extract_text_from_file(temp_path, filename=uf.name)
                        chunks = chunk_document(uf.name, pages)
                        raw_content = "\n".join(p["text"] for p in pages)
                        st.session_state.index.add_document(uf.name, raw_content, chunks)
                        st.session_state.indexed_docs.add(uf.name)
                        st.toast(f"Indexed {uf.name} ({len(chunks)} chunks)", icon="✅")
                    except Exception as e:
                        st.error(f"Error indexing {uf.name}: {e}")

    # Load Sample Documents Button
    if st.button("📁 Load Sample Documents", use_container_width=True):
        samples = [
            "stayeasy_terms.md",
            "stayeasy_faq.md",
            "voltedge_warranty.md",
            "clipstream_subscription.md"
        ]
        with st.spinner("Indexing synthetic sample policies..."):
            for s in samples:
                s_path = os.path.join("sample_docs", s)
                if os.path.exists(s_path) and s not in st.session_state.indexed_docs:
                    pages = extract_text_from_file(s_path)
                    chunks = chunk_document(s, pages)
                    raw_text = "\n".join(p["text"] for p in pages)
                    st.session_state.index.add_document(s, raw_text, chunks)
                    st.session_state.indexed_docs.add(s)
            st.toast("Loaded 4 sample policy documents!", icon="📚")

    if st.session_state.indexed_docs:
        st.markdown("**Indexed Documents:**")
        for doc in sorted(st.session_state.indexed_docs):
            st.markdown(f"- 📄 `{doc}`")
        if st.button("Clear Index", type="secondary", use_container_width=True):
            st.session_state.index.clear()
            st.session_state.indexed_docs = set()
            st.session_state.last_result = None
            st.rerun()
    else:
        st.info("No documents indexed yet. Upload a policy or click 'Load Sample Documents'.")

    st.markdown("---")
    st.subheader("2. Model Selection")
    chosen_model = st.selectbox(
        "Local LLM",
        options=[config.GEN_MODEL, config.LOW_RAM_GEN_MODEL],
        index=0,
        help="llama3.1:8b is recommended for rigorous reasoning. Choose 3.2:3b for low-RAM machines."
    )
    st.session_state.selected_model = chosen_model


# Main Interface
st.markdown('<div class="main-title">ClauseLens AI</div>', unsafe_allow_html=True)
st.markdown("##### Verifiable consumer policy comprehension with character-level quote citations & conflict checks.")

# Question & Scenario Form
with st.container():
    col_q, col_btn = st.columns([5, 1])
    with col_q:
        default_q = "Can I get a full refund if I cancel my hotel reservation 5 days before check-in?"
        question = st.text_input(
            "What would you like to know about your policy?",
            placeholder="e.g. Can I cancel my booking? Is water damage covered under warranty?",
            value=""
        )

    # Optional Scenario Expander
    with st.expander("⚙️ Optional Scenario Parameters (Dates & Payment Amount)", expanded=False):
        st.caption("Specify timeline and amount to activate deterministic Python refund and notice calculators.")
        c_sc1, c_sc2, c_sc3 = st.columns(3)
        with c_sc1:
            start_date = st.date_input("Start / Check-in Date", value=None)
        with c_sc2:
            action_date = st.date_input("Action / Cancellation Date", value=None)
        with c_sc3:
            amount_paid = st.number_input("Amount Paid (₹ INR)", min_value=0, value=0, step=500)

    with col_btn:
        st.write("")
        st.write("")
        analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)


# Run Pipeline
if analyze_clicked and question:
    if not st.session_state.indexed_docs:
        st.warning("Please upload or load at least one policy document first!")
    else:
        scenario = {}
        if start_date and action_date:
            scenario["start_date"] = str(start_date)
            scenario["action_date"] = str(action_date)
        if amount_paid > 0:
            scenario["amount_paid"] = int(amount_paid)

        with st.spinner("Retrieving clauses, verifying verbatim quotes, and evaluating conflicts..."):
            client = LLMClient(model=st.session_state.selected_model)
            res = answer_question(
                question=question,
                index=st.session_state.index,
                scenario=scenario,
                client=client,
                model=st.session_state.selected_model
            )
            st.session_state.last_result = res


# Render Structured Results (Strict Order 1 to 7)
res: Result = st.session_state.last_result

if res:
    st.markdown("---")

    # 1. Verdict Card
    verdict_titles = {
        "SUPPORTED": "✅ Policy Supported — Fully Grounded",
        "CONFLICT": "⚠️ Policy Conflict Detected Between Documents",
        "PARTIAL": "ℹ️ Partially Supported / Conditional Evidence",
        "INSUFFICIENT_EVIDENCE": "❓ Insufficient Evidence — Clarification Recommended",
        "ERROR": "🚨 Analysis Error"
    }
    verdict_class = f"verdict-{res.verdict}"
    st.markdown(f"""
    <div class="verdict-card {verdict_class}">
        <h3 style="margin: 0; color: white;">{verdict_titles.get(res.verdict, res.verdict)}</h3>
        <p style="margin: 6px 0 0 0; opacity: 0.95; font-size: 0.95rem;">
            Verdict derived deterministically by Python Gatekeeper based on character-level quote matching and conflict evaluations.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 2. Plain-Language Answer
    if res.bottom_line and res.verdict != "INSUFFICIENT_EVIDENCE":
        st.markdown("### 📋 Bottom Line")
        st.info(res.bottom_line)

    # 3. Watch Out Highlights
    if res.verified_claims:
        chips = []
        for c in res.verified_claims:
            ctype = c.get("type", "other").lower()
            text = c.get("text", "")
            icon = {"fee": "💸", "deadline": "⏰", "exclusion": "⚠️", "eligibility": "📋"}.get(ctype, "📌")
            chips.append(f'<span class="chip chip-{ctype}">{icon} <b>{ctype.upper()}:</b> {text}</span>')

        if chips:
            st.markdown("### ⚠️ Watch Out: Critical Conditions & Fees")
            st.markdown("".join(chips), unsafe_allow_html=True)
            st.write("")

    # 4. Verified Sources & Citations
    if res.verified_claims:
        st.markdown("### 📖 Verified Sources & Citations")
        for idx, c in enumerate(res.verified_claims, 1):
            page_info = f", Page {c['page']}" if c.get("page") else ""
            st.markdown(f"**[{idx}] {c.get('doc_name')} ({c.get('clause_label')}{page_info})**")
            st.markdown(f'<div class="source-quote">"{c.get("quote")}"</div>', unsafe_allow_html=True)

    # 5. Conflict Panel (Side-by-Side)
    if res.conflicts:
        st.markdown("### ⚔️ Cross-Document Conflict Analysis")
        for idx, conf in enumerate(res.conflicts, 1):
            st.warning(f"**Discrepancy #{idx} — Topic: {conf.topic}**\n\n{conf.explanation}")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"##### 📄 Document A: `{conf.doc_a}`")
                st.caption(f"Clause: {conf.clause_label_a}")
                st.markdown(f'<div class="source-quote">"{conf.quote_a}"</div>', unsafe_allow_html=True)
                if "terms_calc" in res.calculations:
                    t_amt = res.calculations["terms_calc"].get("refund_amount", 0)
                    t_pct = res.calculations["terms_calc"].get("refund_percent", 0)
                    st.markdown(f"""
                    <div class="dual-calc-box">
                        <b>Financial Math Under Document A:</b><br/>
                        Notice Window: {res.calculations.get('days_notice', 'N/A')} days<br/>
                        Refund Percent: {t_pct}%<br/>
                        <b>Estimated Refund: ₹{t_amt:,}</b>
                    </div>
                    """, unsafe_allow_html=True)

            with col_b:
                st.markdown(f"##### 📄 Document B: `{conf.doc_b}`")
                st.caption(f"Clause: {conf.clause_label_b}")
                st.markdown(f'<div class="source-quote">"{conf.quote_b}"</div>', unsafe_allow_html=True)
                if "faq_calc" in res.calculations:
                    f_amt = res.calculations["faq_calc"].get("refund_amount", 0)
                    f_pct = res.calculations["faq_calc"].get("refund_percent", 0)
                    st.markdown(f"""
                    <div class="dual-calc-box">
                        <b>Financial Math Under Document B:</b><br/>
                        Notice Window: {res.calculations.get('days_notice', 'N/A')} days<br/>
                        Refund Percent: {f_pct}%<br/>
                        <b>Estimated Refund: ₹{f_amt:,}</b>
                    </div>
                    """, unsafe_allow_html=True)

        if res.precedence_hint:
            st.info(f"💡 **Precedence Hint:** {res.precedence_hint['hint']}\n\n*Quote:* \"{res.precedence_hint['quote']}\"\n\n*Note: Precedence statements in contracts are highlighted for awareness, but we recommend confirming directly with customer support.*")

    # 6. What to Ask Support
    if res.support_draft:
        st.markdown("### ✉️ What to Ask Support (Copyable Draft)")
        st.text_area(
            "Ready-to-send support query citing verified clauses:",
            value=res.support_draft,
            height=200
        )

    # 7. Trust Panel (Auditable Gate Trace)
    with st.expander("🛡️ Trust Panel & Gate Trace (Audit Log)", expanded=False):
        st.markdown("#### Verification Gate Log")
        st.caption("ClauseLens strictly enforces 3 deterministic gates. The LLM does not set confidence or perform math.")

        for event in res.trace:
            gate_name = event.get("gate", "Gate Event")
            status = event.get("status", "INFO")
            icon = "✅" if status in ("PASS", "FINAL", "CONSISTENT") else ("⚠️" if status in ("WARN", "CONFLICT_FOUND", "EVALUATE") else "🛑")
            st.markdown(f"- {icon} **{gate_name}**: `{status}` — {event}")

        if res.dropped_claims:
            st.markdown("#### ❌ Dropped Claims (Gate 2 Quote Verification Failure)")
            for d in res.dropped_claims:
                st.markdown(f"- Claim: *{d.get('text')}* from `{d.get('doc_name')}`\n  Reason: `{d.get('reason')}`")

        if res.retrieved_chunks:
            st.markdown("#### 📊 Retrieved Chunks & Hybrid Scores")
            for c, sc in res.retrieved_chunks:
                st.markdown(f"- `{c.chunk_id}` (`{c.doc_name}`, {c.clause_label}) — Hybrid Score: `{sc:.3f}`")

st.markdown("---")
st.caption("⚖️ **Legal Disclaimer:** ClauseLens AI provides automated text extraction and policy assistance for consumer preparation. It does not provide legal advice. All document processing is performed 100% locally on your machine.")
