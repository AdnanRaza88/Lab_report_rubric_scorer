schema.md

```markdown
# Schema – Lab Report Rubric Scorer

## Data Models (Pydantic)

### Criterion

A single dimension of evaluation.

| Field       | Type    | Constraints             | Description |
|-------------|---------|--------------------------|-------------|
| name        | string  | required                 | Name of the criterion (e.g., "Methodology") |
| weight      | float   | 0 ≤ value ≤ 1           | Relative weight of this criterion (all weights must sum to 1.0) |
| description | string  | required                 | Detailed guideline for what a perfect score looks like |

**Example:**
```json
{
  "name": "Methodology",
  "weight": 0.4,
  "description": "Clarity of the experimental procedure, sample size, and reproducibility."
}
```

---

Rubric

A collection of criteria that together define a complete grading scheme.

Field Type Constraints Description
id string (UUID) auto‑generated Unique identifier for the rubric
criteria list[Criterion] at least one element, sum(weights) == 1.0 List of scoring criteria

Example:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "criteria": [
    {"name": "Methodology", "weight": 0.4, "description": "..."},
    {"name": "Analysis", "weight": 0.6, "description": "..."}
  ]
}
```

---

CriterionScore

The output of a single specialist scorer for one criterion.

Field Type Constraints Description
criterion_name string required Name of the criterion this score belongs to
score int 0 ≤ score ≤ 100 Numeric score for that criterion
evidence_quote string required Exact verbatim quote from the lab report that supports the score
improvement_note string required Suggestion for improvement

Example:

```json
{
  "criterion_name": "Methodology",
  "score": 85,
  "evidence_quote": "We measured 30 plant heights weekly for 4 weeks.",
  "improvement_note": "Mention calibration of the measuring instrument."
}
```

---

ScoreCard

The final aggregated result of a scored lab report.

Field Type Constraints Description
report_id string (UUID) auto‑generated Unique identifier for this scoring session
rubric_id string (UUID) required ID of the rubric used
criterion_scores list[CriterionScore] length equals number of rubric criteria Scores for each criterion
weighted_total float 0 ≤ value ≤ 100, computed in Python Σ(score × weight) rounded to 2 decimals
needs_human_review bool auto‑set True if standard deviation of scores > 15
review_reason string \| null present only when needs_human_review is true Explanation for the flag

Example:

```json
{
  "report_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "rubric_id": "550e8400-e29b-41d4-a716-446655440000",
  "criterion_scores": [
    {"criterion_name": "Methodology", "score": 85, "evidence_quote": "...", "improvement_note": "..."},
    {"criterion_name": "Analysis", "score": 75, "evidence_quote": "...", "improvement_note": "..."}
  ],
  "weighted_total": 79.0,
  "needs_human_review": false,
  "review_reason": null
}
```

---

API Endpoints

1. Create Rubric

POST /rubrics

Request Body:

```json
{
  "criteria": [
    {"name": "Methodology", "weight": 0.4, "description": "..."},
    {"name": "Analysis", "weight": 0.6, "description": "..."}
  ]
}
```

Validation:

· criteria must be a non‑empty list.
· Sum of all weight fields must equal 1.0.

Response (201):

```json
{
  "id": "generated-uuid",
  "criteria": [ ... ]
}
```

Error (400): {"detail": "Weights must sum to 1.0"}

---

2. List All Rubrics

GET /rubrics

Response:

```json
{
  "rubrics": [
    {
      "id": "...",
      "criteria": [ ... ]
    }
  ]
}
```

---

3. Get Rubric by ID

GET /rubrics/{rubric_id}

Response: Rubric object or 404 if not found.

---

4. Score a Lab Report

POST /score

Request Body:

```json
{
  "report": "Full lab report text...",
  "rubric_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Process:

· Orchestrator agent calls one specialist tool per criterion.
· Weighted total computed in Python.
· Human review flag set if stdev(scores) > 15.

Response: ScoreCard object (see above).
Errors: 404 (rubric not found), 500 (incomplete scores).

---

5. Get Score Breakdown

GET /score/{report_id}/breakdown

Response:

```json
{
  "report_id": "...",
  "rubric_id": "...",
  "weighted_total": 79.0,
  "needs_human_review": false,
  "review_reason": null,
  "scores": [
    {
      "criterion": "Methodology",
      "score": 85,
      "quote": "We measured 30 plant heights...",
      "note": "Mention calibration..."
    },
    ...
  ]
}
```

---

6. Guarded Score Endpoint (with name‑integrity check)

POST /score/guardrail

Same request and response as /score, but before returning the result the system verifies that the set of criterion_name values in the response exactly matches the rubric’s criteria names.
Error (422): {"detail": "Criterion names mismatch – guardrail triggered"}

---

Validation Rules Summary

Rule Applied where Error Code
sum(weights) == 1.0 POST /rubrics 400
0 ≤ score ≤ 100 Pydantic model (automatic rejection) 422 (unprocessable entity if LLM output out of range)
All criteria must be scored exactly once POST /score 500
Criterion name integrity POST /score/guardrail 422
Non‑existent rubric ID POST /score, GET /rubrics/{id} 404

```
