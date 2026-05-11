# HelloRecruiter Smart Router

A dynamic LLM routing system that categorizes user questions by difficulty and routes them to the appropriate AI model (e.g., Gemini Flash Lite for EASY, Gemini Flash for MID, Gemini Pro for TOUGH). 

To reduce latency, lower API costs, and maximize User Experience, the project was progressively upgraded through 4 architectural phases.

## 🚀 Architectural Upgrades (Phases 1 - 4)

### Phase 1: Pure LLM Routing
- **Architecture:** Every query makes 2 API calls. Call 1 uses `gemini-2.5-flash-lite` to classify the difficulty. Call 2 uses the selected model to generate the answer.
- **Latency:** ~4.5 seconds.
- **Cost:** High (Charged for every single classification and generation).

### Phase 2: Exact Match Caching
- **Architecture:** Introduced basic memory caching. If User B asks the exact same string as User A, the system returns the cached answer.
- **Latency:** 0 seconds for exact matches.
- **Cost:** Reduced for exact duplicates.

### Phase 3: Hybrid Architecture (Semantic Cache + Heuristics)
- **Architecture:** 
  1. **Self-Feeding Local DB:** Added `chromadb` and `sentence-transformers` to embed questions. If a question is 90% semantically similar to a previous one, it returns the answer instantly.
  2. **Heuristic Pre-Routing:** Added fast Python rules (length checks, keyword matching) to bypass the LLM classification step.
- **Latency:** ~30 milliseconds for cache hits. ~4.5 seconds for cache misses.
- **Cost:** Extremely low.

### Phase 4: Enterprise Upgrades (Current State)
- **1. Specialized Local ML Router:** Replaced the heuristic rules and LLM classifier with a lightweight offline `scikit-learn` text classifier. Takes 0 API calls and categorizes instantly.
- **2. Agentic Workflows:** Gave the `gemini-2.5-pro` model access to the **Google Search** tool for `TOUGH` questions, allowing it to autonomously search the internet for the latest architectures before responding.
- **3. Native Model Streaming:** Switched from blocking requests to `generate_content_stream`. The answer now streams onto the UI instantly like a typewriter.
- **4. The Data Flywheel:** Added a "Thumbs Up/Down" feedback UI that saves user ratings directly into `chromadb` for future fine-tuning.
- **5. Performance Timer:** Added a `⏱️ Response Time` tracker to visually prove the 0.03s response time of cached queries vs 4s+ API queries.

---

## 💬 Architecture Discussions (Q&A)

Below are the architectural discussions and decisions made during the development of this project with an LLM!

---

**Q: We need to save calls. How many calls are we making per input?**

**A:** Right now, the system makes **exactly 2 API calls** per input:
1. **The Classification Call:** It sends the question to `gemini-2.5-flash-lite` to figure out if it's EASY, MID, or TOUGH.
2. **The Generation Call:** It routes the original question to the specific model chosen to get the final answer.

Because we need to know the complexity of the question *before* we pick which model to use, that 1st classification call is necessary. However, to save calls, we can implement:
1. Input Caching (Recommended & Easy)
2. Keyword/Heuristic Pre-Filtering (Advanced)
3. Cache Only the Classification

---

**Q: How many API calls are we *now* making with the Phase 4 upgrades?**

**A:** With our new Phase 4 architecture, we have drastically reduced the number of API calls! 

**Scenario 1: You ask a repeat or similar question** (Cache Hit)
* Local Semantic Check: Uses the free local database.
* Classification: Skipped.
* Generation: Served from the local database.
* **Total API Calls: 0**

**Scenario 2: You ask a brand new question** (Cache Miss)
* Classification: Uses the free offline `scikit-learn` Machine Learning model. (0 API calls)
* Generation: Calls Gemini Flash/Pro to get the answer. (1 API call)
* **Total API Calls: 1**

So we dropped from a guaranteed **2 API calls** per question down to a maximum of **1 API call** (and **0** if the question was cached). That is a 50% to 100% cost reduction per user!

---

**Q: Why didn't we use RAG or REGX?**

**A:** That's a fantastic architectural question!

**1. Why not Regex (Regular Expressions)?**
Regex is incredibly fast and costs $0 and 0 API calls. It’s perfect for Safety Guardrails or strict keyword matching. 
*Why we didn't use it initially:*
- **Lack of Semantic Understanding:** Regex only looks for exact words. If we wrote a rule that triggers `TOUGH` when the user types "design architecture", it would work. But if a user typed "How should I structure a highly available backend?", Regex would miss it entirely.
- **Maintenance Nightmare:** To accurately classify "EASY" vs "MID" vs "TOUGH", you would have to maintain a massive dictionary of keywords, which becomes brittle over time. An LLM natively understands intent.

**2. Why not RAG (Retrieval-Augmented Generation)?**
RAG is used when the AI needs access to external, private, or real-time data that it wasn't trained on. 
*Why we didn't use it initially:*
- **No Custom Knowledge Base Needed (Yet):** Your requirement was to categorize general-purpose questions, coding questions, and tough dev projects. Gemini Pro and Flash already possess the vast coding and general knowledge required to answer these out of the box. 

---

**Q: What can we do? To save API calls think from a business purpose.**

**A:** From a business perspective, the goal isn't just to "make fewer calls," but to **reduce total inference cost, minimize latency, and preserve user experience**. Here are three tiers of optimization:

