import os
import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Rubric Scorer", layout="wide")

st.markdown(
    """
<style>
    body { background: #e0e5ec; }
    .block-container { padding-top: 2rem; }

    .neu-box {
        background: #e0e5ec;
        border-radius: 20px;
        box-shadow: 9px 9px 16px #a3b1c6, -9px -9px 16px #ffffff;
        padding: 24px;
        margin: 16px 0;
    }

    .neu-inset {
        background: #e0e5ec;
        border-radius: 20px;
        box-shadow: inset 6px 6px 12px #a3b1c6, inset -6px -6px 12px #ffffff;
        padding: 24px;
        margin: 16px 0;
    }

    .score-tile {
        background: #e0e5ec;
        border-radius: 16px;
        box-shadow: 5px 5px 10px #a3b1c6, -5px -5px 10px #ffffff;
        padding: 16px;
        margin: 10px 0;
        transition: all 0.2s;
    }

    .score-tile.flagged {
        border-left: 6px solid #d64045;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        background: #e0e5ec !important;
        border: none !important;
        border-radius: 14px !important;
        box-shadow: inset 3px 3px 8px #a3b1c6, inset -3px -3px 8px #ffffff !important;
        padding: 12px !important;
    }

    .stButton button {
        background: #e0e5ec !important;
        border: none !important;
        border-radius: 30px !important;
        box-shadow: 6px 6px 14px #a3b1c6, -6px -6px 14px #ffffff !important;
        color: #3a3a3a !important;
        font-weight: 600 !important;
        transition: 0.2s !important;
        padding: 10px 28px !important;
    }

    .stButton button:hover {
        box-shadow: inset 4px 4px 10px #a3b1c6, inset -4px -4px 10px #ffffff !important;
    }

    h1, h2, h3, h4 {
        color: #2c3e50;
    }
</style>
""",
    unsafe_allow_html=True,
)

col1, col2 = st.columns([2, 3])

with col1:
    st.markdown('<div class="neu-box">', unsafe_allow_html=True)
    st.header("Create Rubric")
    with st.form("rubric_form"):
        criteria_json = st.text_area(
            "Criteria (JSON list)",
            value='[{"name": "Methodology", "weight": 0.4, "description": "Clarity of method"}, '
                  '{"name": "Analysis", "weight": 0.6, "description": "Depth of analysis"}]',
            height=180,
        )
        create_btn = st.form_submit_button("Create Rubric")
        if create_btn:
            try:
                criteria = eval(criteria_json)   # in production use json.loads
                resp = requests.post(f"{BACKEND}/rubrics", json={"criteria": criteria})
                if resp.status_code == 200:
                    rubric_id = resp.json()["id"]
                    st.success(f"Rubric created: {rubric_id}")
                else:
                    st.error(resp.json().get("detail", "Creation failed"))
            except Exception as e:
                st.error(f"Invalid input: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="neu-box">', unsafe_allow_html=True)
    st.header("Score a Report")
    rubric_list_resp = requests.get(f"{BACKEND}/rubrics")
    rubric_options = {}
    if rubric_list_resp.status_code == 200:
        for r in rubric_list_resp.json().get("rubrics", []):
            rubric_options[r["id"]] = r

    if rubric_options:
        selected_id = st.selectbox(
            "Select Rubric",
            options=list(rubric_options.keys()),
            format_func=lambda x: f"{x} ({', '.join(c['name'] for c in rubric_options[x]['criteria'])})"
        )
    else:
        selected_id = st.text_input("Rubric ID", placeholder="e.g., from creation")

    report = st.text_area("Lab Report Text", height=220, placeholder="Paste the full report here...")

    if st.button("Score Report"):
        if not selected_id or not report:
            st.warning("Provide rubric ID and report text")
        else:
            with st.spinner("Evaluating with specialist agents ..."):
                score_resp = requests.post(
                    f"{BACKEND}/score",
                    json={"rubric_id": selected_id, "report": report},
                )
            if score_resp.status_code == 200:
                data = score_resp.json()
                st.markdown('<div class="neu-inset">', unsafe_allow_html=True)
                st.metric("Weighted Score", f"{data['weighted_total']} / 100")
                if data["needs_human_review"]:
                    st.error(f"Human review required: {data['review_reason']}")
                st.markdown('</div>', unsafe_allow_html=True)

                for sc in data["criterion_scores"]:
                    flagged = "flagged" if data["needs_human_review"] else ""
                    st.markdown(f'<div class="score-tile {flagged}">', unsafe_allow_html=True)
                    st.markdown(f"**{sc['criterion_name']}** — Score: `{sc['score']}`")
                    st.caption(f"Evidence: {sc['evidence_quote']}")
                    st.caption(f"Improvement: {sc['improvement_note']}")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error(score_resp.json().get("detail", "Scoring failed"))
    st.markdown('</div>', unsafe_allow_html=True)
