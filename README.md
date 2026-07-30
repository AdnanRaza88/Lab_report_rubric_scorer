Lab Report Rubric Scorer (E9)

AI-powered lab report grading with multi-agent orchestration and deterministic score calculation.

---

Overview

Teachers and professors spend hours evaluating lab reports against detailed rubrics. This project automates the entire process: you define a rubric (criteria + weights), submit a lab report, and the system dynamically creates a specialist AI agent for each criterion. All agents score the report in parallel, extract exact evidence quotes, and provide improvement suggestions. The weighted total is calculated by Python – not the LLM – guaranteeing zero arithmetic errors. If the scores are highly inconsistent, the system flags the report for manual review.

---

Features

· Dynamic Rubric Creation – define any number of criteria, each with a weight (sum = 1.0) and a description of what constitutes a perfect score.
· Agent-as-Tool Orchestration – every criterion gets its own specialist LLM agent, wrapped as a tool. An orchestrator agent calls all of them exactly once.
· Verbatim Evidence Extraction – each agent pulls an exact quote from the report to justify its score.
· Deterministic Weighted Total – final grade computed in plain Python, avoiding LLM hallucination in math.
· Human Review Flagging – if the standard deviation of criterion scores exceeds 15, the system sets needs_human_review = true and explains why.
· Neumorphism UI – a clean, 3D-style Streamlit interface with soft shadows and inset fields.
· Guardrails – weight sum validation, score range enforcement, and an optional endpoint that verifies all criterion names match the rubric.

---

Tech Stack

Layer Technology
Frontend Streamlit (custom HTML/CSS for neumorphism)
Backend FastAPI (Python 3.10+)
LLM / AI Groq (model llama-3.1-8b-instant) via langchain-groq
Agent Framework LangChain (create_openai_tools_agent, StructuredTool)
Data Validation Pydantic
Environment python-dotenv
Math Python statistics module

---

Architecture

```
┌─────────────────┐     HTTP      ┌──────────────────┐
│  Streamlit UI   │◄──────────────►│   FastAPI Server  │
└─────────────────┘               │                  │
                                  │  Rubric Store    │
                                  │  ScoreCard Store │
                                  │                  │
                                  │  Orchestrator    │
                                  │     Agent        │
                                  │   ┌──────┐       │
                                  │   │Tool 1│───────► Groq LLM
                                  │   ├──────┤       │
                                  │   │Tool 2│───────► Groq LLM
                                  │   ├──────┤       │
                                  │   │ ...  │       │
                                  │   └──────┘       │
                                  └──────────────────┘
```

1. User submits a rubric (JSON) via the UI or API.
2. For scoring, the backend dynamically creates a specialist tool for each criterion.
3. An orchestrator agent invokes all tools, collects their structured JSON responses.
4. Python computes the weighted total and checks score variance.
5. The scorecard is returned and displayed in the UI.

---

Quick Start

Prerequisites

· Python 3.10 or higher
· A Groq API key (free – get it at console.groq.com)

Installation

```bash
git clone https://github.com/yourusername/lab-report-scorer.git
cd lab-report-scorer
pip install -r requirements.txt
cp .env.example .env   # then edit .env with your GROQ_API_KEY
```

Environment Variables

Create a .env file with:

```env
GROQ_API_KEY=gsk_your_api_key_here
BACKEND_URL=http://localhost:8000   # optional, default is localhost
```

Running the Application

1. Start the backend (from the project root):
   ```bash
   uvicorn app:app --reload
   ```
2. Start the Streamlit frontend (in a new terminal):
   ```bash
   streamlit run streamlit_app.py
   ```
3. Open http://localhost:8501 in your browser.

---

Usage

1. Create a Rubric

In the left column of the UI, enter a list of criteria in JSON format. For example:

```json
[
  {
    "name": "Methodology",
    "weight": 0.4,
    "description": "Clear steps, sample size, reproducibility"
  },
  {
    "name": "Analysis",
    "weight": 0.6,
    "description": "Correct statistical tests, interpretation"
  }
]
```

Click Create Rubric. The system will assign a unique ID and show it on the screen.

2. Score a Lab Report

In the right column, select the rubric from the dropdown. Paste the lab report text into the text area. Example:

```
The experiment involved measuring 30 plant heights weekly for 4 weeks.
We used a ruler and recorded data in a table. Average growth was 5 cm.
A t-test gave p=0.03, indicating significant growth.
```

Click Score Report. After a few seconds you will see:

· Weighted Score – the final percentage.
· Per‑Criterion Cards – score, exact evidence quote, and improvement suggestion.
· Human Review Warning (if the scores are too inconsistent).

3. View Detailed Breakdown

You can also retrieve the scorecard via the API:

```bash
curl http://localhost:8000/score/{report_id}/breakdown
```

---

API Reference (main endpoints)

Method Endpoint Description
POST /rubrics Create a new rubric (body: {"criteria": [...]})
GET /rubrics List all rubrics
GET /rubrics/{id} Get one rubric
POST /score Score a report (body: {"rubric_id":..., "report":...})
GET /score/{id}/breakdown Get detailed breakdown
POST /score/guardrail Score + name‑integrity guardrail

Full interactive docs at http://localhost:8000/docs.

---

Screenshots

(Replace these with actual screenshots of your running app.)

Rubric Creation

screenshots/rubric_create.png

Report Scoring

screenshots/scoring.png

Score Breakdown

screenshots/breakdown.png

---

Testing

1. Create a valid rubric – the UI will accept it and show the ID.
2. Try an invalid rubric – e.g., weights summing to 0.9 → error message should appear.
3. Score a report – verify that every criterion returns a score between 0–100, a quote from the report, and a note.
4. Inconsistent scores – if you craft a rubric and report that likely gives very different scores (e.g., Methodology 95, Analysis 20), the app should flag it for human review.
5. Guardrail endpoint – call /score/guardrail with a rubric whose criterion names you manually change in a test; expect a 422 error.

---

Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

License

MIT
