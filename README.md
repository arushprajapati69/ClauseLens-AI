# ClauseLens AI — Local Customer Policy Assistant
**Hackathon Theme:** AI for Customer Experience  
**Core Thesis:** *The LLM does language work only. Python owns retrieval, quote verification, arithmetic, conflicts, and abstention.*

---

## 1. What is ClauseLens AI?
ClauseLens AI is an open-source, 100% private desktop assistant for everyday consumers. Customers upload business policy documents (hotel cancellation policies, Terms of Service, hardware warranties, subscription contracts, FAQs) and ask natural-language questions about their personal situation:
- *Can I get a refund if I cancel my booking 5 days before check-in?*
- *Is water or liquid damage covered under this earbud warranty?*
- *What happens if I cancel after the free trial?*
- *Which fees, exclusions, or deadlines should I know before buying?*
- *Why might my refund or warranty claim be rejected?*

ClauseLens eliminates the two most dangerous failure modes of consumer RAG: **hallucinated deadline math** and **silent conflict resolution**.

---

## 2. System Architecture & Three-Gate Philosophy

```
Upload Docs (.pdf, .txt, .md) 
   │
   ▼
[Ingestion: clause-aware chunking (numbered sections, headings, Q&As)]
   │
   ▼
[Embedding & Caching: nomic-embed-text -> disk cache keyed by SHA256]
   │
   ▼
Customer Question (+ optional scenario: start_date, action_date, amount_paid)
   │
   ▼
[Gate 0: Input check]  Reject empty or > 1,000 characters
   │
   ▼
[Hybrid Retrieval: Cosine Similarity + Keyword Overlap Boost]
   │── best score < MIN_RETRIEVAL_SCORE ──► [INSUFFICIENT_EVIDENCE] (LLM never called)
   ▼
[Algorithmic Conflict Pairing: Cross-document chunks with similarity >= PAIR_SIM_THRESHOLD]
   │── Deterministic ranking: numeric mismatches (+10), polarity cues (+5)
   │── LLM Judge evaluates top candidate pairs
   └── Gate 2 verifies BOTH quotes verbatim in source chunks
   ▼
[LLM Answer Generation: llama3.1:8b with JSON Schema]
   │── Context wrapped in untrusted <excerpt chunk_id="..."> delimiters
   ▼
[Gate 1: Schema & Chunk Allowlist]
   │── Enforces required JSON keys and allowed claim types
   │── Rejects any cited chunk_id not in the retrieved set
   ▼
[Gate 2: Verbatim Quote Verification & Gate 2b Numeric Grounding]
   │── Normalized character-by-character quote verification (drops invalid claims)
   │── Checks that every number, fee, and duration is grounded in source text or scenario
   ▼
[Deterministic Tools: Python Scenario Calculators]
   │── days_between(start_date, action_date)
   └── apply_refund_tiers(days_notice, amount_paid, tiers, flat_fee)
       └── Dual-reading financial math if documents conflict
   ▼
[Deterministic Verdict Engine]
   └── SUPPORTED | PARTIAL | CONFLICT | INSUFFICIENT_EVIDENCE | ERROR
   ▼
[Streamlit UI: 7-Section Structured Customer View + Auditable Trust Gate Trace]
```

---

## 3. Calibrated Thresholds & Rationale

All tunables live centrally in `config.py`:

| Parameter | Calibrated Value | Engineering Rationale |
| :--- | :--- | :--- |
| `MIN_RETRIEVAL_SCORE` | **0.38** | Calibrated against the evaluation benchmark. Cosine scores below 0.38 represent unrelated boilerplate (e.g. general preamble or off-topic queries). Setting the gate at 0.38 reliably triggers deterministic `INSUFFICIENT_EVIDENCE` abstention without wasting LLM compute. |
| `PAIR_SIM_THRESHOLD` | **0.50** | Determines whether two chunks from different documents discuss the "same topic" (e.g. cancellation deadlines). Below 0.50, candidate pairing produces spurious comparisons; at 0.50+, topic clustering isolates legitimate contradictions (such as FAQ 24-hour vs Terms 3–7 day policies). |
| `MAX_CONFLICT_PAIRS` | **3** | Caps the maximum number of candidate pairs sent to the LLM judge to prevent quadratic latency overhead on consumer CPUs. |
| `CHUNK_MAX_CHARS` | **900** | Preserves complete numbered clauses and sub-sections while fitting within the local model's optimal attention span. |
| `LLM_TIMEOUT` | **120.0s** | Client timeout to prevent UI hangs during multi-step CPU inference. |

---

## 4. How to Run Locally

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) installed and running locally on port 11434.

### Step-by-Step Setup
```bash
# 1. Pull the required local models in Ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. Navigate to project directory
cd clauselens-ai

# 3. Create and activate a virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the unit test suite (LLM-free, pure Python)
pytest -o pythonpath=.

# 6. Run the automated evaluation benchmark
python eval/run_eval.py

# 7. Launch the Streamlit application
streamlit run app.py
```

---

## 5. Limitations & Assumptions to Validate

1. **Scanned Documents & OCR:** The current implementation uses pure text extraction via `pypdf`. Scanned documents, handwritten receipts, and bitmap images are unsupported in this MVP and are rejected with a descriptive error.
2. **Local Model Reasoning:** `llama3.1:8b` is highly capable at text extraction, but complex conditional legalese can occasionally yield dropped claims. The three-gate system catches these failures and downgrades to `PARTIAL` rather than presenting false information.
3. **Document Versioning:** ClauseLens operates on the text of uploaded files. If an uploaded policy is outdated, the system cannot detect external revisions unless an explicit date is contained within the document.
4. **Hinglish & Regional Consumer Agreements:** Consumer documents in India often mix Hindi and English or use colloquial expressions. The MVP targets English policy text; multilingual performance must be validated.
5. **Legal Framing:** ClauseLens is designed as an automated policy-understanding assistant and dispute-preparation tool. It explicitly states in every view that it does not provide formal legal advice.
