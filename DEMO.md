# ClauseLens AI — Live Hackathon Demo Script (4–5 Minutes)

**Presenter:** Solo First-Year BTech Student  
**Target Audience:** Hackathon Judges ("AI for Customer Experience" track)  
**Hardware Setup:** Standard laptop running local Ollama (`llama3.1:8b` & `nomic-embed-text`) with zero cloud dependencies.

---

## Part 1: The Problem & Pitch (0:00 – 1:00)

**[Speaker Hook]**  
> *"Good morning, judges. Have you ever tried to cancel a hotel reservation or file an electronics warranty claim, only to find yourself trapped between contradictory FAQs, 40-page PDFs of legalese, and customer service bots that hallucinate promises they can't keep?*
> 
> *In customer experience, when high-stakes money or warranties are on the line, probabilistic chatbots fail. They hallucinate dates, mess up deadline arithmetic, and silently pick a side when documents disagree.*
> 
> *This is ClauseLens AI—a 100% private, on-device policy assistant. Our core principle is simple: **the LLM does language work only. Python owns retrieval, quote verification, arithmetic, conflicts, and abstention.** Let's see it in action."*

---

## Part 2: Demo 1 — The Planted Conflict & Financial Math (1:00 – 2:30)

**[Action in App]**
1. Click **"Load Sample Documents"** in the sidebar. Note the toast notification: 4 policies indexed locally.
2. In the Scenario Parameters expander, set:
   - Check-in Date: `2026-11-10`
   - Cancellation Date: `2026-11-05` (5 days notice)
   - Amount Paid: `₹12,000`
3. Enter Question:
   > *"Can I get a full refund if I cancel my hotel reservation 5 days before check-in?"*
4. Click **Analyze**.

**[Speaker Voiceover]**  
> *"Watch what happens here:
> 1. Instead of giving a generic 'yes' or 'no', ClauseLens raises an immediate **CONFLICT** verdict card.
> 2. It detected that StayEasy's marketing FAQ promises 'Free cancellation up to 24 hours before check-in', while Section 4.2 of their binding Terms of Service permits only a 50% refund for 3 to 6 days notice.
> 3. ClauseLens doesn't guess who is right. Notice the dual financial calculation cards:
>    - Under the FAQ: estimated refund is ₹12,000 (100%).
>    - Under the Terms: estimated refund is ₹6,000 (50%).
> 4. Notice the Precedence Alert: Python detected Clause 9.1 where StayEasy states the Terms prevail over marketing materials.
> 5. Best of all, look at the **'What to Ask Support'** box: it generated a ready-to-copy email citing both clauses so the customer can negotiate for the full ₹12,000 refund."*

---

## Part 3: Demo 2 — Strict Warranty Exclusions (2:30 – 3:30)

**[Action in App]**
1. Clear the scenario parameters.
2. Enter Question:
   > *"Is water damage or dropped earbuds covered under the VoltEdge warranty?"*
3. Click **Analyze**.

**[Speaker Voiceover]**  
> *"Now let's check a warranty dispute. Customers often submit claims without realizing exclusions.
> 1. Verdict is **SUPPORTED** (Green card).
> 2. Look at the **Watch Out** chips: it highlights `EXCLUSION: Liquid & moisture exposure` and `EXCLUSION: Physical & accidental abuse`.
> 3. Under **Verified Sources**, notice quotation markers `[1]` and `[2]`. Every single quote shown is verified character-for-character against the raw document via Gate 2. If an LLM paraphrases or fabricates a word, the claim is dropped."*

---

## Part 4: Demo 3 — Deterministic Abstention (3:30 – 4:15)

**[Action in App]**
1. Enter Question:
   > *"Can I transfer my hotel booking to another person or family member?"*
2. Click **Analyze**.

**[Speaker Voiceover]**  
> *"Here is the ultimate test of an AI system: **admitting what it doesn't know**.
> 
> Most consumer bots will invent a generic answer like 'Yes, most hotels allow transfers with ID.'
> 
> But StayEasy's policy contains no clause about transferring bookings.
> 
> ClauseLens immediately surfaces an **INSUFFICIENT EVIDENCE** verdict. It refuses to guess, skips the LLM generation when scores are ungrounded, and instructs the user to contact support with a drafted inquiry."*

---

## Part 5: Demo 4 — The Trust Panel & Conclusion (4:15 – 5:00)

**[Action in App]**
1. Open the **Trust Panel & Gate Trace** expander at the bottom.

**[Speaker Voiceover]**  
> *"Finally, everything in ClauseLens is auditable. The Trust Panel logs all three gates:
> - Gate 1: JSON schema compliance and chunk allowlists.
> - Gate 2: Verbatim quote string verification and numeric grounding.
> - Gate 3: Safe execution.
> 
> ClauseLens runs completely on-device. No customer documents are uploaded to third-party clouds. It is safe, verifiable, and puts customer rights first.
> 
> Thank you! I welcome your questions."*
