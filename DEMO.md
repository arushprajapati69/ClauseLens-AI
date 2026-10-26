# ClauseLens AI — Guided Walkthrough & Test Guide

ClauseLens is a private, on-device assistant that helps customers read, verify, and understand complex policy documents — without legal jargon, confusing fine print, or cloud uploads.

---

## Quick Start (30 Seconds)

1. **Launch the application:**
   ```bash
   streamlit run app.py
   ```
2. Open your browser to `http://localhost:8501`.
3. In the sidebar, click **"📚 Load Example Policies"** to index 4 built-in documents:
   - StayEasy Hotel — Terms & Conditions
   - StayEasy Hotel — Marketing FAQ
   - VoltEdge Wireless Earbuds — Warranty Card
   - ClipStream — Subscription & Cancellation Terms

---

## Scenario 1: Spotting Hidden Contradictions & Calculating Refunds

Policies and FAQs often disagree. ClauseLens spots these contradictions automatically and calculates both outcomes.

### Steps:
1. In the sidebar, under **Optional: Your Situation**, enter:
   - **Check-in date:** `2026-11-10`
   - **Cancellation date:** `2026-11-05` (5 days notice)
   - **Amount paid:** `12000`
2. In the main question box, ask:
   > *"Can I get a full refund if I cancel my hotel reservation 5 days before check-in?"*
3. Click **Analyse Policy**.

### What you'll see:
- ⚠️ **Conflict Detected** banner — highlights that the FAQ promises *"Free cancellation up to 24 hours before check-in"*, while Section 4.2 of the Terms of Service allows only a *50% refund* for 3 to 6 days notice.
- **Dual Calculations** — side-by-side refund amounts:
  - FAQ: ₹12,000 (100% refund)
  - Terms of Service: ₹6,000 (50% refund)
- **Document Precedence Alert** — highlights Clause 9.1 where the Terms state they override promotional materials.
- **Support Draft** — a pre-written, ready-to-copy email referencing both clauses for you to send to customer support.

---

## Scenario 2: Uncovering Warranty Exclusions

When you need a repair or replacement, companies often point to exclusions buried in the fine print.

### Steps:
1. Clear the dates and amount from the situation panel.
2. Ask:
   > *"Is water damage or dropped earbuds covered under the VoltEdge warranty?"*
3. Click **Analyse Policy**.

### What you'll see:
- ✅ **Supported** verdict.
- **Watch Out Chips** — visual tags highlighting specific exclusions:
  - `⛔ Excluded: Liquid & moisture exposure`
  - `⛔ Excluded: Physical & accidental damage`
- **Verified Sources** — exact sentences quoted word-for-word from the original document with source page and section references.

---

## Scenario 3: Honest Abstention (Admitting What Isn't Covered)

Generic AI chatbots often guess or hallucinate when an answer isn't in the document. ClauseLens admits when a topic isn't mentioned.

### Steps:
1. Ask:
   > *"Can I transfer my hotel booking to another person or family member?"*
2. Click **Analyse Policy**.

### What you'll see:
- 🤷 **Not Found** verdict.
- A clear explanation that the uploaded documents contain no clause regarding booking transfers.
- Advice to contact the company directly before making plans.

---

## Scenario 4: Verifying Any Custom Policy

Upload your own documents:
1. Drag and drop any **PDF**, **TXT**, or **Markdown** file into the sidebar upload area.
2. Ask your question in plain, conversational language.
3. ClauseLens will parse sections, index them locally, and present answers backed by direct quotes.
