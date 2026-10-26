# ClauseLens AI — Idea Brief
**Theme:** AI for Customer Experience  
**Stage:** Hackathon Prototype (Solo First-Year BTech Builder)  
**Status:** Phase 0 Feasibility & Product Brief  

---

## 1. The Idea in Plain Language
ClauseLens AI is a local, private desktop assistant that reads complex consumer policy documents—hotel cancellation rules, electronics warranties, subscription fine print, and refund terms—and directly answers questions about a customer's specific situation. 

Instead of trusting a large language model to guess terms or do date and fee math in its head, ClauseLens uses Python to deterministically find clauses, verify verbatim quotes, detect conflicts between separate documents (such as marketing FAQs versus official Terms of Service), calculate refunds or notice periods, and abstain when information is missing.

---

## 2. The Exact Customer Problem and Beneficiaries

### The Problem
When customers face cancellations, unexpected charges, or equipment failures, they are forced to parse dense, legalese-laden policy documents or wait in customer service queues. Businesses often present contradictory information across marketing FAQs and binding Terms of Service. Furthermore, standard consumer AI chatbots hallucinate policies, hallucinate deadline math, or fabricate reassuring answers that lead customers to lose money.

### Who Benefits
- **Everyday Consumers:** Travelers cancelling hotel bookings, buyers with defective gadgets, and subscribers trying to cancel before recurring subscription charges hit.
- **Support-Weary Customers:** Users preparing to contest an unfair denial or chargeback who need exact, cited clause evidence and discrepancy proofs before emailing support.
- **Privacy-Conscious Individuals:** Users dealing with sensitive booking details, invoices, and warranties who refuse to upload personal documents to third-party cloud AI APIs.

---

## 3. Realistic Customer Walkthrough

1. **The Situation:** Priya booked a 3-night stay at "StayEasy" starting on November 10th for ₹12,000. On November 5th (5 days before check-in), an emergency forces her to cancel.
2. **The Contradiction:**
   - The StayEasy FAQ page promises: *"Free cancellation up to 24 hours before check-in on standard rates."*
   - The binding StayEasy Terms of Service (Section 4.2) states: *"Cancellations made between 3 and 6 days prior to check-in receive a 50% refund."*
3. **The Interaction:**
   - Priya uploads `stayeasy_terms.md` and `stayeasy_faq.md` to ClauseLens AI.
   - She inputs her scenario: Check-in Date: `2026-11-10`, Cancellation Date: `2026-11-05`, Amount Paid: `₹12,000`.
   - Question: *"Can I get a full refund if I cancel today?"*
4. **The System Response:**
   - **Verdict:** `CONFLICT` (Red/Amber alert).
   - **Discrepancy Breakdown:** Displays side-by-side verified quotes from Section 4.2 of the Terms (50% refund) and Section 2 of the FAQ (Free cancellation up to 24 hours).
   - **Deterministic Financial Math:**
     - Under FAQ: Refund = ₹12,000 (100%).
     - Under Terms: Refund = ₹6,000 (50% of ₹12,000).
   - **Precedence Notice:** Highlights Section 9.1 of the Terms which states that the Terms prevail over marketing/FAQ materials.
   - **Support-Ready Draft:** Generates a ready-to-send support query explicitly pointing out the discrepancy between the FAQ and Terms to negotiate the full refund.

---

## 4. How ClauseLens Differs from Generic Chatbots & Document Summarisers

| Dimension | Generic Chatbot (e.g., ChatGPT / standard RAG) | Document Summariser | ClauseLens AI |
| :--- | :--- | :--- | :--- |
| **Arithmetic & Deadlines** | LLM predicts numbers; frequently botches date subtraction and tiered percentages. | Does not compute; merely truncates text. | **Python owns arithmetic:** pure functions calculate notice days, fee deductions, and refund tiers. |
| **Citation Rigour** | Often hallucinates near-miss quotes or summarizes without exact grounding. | Leaves verification to the user. | **Gate 2 Verbatim Verification:** Every single quote must match the source document text character-for-character. |
| **Contradiction Handling** | Silently averages or randomly picks one document's claim. | Lists statements without comparative cross-referencing. | **Algorithmic Conflict Detection:** Identifies cross-document topic pairs with numeric or polarity mismatches and presents both. |
| **Abstention Policy** | Eager to please; fabricates answers when policies omit a specific topic. | Summarizes unrelated boilerplate. | **Strict Abstention:** If evidence score is low or zero clauses exist, issues an `INSUFFICIENT_EVIDENCE` verdict. |
| **Privacy / Execution** | Cloud API dependent; leaks customer data to remote servers. | Often web-based. | **100% Local:** Runs on local Ollama instance; zero network egress. |

