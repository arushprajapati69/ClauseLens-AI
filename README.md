# ClauseLens AI

**Understand any policy — in plain English.**

ClauseLens is a free, open-source tool that helps you make sense of the policies, terms, and agreements that businesses send you. Upload any document and ask questions in plain language. Get clear answers, with the exact lines from the document so you can verify everything yourself.

---

## What it's for

Ever tried to figure out whether you can get a refund, what's covered under your warranty, or what happens if you cancel a subscription — and ended up more confused after reading the policy than before?

ClauseLens is built for exactly that. Some things it's great at:

- *"Can I get a refund if I cancel 3 days before check-in?"*
- *"Is water damage covered under my earbuds warranty?"*
- *"What happens if I miss a payment?"*
- *"Are there any hidden fees I should know about?"*
- *"Why might they reject my claim?"*

It reads the document for you, finds the relevant parts, checks them for accuracy, and gives you a straight answer.

---

## What makes it different

Most AI tools either hallucinate answers or give vague summaries with no way to check the source. ClauseLens does things differently:

**Every quote is verified.** When ClauseLens shows you text from a document, it checks it character-by-character against the original. If it doesn't match exactly, it gets left out.

**No guessing on numbers.** Refund percentages, notice periods, and fees are calculated by code — not by the AI. So you get the real number, not a probabilistic guess.

**Contradictions are surfaced.** If two parts of a policy say different things (which happens more often than you'd think), ClauseLens shows you both sides instead of picking one silently.

**Honest when it doesn't know.** If the answer isn't in the document, ClauseLens says so and tells you what to ask the company directly.

**100% private.** Your documents never leave your machine. Everything runs locally.

---

## Getting started

### What you need

- Python 3.10 or newer
- [Ollama](https://ollama.ai) installed and running on your machine

### Setup (5 minutes)

```bash
# 1. Download the two AI models that ClauseLens uses
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. Clone the repo and go into the project folder
git clone https://github.com/your-username/clauselens-ai.git
cd clauselens-ai

# 3. Create a virtual environment
python -m venv venv

# On Windows:
.\venv\Scripts\Activate.ps1
# On Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch
streamlit run app.py
```

That's it. The app will open at **http://localhost:8501**

---

## How to use it

1. **Upload a document** — any PDF, text file, or Markdown file works. Terms and conditions, warranty cards, subscription agreements, FAQ pages, lease agreements, anything.

2. **Ask your question** — type naturally, like you'd ask a friend. *"Can I get my money back?"* or *"What's not covered?"*

3. **Add dates and amounts if relevant** — if you want an exact refund calculation, you can enter your check-in date, cancellation date, and how much you paid.

4. **Read the answer** — ClauseLens shows you a plain-English answer plus the exact quote from the document so you can double-check it yourself.

5. **Copy the support email** — if you need to contact the company, there's a ready-to-send email that cites the relevant clauses. Companies tend to respond better when you quote their own policy back at them.

---

## Running the tests

The core logic (quote verification, conflict detection, refund math) is tested without needing any AI at all:

```bash
pytest tests/
```

All 29 tests should pass in about 1–2 seconds.

---

## Hardware requirements

| Model | RAM needed | Notes |
|-------|-----------|-------|
| llama3.1:8b (default) | ~8 GB | Best accuracy |
| llama3.2:3b (lite) | ~4 GB | Faster, works on most laptops |

Both work on CPU — no GPU needed.

---

## What it can and can't do

**It can:**
- Read PDF, TXT, and Markdown files
- Handle multiple documents at once and compare them
- Calculate exact refund amounts when you provide dates and payment amount
- Flag contradictions between different documents
- Generate a draft email for customer support

**It can't (yet):**
- Read scanned documents or images (only searchable PDFs with actual text)
- Process documents in languages other than English
- Access the internet or check for newer versions of a policy
- Give formal legal advice

---

## Contributing

Bug reports, feature suggestions, and pull requests are very welcome. The codebase is intentionally straightforward — a first-year student should be able to follow it.

---

## License

MIT License — free to use, modify, and share.

---

## Disclaimer

ClauseLens helps you understand what a policy says. It is not a substitute for legal advice. For any decision involving significant money or your legal rights, please consult a qualified professional.
