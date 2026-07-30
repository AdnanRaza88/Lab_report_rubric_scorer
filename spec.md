Software Design Document (SDD)

Project: Lab Report Rubric Scorer (E9)


---

1. Introduction

The Lab Report Rubric Scorer automates grading of lab reports using a multi‑agent AI system. A user defines a rubric (criteria + weights) and submits a lab report. The system dynamically creates a specialist scoring agent for each criterion, scores the report, calculates a deterministic weighted total, and flags inconsistent results for manual review.

---

2. System Architecture

```
[Streamlit UI] ⟷ HTTP ⟷ [FastAPI Backend]
                          │
                          ├─ POST /rubrics
                          ├─ GET  /rubrics
                          ├─ GET  /rubrics/{id}
                          ├─ POST /score
                          ├─ GET  /score/{id}/breakdown
                          └─ POST /score/guardrail
                                │
                                ▼
                         [LangChain Agents]
                                │
                                ▼
                         [Groq LLM (llama-3.1-8b-instant)]
```

Components:

· Streamlit Frontend – provides a neumorphism‑styled user interface.
· FastAPI Backend – exposes REST endpoints, manages in‑memory databases (rubrics, scorecards), and orchestrates agents.
· LangChain – wraps LLM into specialist scorer tools and an orchestrator agent.
· Groq LLM – the free, fast LLM used for all scoring (easily replaceable with Gemini or OpenAI).

---

3. Data Models (Pydantic Schemas)

Criterion – single grading dimension.

```json
{
  "name": "string",
  "weight": "float (0–1)",
  "description": "string"
}
```

Rubric – collection of criteria.

```json
{
  "id": "uuid",
  "criteria": "list[Criterion]"
}
```

Constraint: sum(c.weight for c in criteria) == 1.0.

CriterionScore – output of one specialist agent.

```json
{
  "criterion_name": "string",
  "score": "int (0–100)",
  "evidence_quote": "string (exact from report)",
  "improvement_note": "string"
}
```

ScoreCard – aggregated result.

```json
{
  "report_id": "uuid",
  "rubric_id": "uuid",
  "criterion_scores": "list[CriterionScore]",
  "weighted_total": "float (calculated in Python)",
  "needs_human_review": "boolean",
  "review_reason": "string|null"
}
```

---

4. API Endpoints

Method Path Request Body Response Description
POST /rubrics {"criteria": [Criterion]} Rubric Create a new rubric. Rejects if weights do not sum to 1.
GET /rubrics – {"rubrics": [Rubric]} List all stored rubrics.
GET /rubrics/{id} – Rubric Fetch a single rubric.
POST /score {"rubric_id": str, "report": str} ScoreCard Score a lab report using the given rubric.
GET /score/{report_id}/breakdown – {"report_id":..., "scores": [...]} Detailed breakdown of criterion scores.
POST /score/guardrail same as /score ScoreCard Same as /score but verifies criterion name integrity before returning.

---

5. Agent Orchestration Logic

1. Rubric Retrieval – the backend fetches the rubric from the in‑memory store.
2. Specialist Agent Creation – for each Criterion, a LangChain StructuredTool is built:
   · It calls a Groq LLM with a prompt that includes the criterion’s name, description, and the full report text.
   · The LLM is instructed to output a JSON object matching CriterionScore.
3. Orchestrator Agent – a LangChain AgentExecutor is instantiated with all specialist tools.
   · System message: "Call EVERY tool EXACTLY ONCE with the provided report text. After all calls, say DONE."
   · It coordinates the parallel or sequential execution of tools (LangChain handles tool‑calling order).
4. Result Collection – intermediate steps are parsed; each tool’s JSON output is converted to a CriterionScore.
5. Deterministic Calculation – Python iterates over ordered criteria and scores to compute weighted_total = sum(score * weight).
6. Human Review Flag – if statistics.stdev(scores) > 15, needs_human_review is set to True with a reason.

---

6. Guardrails

Guardrail Implementation Trigger
Weight sum validation Pydantic Field + manual check in POST /rubrics Request processing
Score range enforcement CriterionScore.score defined as int, ge=0, le=100 Pydantic validation on agent output
Consistency flag Standard deviation > 15 After all scores are collected
Criterion name integrity In /score/guardrail, the set of returned names is compared with the rubric’s criterion names After score collection, before returning
Orchestrator instruction Prompt enforces exactly‑once tool calls Soft guard – relies on LLM compliance

---

7. Environment Variables

Variable Default Description
GROQ_API_KEY – API key for Groq LLM (required)
BACKEND_URL http://localhost:8000 FastAPI backend URL (used by Streamlit)

---

8. Deployment / Run Instructions

```bash
pip install -r requirements.txt
cp .env.example .env   # fill GROQ_API_KEY
uvicorn app:app --reload   # backend
streamlit run streamlit_app.py   # frontend
```

---

9. Testing Guidelines

1. Valid Rubric Creation – weights sum exactly 1 → success; otherwise error 400.
2. List Rubrics – after creation, GET /rubrics shows the rubric.
3. Score a Report – submit a rubric ID and a lab report. Verify:
   · Each criterion gets a score 0‑100.
   · evidence_quote is an exact substring from the report (manual check).
   · improvement_note is meaningful.
   · weighted_total equals Σ(score × weight).
   · Standard deviation > 15 triggers needs_human_review = True.
4. Missing Rubric – POST /score with nonexistent ID returns 404.
5. Breakdown Endpoint – after scoring, fetch /score/{report_id}/breakdown and confirm all fields.
6. Guardrail Endpoint – use /score/guardrail; if an agent returns a wrong criterion name, the request should fail with 422.
7. UI Flow – create rubric, score report, observe neumorphism styling, check breakdown inside the app.

---

End of SDD