---

## 5. Existing Landscape & Meaningful Differentiation

### What Already Exists
- **Generic "Chat-with-PDF" tools** (ChatPDF, AskYourPDF): Basic vector RAG over embeddings. Vulnerable to hallucinated deadlines, lost clause numbers, and poor precision on short technical rules.
- **Notebook-style RAG assistants:** Brittle LangChain/LlamaIndex pipelines without deterministic guardrails or quote cross-referencing.
- **Terms of Service Summarisers** (Terms of Service; Didn't Read - ToS;DR): Hand-curated crowd summaries of major tech platforms; useless for arbitrary local hotel, warranty, or retail receipts/policies.
- **Enterprise Contract-Review Tools** (Ironclad, Robin AI, Kira Systems): Complex B2B legal tech suites priced in tens of thousands of dollars; focused on procurement and indemnification rather than retail customer protection.

### Where This Implementation Meaningfully Differs (No Uniqueness Claimed)
ClauseLens does not claim a novel foundational AI architecture. Instead, it demonstrates **system-level engineering discipline for high-stakes consumer workflows**:
1. Applying a strict **three-gate verification pipeline** (Schema, Verbatim Evidence, Safe Execution).
2. Separating **language comprehension** (delegated to an 8B local LLM) from **computation and verification** (enforced by Python).
3. Treating contradiction detection as an explicit UI primitive rather than an internal retrieval failure.

---

## 6. The Simplest Convincing Prototype (One Paragraph)
The minimum convincing prototype is a clean, local Streamlit dashboard where a user uploads 1–4 policy documents (PDF, TXT, or Markdown) and submits a question with an optional scenario date and amount. The system performs hybrid retrieval using cached `nomic-embed-text` embeddings and keyword overlap, evaluates cross-document numeric and polarity conflicts, queries `llama3.1:8b` via Ollama for structured clause extraction with a strict JSON schema, validates all extracted quotes verbatim in Python, calculates timeline and refund amounts via deterministic tools, and renders an unambiguous verdict card (Supported, Partial, Conflict, or Insufficient Evidence) backed by an auditable Trust gate log.

---

## 7. Limitations, Practical Challenges, and Assumptions to Validate

1. **Messy Real-World & Scanned PDFs:** Real business policies often arrive as low-quality scans, multi-column brochures, or complex tables. The MVP uses pure text extraction (`pypdf`) and explicitly rejects scanned documents without OCR. Validating robust layout extraction is a mandatory future step.
2. **8B Model Reasoning & Schema Compliance:** Local 8B models can occasionally omit fields or output malformed JSON if prompts are loose. Mitigated by using Ollama's native `format` JSON-schema enforcement and zero blind retries, falling back gracefully to retrieval-only mode if the model fails.
3. **Policy Versions and Effective Dates:** Documents often state *"Updated March 2024"*. If a user uploads an expired policy, the tool has no external knowledge to dispute the date unless explicitly provided by the user.
4. **Hinglish & Regional Languages:** Indian consumer agreements and customer support communications frequently mix Hindi and English or use regional phrasing. The MVP targets English policy text; multilingual performance on 8B models requires targeted evaluation.
5. **Legal-Liability Framing:** Clear disclaimers are essential. The UI and pipeline must explicitly state that ClauseLens provides automated general policy analysis and negotiation drafts, not formal legal counsel.
6. **Customer Demand Validation:** Do consumers want to read policies through an app, or do they only care after a claim is denied? The prototype focuses heavily on post-purchase dispute preparation ("Why might my claim be rejected?" and "What to ask support") to target active customer pain.
