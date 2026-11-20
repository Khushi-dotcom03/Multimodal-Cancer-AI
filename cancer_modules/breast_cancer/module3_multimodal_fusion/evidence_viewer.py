"""Standalone Streamlit viewer for separate image and clinical evidence."""

from __future__ import annotations

import sys
import tempfile
from math import isfinite
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image, UnidentifiedImageError


def experimental_fusion_result(
    image_result: dict[str, Any] | None,
    clinical_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Combine independent outputs into an explicitly uncalibrated research score."""
    if not image_result or not clinical_result:
        return None
    if image_result.get("status") not in {"success", "uncertain"}:
        return None
    if clinical_result.get("status") != "success":
        return None

    probabilities = image_result.get("class_probabilities") or {}
    try:
        malignant_score = float(probabilities["Malignant"])
        grade = int(clinical_result["predicted_grade"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

    if not isfinite(malignant_score) or not 0.0 <= malignant_score <= 1.0:
        return None
    if grade not in {1, 2, 3}:
        return None

    # This maps the ordinal histologic grade to a 0–1 index, not a cancer risk.
    grade_index = (grade - 1) / 2
    score = 0.8 * malignant_score + 0.2 * grade_index
    return {
        "prediction": "Cancer-like" if score >= 0.5 else "Non-cancer-like",
        "score": score,
        "non_cancer_score": 1 - score,
        "image_malignant_score": malignant_score,
        "clinical_grade_index": grade_index,
        "grade": grade,
        "image_uncertain": image_result.get("status") == "uncertain",
    }


st.set_page_config(
    page_title="Breast Cancer – Combined Analysis",
    page_icon=":material/health_and_safety:",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    html, body, [data-testid="stAppViewContainer"] { min-height: 100vh; background: #081522; }
    .stApp { background: #081522; color: #e9f2f7; min-height: 100vh; width: 100%; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container {
        width: 100% !important; max-width: none !important; min-height: calc(100vh - 1rem);
        padding: .8rem 1rem 1rem !important; box-sizing: border-box;
    }
    [data-testid="stMain"] { width: 100%; max-width: none; background: transparent; }
    [data-testid="stHorizontalBlock"] { width: 100%; max-width: none; }
    html, body { overflow-x: hidden; }
    h1, h2, h3, p, label, [data-testid="stWidgetLabel"] { color: #e9f2f7 !important; }
    h1 { font-size: 1.65rem !important; letter-spacing: -0.035em; margin-bottom: .15rem !important; }
    h2, h3 { letter-spacing: -.02em; }
    [data-testid="stCaptionContainer"] { color: #a9bdca !important; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        width: 100%; min-width: 0; box-sizing: border-box;
        background: #102335; border: 1px solid #25465b !important;
        border-radius: 14px !important;
    }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background: #0b1b29; border-color: #2b4b60; border-radius: 8px; color: #e9f2f7;
    }
    div[data-baseweb="select"] *, div[data-baseweb="input"] * { color: #e9f2f7; }
    div[data-testid="stNumberInput"] button { background: #173347; color: #e9f2f7; border-color: #2b4b60; }
    [data-testid="stFileUploaderDropzone"], section[data-testid="stFileUploaderDropzone"] {
        background: #0b1b29 !important; border: 1px dashed #31566b !important; color: #e9f2f7 !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        background: #173347 !important; color: #e9f2f7 !important; border-color: #31566b !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        min-height:150px !important; display:flex !important;
        flex-direction:column !important; align-items:center !important; justify-content:center !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] { text-align:center !important; }
    [data-testid="stFileUploaderDropzone"] button { align-self:center !important; margin-left:auto !important; margin-right:auto !important; }
    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stFileUploaderDropzoneInstructions"] *,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] [data-testid="stCaptionContainer"] {
        color:#f4f7fb !important; opacity:1 !important; visibility:visible !important;
        font-size:13px !important;
    }
    .st-key-module3_image_upload_card,
    .st-key-module3_image_upload_card [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:600px !important; height:100% !important;
    }
    .st-key-module3_preview_frame,
    .st-key-module3_preview_frame [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:460px !important; box-sizing:border-box !important;
    }
    .st-key-module3_preview_frame [data-testid="stVerticalBlock"] {
        min-height:430px !important; display:flex !important;
        flex-direction:column !important; align-items:center !important; justify-content:center !important;
    }
    .st-key-module3_preview_frame[data-testid="stVerticalBlock"] {
        min-height:360px !important; display:flex !important; flex-direction:column !important;
        align-items:center !important; justify-content:center !important;
    }
    .st-key-module3_preview_frame [data-testid="stImage"] {
        display:flex !important; width:100% !important; justify-content:center !important;
        max-height:400px !important; overflow:hidden !important; margin:auto !important;
    }
    .st-key-module3_preview_frame [data-testid="stImage"] img {
        width:auto !important; height:auto !important; max-width:360px !important;
        max-height:380px !important; object-fit:contain !important; margin:auto !important;
    }
    [data-baseweb="popover"] > div, [role="listbox"], [role="option"] {
        background: #102335 !important; color: #e9f2f7 !important;
    }
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        min-height: 2.35rem; border: 0; border-radius: 9px; font-weight: 700;
        background: #20b9ad; color: #061720;
    }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background: #3ad5c5; color: #061720;
    }
    [data-testid="stProgressBar"] > div > div { background: #20b9ad; }
    [data-testid="stAlert"], [role="alert"] {
        border-radius:10px !important; background:#173347 !important;
        color:#eef5f8 !important; border:1px solid #31566b !important;
    }
    [data-testid="stAlert"] p, [data-testid="stAlert"] span,
    [data-testid="stAlert"] div, [role="alert"] p, [role="alert"] span,
    [role="alert"] div {
        color:#eef5f8 !important; background:transparent !important;
    }
    @media (max-width: 720px) {
        .block-container { padding: .55rem .55rem .8rem !important; }
        .st-key-module3_image_upload_card,
        .st-key-module3_image_upload_card [data-testid="stVerticalBlockBorderWrapper"] { min-height:0 !important; height:auto !important; }
        .st-key-module3_preview_frame,
        [data-testid="stFileUploaderDropzone"] { min-height:140px !important; }
        .st-key-module3_preview_frame,
        .st-key-module3_preview_frame [data-testid="stVerticalBlockBorderWrapper"] { min-height:340px !important; }
        .st-key-module3_preview_frame [data-testid="stVerticalBlock"] { min-height:310px !important; }
        .st-key-module3_preview_frame [data-testid="stImage"] img { max-width:280px !important; max-height:280px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Add this file's folder so sibling adapters import reliably when launched from
# the project root with Streamlit.
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from image_adapter import predict_ultrasound
    IMAGE_ADAPTER_IMPORT_ERROR = None
except Exception as exc:
    predict_ultrasound = None
    IMAGE_ADAPTER_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

try:
    from clinical_adapter import predict_clinical_grade
    CLINICAL_ADAPTER_IMPORT_ERROR = None
except Exception as exc:
    predict_clinical_grade = None
    CLINICAL_ADAPTER_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


st.session_state.setdefault("module3_image_result", None)
st.session_state.setdefault("module3_clinical_result", None)

st.title("Multimodal Image + Clinical Analysis")
st.caption(
    "Upload a breast ultrasound image and enter clinical features to run the two existing analyses together. "
    "The model outputs remain separate evidence streams."
)
st.info(
    "BUSI ultrasound images and Module 2 clinical records are not patient-matched. "
    "The models were not trained together. This interface shows an experimental late-fusion "
    "research score when both outputs are available; it is uncalibrated and is not a clinical probability."
)

image_panel, controls_panel = st.columns([3, 2], gap="large")
uploaded_image = None
image_bytes = None

with image_panel:
    with st.container(border=True, key="module3_image_upload_card"):
        st.subheader("Image Upload")
        st.caption("Breast ultrasound image - PNG, JPG or JPEG")
        uploaded_image = st.file_uploader(
            "Upload a breast ultrasound image",
            type=["png", "jpg", "jpeg"],
            key="module3_ultrasound_upload",
        )
        st.caption("Maximum file size: 200 MB per image. Supported formats: PNG, JPG, JPEG.")
        if uploaded_image is not None:
            image_bytes = uploaded_image.getvalue()
            try:
                with Image.open(uploaded_image) as preview_image:
                    preview = preview_image.convert("RGB")
                with st.container(border=True, key="module3_preview_frame"):
                    st.image(
                        preview,
                        caption=f"Uploaded image: {uploaded_image.name}",
                        width=360,
                    )
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                st.warning(f"Image preview is unavailable: {exc}")
            metadata = st.columns(2, gap="small")
            metadata[0].caption(f"Format - {Path(uploaded_image.name).suffix.lstrip('.').upper()}")
            metadata[1].caption(f"Size - {uploaded_image.size / 1024:.1f} KB")
        else:
            st.caption("Upload an image to preview it here.")

with controls_panel:
    with st.container(border=True):
        st.subheader("Analysis Controls")
        st.caption("Enter the clinical details and run both analyses.")
        module_col, badge_col = st.columns([4, 1])
        module_col.markdown("**Selected module**  \nBreast Cancer Multimodal Review")
        badge_col.caption("Prototype")

        with st.form("module3_clinical_form"):
            st.markdown("**Patient clinical information**")
            st.caption("Enter the five features used by the saved clinical grade pipeline.")
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
            er_status = receptor_columns[0].selectbox(
                "ER Status", ["Positive", "Negative"], index=None, placeholder="Choose"
            )
            pr_status = receptor_columns[1].selectbox(
                "PR Status", ["Positive", "Negative"], index=None, placeholder="Choose"
            )
            her2_status = receptor_columns[2].selectbox(
                "HER2 Status", ["Positive", "Negative"], index=None, placeholder="Choose"
            )
            st.markdown("**Model configuration**")
            st.caption("Image - BUSI validator + MobileNetV2")
            st.caption("Clinical - saved Random Forest grade pipeline")
            st.caption("The adapters load their model files when analysis runs.")
            run_both = st.form_submit_button(
                "Analyze both inputs",
                type="primary",
                width="stretch",
            )

        if run_both:
            # Each adapter runs independently; nothing is joined or fused here.
            if uploaded_image is None or image_bytes is None:
                image_result = {
                    "status": "invalid_input",
                    "prediction": None,
                    "confidence": None,
                    "class_probabilities": {name: None for name in ("Normal", "Benign", "Malignant")},
                    "validator_probability": None,
                    "message": "Upload a BUSI ultrasound image before running both analyses.",
                }
            elif predict_ultrasound is None:
                image_result = {
                    "status": "dependency_unavailable",
                    "prediction": None,
                    "confidence": None,
                    "class_probabilities": {name: None for name in ("Normal", "Benign", "Malignant")},
                    "validator_probability": None,
                    "message": f"The image adapter could not be imported: {IMAGE_ADAPTER_IMPORT_ERROR}",
                }
            else:
                suffix = Path(uploaded_image.name).suffix.lower()
                temporary_path: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=suffix, prefix="busi_review_", delete=False
                    ) as temporary_file:
                        temporary_file.write(image_bytes)
                        temporary_path = Path(temporary_file.name)
                    image_result = predict_ultrasound(temporary_path)
                except Exception as exc:
                    image_result = {
                        "status": "prediction_error",
                        "prediction": None,
                        "confidence": None,
                        "class_probabilities": {name: None for name in ("Normal", "Benign", "Malignant")},
                        "validator_probability": None,
                        "message": f"Image analysis could not run: {type(exc).__name__}: {exc}",
                    }
                finally:
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)
            st.session_state["module3_image_result"] = {
                "image_name": uploaded_image.name if uploaded_image is not None else None,
                **image_result,
            }

            if predict_clinical_grade is None:
                clinical_result = {
                    "status": "dependency_unavailable",
                    "predicted_grade": None,
                    "grade_label": None,
                    "message": f"The clinical adapter could not be imported: {CLINICAL_ADAPTER_IMPORT_ERROR}",
                }
            else:
                clinical_features = {
                    "Age at Diagnosis": age_at_diagnosis,
                    "Tumor Size": tumor_size,
                    "ER Status": er_status,
                    "PR Status": pr_status,
                    "HER2 Status": her2_status,
                }
                try:
                    clinical_result = predict_clinical_grade(clinical_features)
                except Exception as exc:
                    clinical_result = {
                        "status": "prediction_error",
                        "predicted_grade": None,
                        "grade_label": None,
                        "message": f"Clinical analysis could not run: {type(exc).__name__}: {exc}",
                    }
            st.session_state["module3_clinical_result"] = clinical_result

        st.caption("One action runs both adapters separately; the experimental score below is not a diagnosis or clinical probability.")

with st.container(border=True):
    st.subheader("Research Results")
    st.caption("Separate outputs from the ultrasound image and clinical grade models.")
    image_result_panel, clinical_result_panel = st.columns(2, gap="large")

    with image_result_panel:
        st.markdown("**Ultrasound image output**")
        image_record = st.session_state["module3_image_result"]
        if image_record is None:
            st.caption("Run both analyses to display the image result here.")
        else:
            if image_record.get("image_name"):
                st.caption(f"Image - {image_record['image_name']}")
            image_status = image_record.get("status", "unknown")
            st.write(f"**Status:** {image_status.replace('_', ' ').title()}")
            if image_status == "success":
                st.success(f"Image model output: {image_record.get('prediction')}")
            elif image_status == "uncertain":
                st.warning("Image model output: Uncertain")
            elif image_status == "rejected":
                st.warning("Image rejected by the ultrasound validator.")
            elif image_status == "invalid_image":
                st.warning("The uploaded file is not a readable image.")
            else:
                st.error(image_record.get("message", "Image analysis is unavailable."))
            confidence = image_record.get("confidence")
            validator_probability = image_record.get("validator_probability")
            if confidence is not None:
                st.write(f"**Confidence:** {confidence:.1%}")
            if validator_probability is not None:
                st.write(f"**Validator probability:** {validator_probability:.1%}")
            probabilities = image_record.get("class_probabilities", {})
            if any(value is not None for value in probabilities.values()):
                st.markdown("**Image class probabilities**")
                for class_name in ("Normal", "Benign", "Malignant"):
                    value = probabilities.get(class_name)
                    if value is not None:
                        st.write(f"{class_name}: {value:.1%}")
            st.caption(image_record.get("message", ""))

    with clinical_result_panel:
        st.markdown("**Clinical grade output**")
        clinical_result = st.session_state["module3_clinical_result"]
        if clinical_result is None:
            st.caption("Run both analyses to display the clinical result here.")
        else:
            clinical_status = clinical_result.get("status", "unknown")
            st.write(f"**Status:** {clinical_status.replace('_', ' ').title()}")
            if clinical_status == "success":
                st.success(f"Predicted histologic grade: {clinical_result.get('grade_label')}")
            else:
                st.error(clinical_result.get("message", "Clinical prediction is unavailable."))
            st.caption(clinical_result.get("message", ""))

with st.container(border=True):
    st.subheader("Cancer / non-cancer fusion score")
    st.caption("Experimental late-fusion research output. It is not a clinical probability or diagnosis.")
    fusion_result = experimental_fusion_result(image_record, clinical_result)

    if fusion_result is None:
        st.info(
            "A score is shown only when the ultrasound image has usable class probabilities "
            "and the clinical model successfully predicts a histologic grade."
        )
    else:
        with st.container(horizontal=True):
            st.metric("Fusion prediction", fusion_result["prediction"], border=True)
            st.metric("Experimental fusion score", f"{fusion_result['score']:.1%}", border=True)
            st.metric("Predicted histologic grade", f"Grade {fusion_result['grade']}", border=True)

        if fusion_result["image_uncertain"]:
            st.warning(
                "The image classifier marked its output uncertain. Treat the experimental fusion score with extra caution."
            )

        st.warning(
            "Experimental late-fusion score: 80% × image-model malignant-class score + "
            "20% × ordinal histologic grade index (Grade 1 = 0, Grade 2 = 0.5, Grade 3 = 1). "
            "The grade index is not a clinical risk score, and the 50% category threshold is a display heuristic. "
            "The models were trained separately and have no patient-linked fusion validation; this score is "
            "uncalibrated and must not be used to diagnose or rule out cancer."
        )

        st.markdown("**Image-model malignant-class score**")
        st.progress(
            fusion_result["image_malignant_score"],
            text=f"Malignant class: {fusion_result['image_malignant_score']:.1%}",
        )
        st.markdown("**Ordinal clinical grade index**")
        st.progress(
            fusion_result["clinical_grade_index"],
            text=f"Grade {fusion_result['grade']} index: {fusion_result['clinical_grade_index']:.1%}",
        )

        with st.container(border=True):
            st.markdown("**Cancer-like / non-cancer-like fusion score**")
            st.progress(
                fusion_result["score"],
                text=f"Cancer-like: {fusion_result['score']:.1%}",
            )
            st.progress(
                fusion_result["non_cancer_score"],
                text=f"Non-cancer-like: {fusion_result['non_cancer_score']:.1%}",
            )
        st.caption(
            "Formula: 0.8 × malignant-class score + 0.2 × ordinal grade index. "
            "The two models still describe separate evidence streams."
        )

st.caption(
    "This is a research prototype, not a medical diagnostic tool. BUSI images and Module 2 records are not patient-matched. "
    "The experimental score is uncalibrated, has no patient-linked validation, and must not be used to diagnose or rule out cancer."
)