**Tier 1: The "Zero-Cost" Heuristic Router (Immediate ROI)**
Instead of asking the LLM to classify *every* question, we implement a lightning-fast local Python rule engine that runs first. (Length Checking, Regex/Keyword Matching). Only if these fail do we ask the classifier.

**Tier 2: Exact Match Caching (High ROI for repeated queries)**
If User B asks the exact same question as User A, we return the cached answer instantly. Saves 2 API calls.

**Tier 3: Semantic Caching (Advanced ROI)**
We use a free, local, lightweight open-source embedding model (like `all-MiniLM-L6-v2`) to convert questions into vectors. If a new question has a 95% semantic similarity to an old question, we return the cached answer.

---

**Q: ok i want hybrid of all these combined**
**1) a data base which feed it self with user inputs so next time if we find similar questoin we can send response from local db not from API**
**2) on bases of lingh find matching words then out  TIER 1**
**3) Caching**

**A:** Excellent choice! We built a hybrid system that combines all three tiers to maximize cost savings and performance:
1. **The Self-Feeding Local DB (Tier 3 + 2):** We used `chromadb` (a local database) and `sentence-transformers` (a tiny, free, local AI model) to embed questions. If a user asks "Tell me the capital of India", it checks the DB. If it's a 90% match to the already-saved "What is the capital of India?", it returns the answer instantly. **Zero API calls.**
2. **Heuristic Pre-Routing (Tier 1):** If the DB check misses, we run Python rules. If the question is short (e.g., "hello") or has obvious coding keywords, we skip the classification API call and route it directly. **Saves 1 API call.**
3. **The Loop:** If it's a brand new question, it goes through the LLMs, and the final answer is automatically inserted back into `chromadb`. The system gets cheaper and faster with every new user.

---

**Q: Our main focus is to reduce LLM calls and reduce the latency which increase user exprinnce. Isnt this workflow is time taking in terms of response generation?**

**A:** It might sound like we are adding a lot of "extra steps", but here is the math on why this actually **massively reduces latency**:

**Current Workflow Latency**
Right now, every single question takes 2 API trips over the internet to Google's servers:
1. Gemini Classification Call: ~1.5 seconds
2. Gemini Generation Call: ~3.0 seconds
*Total Current Latency: ~4.5 seconds*

**The Proposed Hybrid Workflow Latency**
Everything we proposed happens locally on your machine/server.
- Heuristic Python Rules: ~0.0001 seconds.
- Semantic DB Check: Converting a sentence to a vector and searching ChromaDB takes roughly ~0.03 seconds (30 milliseconds).

*Scenario A: Cache Hit (A similar question was found in DB)*
- DB Search: ~0.03s -> Answer returned instantly.
*Total Latency: 0.03 seconds (Massive UX Improvement)*

*Scenario B: Cache Miss (Brand new question)*
- DB Search: ~0.03s
- Heuristic check fails: ~0.0001s
- Call Gemini API: ~4.5s
*Total Latency: ~4.53 seconds*

By adding an imperceptible **30 milliseconds** of local processing time upfront, we gain the ability to drop response times to **near-zero** for repeat/similar questions, while eliminating thousands of API calls.

---

## ScreenShorts
### Local
<img width="1440" height="855" alt="Screenshot 2026-05-12 at 3 40 58 AM" src="https://github.com/user-attachments/assets/ddcf05e2-e112-4e88-92af-b6db8b75462e" />
<img width="1437" height="858" alt="Screenshot 2026-05-12 at 3 40 23 AM" src="https://github.com/user-attachments/assets/d2eaf6d7-1c65-41bb-858f-3b5ad0796a89" />
<img width="1434" height="857" alt="Screenshot 2026-05-12 at 3 39 34 AM" src="https://github.com/user-attachments/assets/fe2d4f66-1ccf-48c2-88c4-e105093426fd" />

### Live
<img width="1440" height="900" alt="Screenshot 2026-05-12 at 3 41 11 AM" src="https://github.com/user-attachments/assets/5968ab07-f949-4a44-8d83-68749eb862ce" />


## 🛠️ Setup & Deployment Guide

### Local Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/singhharsh77/hellorecruiter_Assessment.git
   cd hellorecruiter_Assessment
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure API Key:**
   Copy the `.env.example` file to `.env` and add your Google Gemini API key:
   ```bash
   cp .env.example .env
   # Edit .env and replace with your actual GEMINI_API_KEY
   ```
4. **Run the App:**
   ```bash
   streamlit run app.py
   ```
   *(Note: The very first time you ask a question, the app will pause for a minute to download the 80MB local semantic embedding model. After that, it will respond instantly.)*

### Cloud Deployment (Railway.app)
Because this app relies on a self-feeding Local Database (`ChromaDB`) to save money and latency, it requires **Permanent Storage** when deployed to the cloud. You cannot use standard serverless platforms.

1. **Deploy from GitHub:** Go to [Railway.app](https://railway.app/), create a "New Project", and select "Deploy from GitHub repo". Point it to your repository. Railway will detect the included `railway.json` and start the server automatically.
2. **Add API Key:** In the Railway dashboard for your service, go to **Variables**, add a new variable called `GEMINI_API_KEY`, and paste your key.
3. **Attach Permanent Storage (Crucial):** Go to the **Settings** tab of your service, scroll down to **Volumes**, click "Add Volume", and set the **Mount Path** to `/app/local_db`. If you skip this, your cache will be wiped clean every time the server restarts!
4. **Generate Domain:** In the **Networking** section of the Settings tab, click "Generate Domain" to get your public URL.
