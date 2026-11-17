"""Standalone clinical analysis and preliminary symptom assessment dashboards."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st


st.set_page_config(
    page_title="Breast Cancer Clinical Analysis",
    page_icon=":material/health_and_safety:",
    layout="wide",
)

MODULE2_DIR = Path(__file__).resolve().parent
MODULE3_DIR = MODULE2_DIR.parent / "module3_multimodal_fusion"
if str(MODULE3_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE3_DIR))

try:
    from clinical_adapter import predict_clinical_grade
    CLINICAL_ADAPTER_ERROR = None
except Exception as exc:
    predict_clinical_grade = None
    CLINICAL_ADAPTER_ERROR = f"{type(exc).__name__}: {exc}"


st.markdown(
    """
    <style>
    @font-face {
        font-family: "Plus Jakarta Sans";
        font-style: normal;
        font-weight: 200 800;
        font-display: swap;
        src: url("https://wecure-five.vercel.app/_next/static/immutable/media/d8aeca813a9ab546-s.p.08ssgmy_tb90r.woff2") format("woff2");
    }
    :root {
        color-scheme: dark;
        --background:#0b1220; --foreground:#e6ebf2; --card:#142133;
        --elevated:#1b2a3e; --muted-foreground:#a1b0c5; --border:#2a394e;
        --primary:#22c5b7; --primary-hover:#48d7ca; --radius:14px;
        font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;
    }
    html, body, [data-testid="stAppViewContainer"] { min-height:100vh; background:var(--background); }
    .stApp { background:var(--background); color:var(--foreground); min-height:100vh; width:100%; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container {
        width:100% !important; max-width:none !important; min-height:100vh;
        padding:20px 20px 16px !important; box-sizing:border-box;
    }
    [data-testid="stMain"] { width:100%; max-width:none; background:transparent; }
    [data-testid="stHorizontalBlock"] { width:100%; max-width:none; align-items:stretch; gap:18px; }
    html, body { overflow-x: hidden; }
    h1, h2, h3, p, label, [data-testid="stWidgetLabel"] { color:var(--foreground) !important; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif; }
    h1 { font-size:clamp(27px,2.35vw,32px) !important; letter-spacing:-.035em; margin-bottom:.25rem !important; }
    h2, h3 { letter-spacing:-.02em; }
    [data-testid="stCaptionContainer"] { color:var(--muted-foreground) !important; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        width:100%; min-width:0; box-sizing:border-box;
        background:var(--card); border:1px solid var(--border) !important;
        border-radius:18px !important; box-shadow:none !important;
    }
    .st-key-module2_assessment_form_card,
    .st-key-module2_assessment_summary_card,
    .st-key-module2_assessment_form_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-module2_assessment_summary_card [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:clamp(540px,70vh,680px) !important; height:100% !important;
        align-self:stretch !important; box-sizing:border-box !important;
    }
    .st-key-module2_assessment_form_card,
    .st-key-module2_assessment_form_card[data-testid="stVerticalBlock"],
    .st-key-module2_assessment_form_card > [data-testid="stVerticalBlock"] {
        display:flex !important; flex-direction:column !important;
        justify-content:space-between !important; gap:16px !important;
    }
    .st-key-module2_assessment_form_card > [data-testid="stVerticalBlock"] { flex:1 1 auto; }
    .st-key-module2_grade_input_card,
    .st-key-module2_grade_output_card,
    .st-key-module2_grade_input_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-module2_grade_output_card [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:clamp(460px,60vh,580px) !important; height:100% !important;
        align-self:stretch !important; box-sizing:border-box !important;
    }
    .st-key-module2_grade_input_card,
    .st-key-module2_grade_output_card,
    .st-key-module2_grade_input_card > [data-testid="stVerticalBlock"],
    .st-key-module2_grade_output_card > [data-testid="stVerticalBlock"] {
        display:flex !important; flex-direction:column !important;
        justify-content:space-between !important; gap:18px !important;
    }
    .st-key-module2_grade_input_card > [data-testid="stVerticalBlock"],
    .st-key-module2_grade_output_card > [data-testid="stVerticalBlock"] { flex:1 1 auto; }
    .st-key-module2_grade_output_card,
    .st-key-module2_grade_output_card [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:clamp(440px,56vh,560px) !important; height:auto !important;
        align-self:flex-start !important;
    }
    .st-key-module2_grade_input_card [data-testid="stForm"] > [data-testid="stVerticalBlock"] {
        display:flex !important; min-height:330px; flex-direction:column !important;
        justify-content:space-between !important; gap:18px !important;
    }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background:#dfe4e8 !important; border:1px solid #9daab5; border-radius:11px; color:#263442 !important;
    }
    div[data-baseweb="select"] *, div[data-baseweb="input"] * { color:#263442 !important; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif; }
    div[data-baseweb="select"] svg { color:#526170 !important; fill:#526170 !important; }
    div[data-testid="stNumberInput"] input { background:#dfe4e8 !important; color:#263442 !important; caret-color:#263442; }
    div[data-testid="stNumberInput"] button { background:#23364b; color:var(--foreground); border-color:var(--border); }
    [data-testid="stFileUploaderDropzone"], section[data-testid="stFileUploaderDropzone"] {
        background:var(--elevated) !important; border:1px dashed #3b5068 !important; color:var(--foreground) !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        background:#23364b !important; color:var(--foreground) !important; border-color:#3b5068 !important;
    }
    [data-baseweb="popover"] > div, [role="listbox"], [role="option"] {
        background:var(--card) !important; color:var(--foreground) !important;
    }
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        min-height:42px; border:0; border-radius:11px; font-weight:700;
        font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;
        background:var(--primary); color:#06212a; box-shadow:0 5px 15px rgba(34,197,183,.14);
    }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background:var(--primary-hover); color:#06212a;
    }
    [data-testid="stAlert"] { border-radius:11px; background:var(--elevated); color:var(--foreground); }
    [data-testid="stMetric"] { padding:13px 14px; border:1px solid var(--border); border-top:2px solid #22c5b7; border-radius:12px; background:var(--elevated); }
    [data-testid="stMetricLabel"] {
        display:inline-flex; width:fit-content; padding:4px 8px; border:1px solid #285453;
        border-radius:7px; background:#153b43; color:#7ce7dc !important;
        font-size:11px !important; font-weight:700 !important; letter-spacing:.035em;
    }
    [data-testid="stMetricValue"] { margin-top:7px; color:#e6ebf2 !important; font-size:21px !important; font-weight:700 !important; }
    .grade-success {
        padding:14px 16px; border:1px solid #96a6b1; border-radius:11px;
        background:#d8e0e4; color:#263442; font-size:15px; font-weight:700; line-height:1.5;
    }
    [data-testid="stProgressBar"] > div { background:#26364b; border-radius:999px; }
    [data-testid="stProgressBar"] > div > div { background:var(--primary); border-radius:999px; }
    [data-testid="stTabs"] [role="tab"] { color:var(--muted-foreground) !important; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif; font-weight:600; }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color:var(--primary) !important; }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background:var(--primary) !important; }
    [data-testid="stTabs"] [data-baseweb="tab-border"] { background:var(--border) !important; }
    /* Gently enlarge text across the clinical dashboard for easier reading. */
    h1 { font-size:34px !important; }
    h2 { font-size:22px !important; }
    h3 { font-size:18px !important; }
    p, label, [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"] { font-size:15px; }
    [data-testid="stCaptionContainer"] { font-size:14px !important; }
    input, select, textarea, [data-baseweb="select"] *, [data-baseweb="input"] * { font-size:15px !important; }
    button, div.stButton > button, div[data-testid="stFormSubmitButton"] > button { font-size:15px !important; }
    [data-testid="stTabs"] [role="tab"] { font-size:15px !important; }
    [data-testid="stMetricLabel"] { font-size:12px !important; }
    [data-testid="stMetricValue"] { font-size:21px !important; }
    .grade-success { font-size:16px; }
    a { color:var(--primary) !important; }
    hr { border-color:var(--border); }
    @media (max-width: 720px) {
        .block-container { padding:12px 10px !important; }
        .st-key-module2_assessment_form_card,
        .st-key-module2_assessment_summary_card,
        .st-key-module2_assessment_form_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-module2_assessment_summary_card [data-testid="stVerticalBlockBorderWrapper"] {
            min-height:0 !important; height:auto !important;
        }
        .st-key-module2_assessment_form_card,
        .st-key-module2_assessment_form_card[data-testid="stVerticalBlock"],
        .st-key-module2_assessment_form_card > [data-testid="stVerticalBlock"] {
            justify-content:flex-start !important; gap:14px !important;
        }
        .st-key-module2_grade_input_card,
        .st-key-module2_grade_output_card,
        .st-key-module2_grade_input_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-module2_grade_output_card [data-testid="stVerticalBlockBorderWrapper"] {
            min-height:0 !important; height:auto !important;
        }
        .st-key-module2_grade_input_card,
        .st-key-module2_grade_output_card,
        .st-key-module2_grade_input_card > [data-testid="stVerticalBlock"],
        .st-key-module2_grade_output_card > [data-testid="stVerticalBlock"],
        .st-key-module2_grade_input_card [data-testid="stForm"] > [data-testid="stVerticalBlock"] {
            min-height:0 !important; justify-content:flex-start !important; gap:14px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Breast Cancer Clinical Analysis")
st.caption("Clinical grade prediction and preliminary symptom assessment · Research prototype")

symptom_tab, grade_tab = st.tabs(["Breast health assessment", "Histologic grade model"])

SYMPTOM_QUESTIONS = {
    "New lump or swelling in breast/chest or armpit": "lump",
    "Unusual nipple changes": "nipple",
    "Unusual skin changes": "skin",
    "Unexpected breast/chest size or shape change": "shape",
}
ANSWER_OPTIONS = ["Select an answer", "Yes", "No", "Not sure"]


def render_symptom_assessment() -> None:
    """Render the existing questionnaire and summary without changing its rules."""
    form_panel, result_panel = st.columns([1.05, 0.95], gap="medium")

    with form_panel:
        with st.container(border=True, key="module2_assessment_form_card"):
            st.subheader("Breast health assessment")
            st.caption("Answer each item. The duration question appears if any symptom is Yes.")

            age_sex = st.columns(2)
            age = age_sex[0].number_input("Age", min_value=0, max_value=120, value=18, step=1)
            sex = age_sex[1].selectbox(
                "Sex", ["Select an answer", "Female", "Male", "Intersex", "Prefer not to say"]
            )

            symptom_answers: dict[str, str] = {}
            question_items = list(SYMPTOM_QUESTIONS.items())
            for start in (0, 2):
                question_columns = st.columns(2, gap="small")
                for column, (question, key) in zip(question_columns, question_items[start:start + 2]):
                    with column:
                        symptom_answers[key] = st.selectbox(
                            question, ANSWER_OPTIONS, key=f"symptom_{key}"
                        )

            any_symptom_yes = any(answer == "Yes" for answer in symptom_answers.values())
            family_duration = st.columns(2, gap="small")
            family_history = family_duration[0].selectbox(
                "Family history of breast or ovarian cancer",
                ANSWER_OPTIONS,
                key="family_history",
            )
            symptom_duration = None
            if any_symptom_yes:
                symptom_duration = family_duration[1].selectbox(
                    "How long have symptoms been present?",
                    ["Select a duration", "Less than 2 weeks", "2–6 weeks", "More than 6 weeks", "Not sure"],
                    key="symptom_duration",
                )

            all_answers_complete = (
                sex != "Select an answer"
                and family_history != "Select an answer"
                and all(answer != "Select an answer" for answer in symptom_answers.values())
                and (not any_symptom_yes or symptom_duration != "Select a duration")
            )
            submitted = st.button(
                "Create assessment summary",
                type="primary",
                disabled=not all_answers_complete,
                width="stretch",
                key="create_symptom_summary",
            )

    answers_snapshot = {
        "age": int(age),
        "sex": sex,
        "symptoms": symptom_answers,
        "family_history": family_history,
        "symptom_duration": symptom_duration if any_symptom_yes else None,
    }

    if submitted:
        reported_symptoms = [
            question for question, key in SYMPTOM_QUESTIONS.items()
            if symptom_answers[key] == "Yes"
        ]
        unsure_symptoms = [
            question for question, key in SYMPTOM_QUESTIONS.items()
            if symptom_answers[key] == "Not sure"
        ]
        if reported_symptoms:
            assessment_status = "One or more new or unusual changes were reported."
            recommendation = (
                "Please contact a qualified healthcare professional promptly to discuss these changes "
                "and arrange an appropriate medical evaluation. Symptoms can have causes other than cancer."
            )
        elif unsure_symptoms:
            assessment_status = "Some symptom responses were marked Not sure."
            recommendation = (
                "If you are uncertain about a change or it concerns you, contact a qualified healthcare "
                "professional for advice and assessment."
            )
        else:
            assessment_status = "No listed new or unusual symptoms were reported."
            recommendation = (
                "Continue routine breast health care. Discuss screening appropriate to your age and personal "
                "history with a healthcare professional."
            )
        if family_history == "Yes":
            recommendation += " You also reported a family history; consider discussing it with a healthcare professional."

        assessment_id = f"BHA-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"
        st.session_state["assessment_result"] = {
            "answers": answers_snapshot,
            "symptoms": reported_symptoms,
            "status": assessment_status,
            "recommendation": recommendation,
            "assessment_id": assessment_id,
        }

    with result_panel:
        with st.container(border=True, key="module2_assessment_summary_card"):
            st.subheader("Assessment summary")
            result = st.session_state.get("assessment_result")
            if result and result["answers"] == answers_snapshot:
                st.caption(f"Assessment ID · {result['assessment_id']}")
                age_col, sex_col = st.columns(2)
                age_col.metric("Age", result["answers"]["age"])
                sex_col.metric("Sex", result["answers"]["sex"])
                st.markdown("**Assessment status**")
                st.write(result["status"])
                summary_columns = st.columns(2)
                with summary_columns[0]:
                    st.markdown("**Reported symptoms**")
                    if result["symptoms"]:
                        for item in result["symptoms"]:
                            st.write(f"• {item}")
                        if symptom_duration:
                            st.caption(f"Duration: {symptom_duration}")
                    else:
                        st.write("No symptom question was answered Yes.")
                with summary_columns[1]:
                    st.markdown("**Risk factors reported**")
                    st.write(f"Family history: {result['answers']['family_history']}")
                st.markdown("**Recommended medical evaluation**")
                st.write(result["recommendation"])
            elif result:
                st.caption("Your answers changed. Create a new summary to update the assessment.")
            else:
                st.caption("Complete the questionnaire to display the assessment summary.")

    st.caption(
        "Preliminary symptom assessment only; not a cancer diagnosis and does not estimate cancer probability. "
        "Discuss new or unusual changes with a healthcare professional."
    )


with symptom_tab:
    render_symptom_assessment()


with grade_tab:
    input_panel, result_panel = st.columns([1.05, 0.95], gap="medium")
    with input_panel:
        with st.container(border=True, key="module2_grade_input_card"):
            st.subheader("Histologic grade prediction")
            st.caption("Enter the five features expected by the saved Module 2 pipeline.")
            with st.form("clinical_grade_form"):
                numeric_columns = st.columns(2, gap="small")
                age_at_diagnosis = numeric_columns[0].number_input(
                    "Age at Diagnosis", min_value=0, max_value=120, value=None,
                    step=1, placeholder="Enter age",
                )
                tumor_size = numeric_columns[1].number_input(
                    "Tumor Size", min_value=0.0, value=None, step=0.1,
                    format="%.1f", placeholder="Enter tumor size",
                )
                receptor_columns = st.columns(3, gap="small")
                er_status = receptor_columns[0].selectbox("ER Status", ["Choose", "Positive", "Negative"])
                pr_status = receptor_columns[1].selectbox("PR Status", ["Choose", "Positive", "Negative"])
                her2_status = receptor_columns[2].selectbox("HER2 Status", ["Choose", "Positive", "Negative"])
                submitted_grade = st.form_submit_button(
                    "Predict histologic grade", type="primary", width="stretch"
                )

    if submitted_grade:
        feature_values = {
            "Age at Diagnosis": age_at_diagnosis,
            "Tumor Size": tumor_size,
            "ER Status": None if er_status == "Choose" else er_status,
            "PR Status": None if pr_status == "Choose" else pr_status,
            "HER2 Status": None if her2_status == "Choose" else her2_status,
        }
        if any(value is None for value in feature_values.values()):
            grade_result = {
                "status": "invalid_input",
                "predicted_grade": None,
                "grade_label": None,
                "message": "Enter age, tumor size, and select all three receptor statuses.",
            }
        elif predict_clinical_grade is None:
            grade_result = {
                "status": "dependency_unavailable",
                "predicted_grade": None,
                "grade_label": None,
                "message": f"Clinical model adapter unavailable: {CLINICAL_ADAPTER_ERROR}",
            }
        else:
            grade_result = predict_clinical_grade(feature_values)
        st.session_state["module2_grade_result"] = grade_result

    with result_panel:
        with st.container(border=True, key="module2_grade_output_card"):
            st.subheader("Model output")
            grade_result = st.session_state.get("module2_grade_result")
            if grade_result is None:
                st.caption("Submit the five clinical features to display a grade prediction.")
            elif grade_result.get("status") == "success":
                st.markdown(
                    f'<div class="grade-success">Predicted histologic grade · {grade_result["grade_label"]}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(grade_result.get("message", ""))
            else:
                st.error(grade_result.get("message", "Prediction is unavailable."))

            st.markdown("**Model information**")
            model_col, accuracy_col, macro_col = st.columns(3, gap="small")
            model_col.metric("Selected model", "Random Forest")
            accuracy_col.metric("Test accuracy", "51.26%")
            macro_col.metric("Test macro F1", "0.4386")
            st.caption(
                "Cross-validation macro F1: 0.4899. This model predicts grade among cancer records; "
                "it is not a cancer screening or diagnostic model and has not been clinically validated."
            )
