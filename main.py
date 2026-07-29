import os
import json
import statistics
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import StructuredTool

load_dotenv()

app = FastAPI()

rubrics_db = {}
scorecards_db = {}

class Criterion(BaseModel):
    name: str
    weight: float = Field(..., ge=0, le=1)
    description: str

class Rubric(BaseModel):
    id: str
    criteria: list[Criterion]

class CriterionScore(BaseModel):
    criterion_name: str
    score: int = Field(..., ge=0, le=100)
    evidence_quote: str
    improvement_note: str

class ScoreCard(BaseModel):
    report_id: str
    rubric_id: str
    criterion_scores: list[CriterionScore]
    weighted_total: float
    needs_human_review: bool
    review_reason: Optional[str] = None

class RubricRequest(BaseModel):
    criteria: list[Criterion]

class ScoreRequest(BaseModel):
    report: str
    rubric_id: str

@app.post("/rubrics")
def create_rubric(req: RubricRequest):
    if abs(sum(c.weight for c in req.criteria) - 1.0) > 1e-6:
        raise HTTPException(400, "Weights must sum to 1.0")
    rubric = Rubric(id=str(uuid4()), criteria=req.criteria)
    rubrics_db[rubric.id] = rubric
    return rubric

@app.get("/rubrics/{rubric_id}")
def get_rubric(rubric_id: str):
    if rubric_id not in rubrics_db:
        raise HTTPException(404, "Not found")
    return rubrics_db[rubric_id]

def _build_tools(rubric: Rubric):
    tools = []
    for crit in rubric.criteria:
        def scorer(report_text: str, c=crit) -> dict:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
            prompt = f"""
Criterion: {c.name}
Description: {c.description}
Score the following report (0-100) and return a JSON object with keys:
criterion_name, score (int), evidence_quote (exact from report), improvement_note.
Report:
{report_text}
"""
            raw = llm.invoke(prompt).content
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"criterion_name": c.name, "score": 0, "evidence_quote": "", "improvement_note": "Parse error"}
            return data

        tool = StructuredTool.from_function(
            func=scorer,
            name=f"score_{crit.name.replace(' ', '_')}",
            description=f"Scores the report on '{crit.name}' only."
        )
        tools.append(tool)
    return tools

@app.post("/score")
async def score_report(req: ScoreRequest):
    rubric = rubrics_db.get(req.rubric_id)
    if not rubric:
        raise HTTPException(404, "Rubric not found")

    tools = _build_tools(rubric)
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    agent = create_openai_tools_agent(
        llm, tools,
        system_message="You are an orchestrator. Call EVERY tool EXACTLY ONCE with the provided report text. After all calls, say DONE."
    )
    executor = AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True, verbose=False)

    result = await executor.ainvoke({"input": req.report})
    steps = result["intermediate_steps"]

    scores = []
    for action, output in steps:
        try:
            data = json.loads(output) if isinstance(output, str) else output
            scores.append(CriterionScore(**data))
        except:
            continue

    if len(scores) != len(rubric.criteria):
        raise HTTPException(500, "Incomplete scores")

    score_map = {s.criterion_name: s for s in scores}
    ordered = []
    for crit in rubric.criteria:
        s = score_map.get(crit.name)
        if not s:
            raise HTTPException(500, f"Missing score for {crit.name}")
        ordered.append(s)

    weighted_total = sum(s.score * crit.weight for s, crit in zip(ordered, rubric.criteria))
    stdev = statistics.stdev([s.score for s in ordered]) if len(ordered) > 1 else 0.0
    needs_review = stdev > 15
    reason = f"High score variance (σ={stdev:.1f})" if needs_review else None

    card = ScoreCard(
        report_id=str(uuid4()),
        rubric_id=rubric.id,
        criterion_scores=ordered,
        weighted_total=round(weighted_total, 2),
        needs_human_review=needs_review,
        review_reason=reason
    )
    scorecards_db[card.report_id] = card
    return card

@app.get("/score/{report_id}/breakdown")
def get_breakdown(report_id: str):
    card = scorecards_db.get(report_id)
    if not card:
        raise HTTPException(404, "Not found")
    return {
        "report_id": card.report_id,
        "rubric_id": card.rubric_id,
        "weighted_total": card.weighted_total,
        "needs_human_review": card.needs_human_review,
        "review_reason": card.review_reason,
        "scores": [
            {"criterion": s.criterion_name, "score": s.score, "quote": s.evidence_quote, "note": s.improvement_note}
            for s in card.criterion_scores
        ]
                  }
