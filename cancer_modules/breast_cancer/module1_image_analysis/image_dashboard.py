"""Standalone Streamlit dashboard for the BUSI ultrasound image predictor."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError


st.set_page_config(
    page_title="Breast Ultrasound Image Analysis",
    page_icon=":material/monitor_heart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MODULE1_DIR = Path(__file__).resolve().parent
MODULE3_DIR = MODULE1_DIR.parent / "module3_multimodal_fusion"
if str(MODULE3_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE3_DIR))

try:
    from image_adapter import predict_ultrasound

    IMAGE_ADAPTER_ERROR = None
except Exception as exc:  # Keep the interface available when TF cannot import.
    predict_ultrasound = None
    IMAGE_ADAPTER_ERROR = f"{type(exc).__name__}: {exc}"


st.markdown(
    """
    <style>
    @font-face {
        font-family:"Plus Jakarta Sans"; font-style:normal; font-weight:200 800;
        font-display:swap;
        src:url("https://wecure-five.vercel.app/_next/static/immutable/media/d8aeca813a9ab546-s.p.08ssgmy_tb90r.woff2") format("woff2");
    }
    :root {
        color-scheme:dark; --background:#0b1220; --foreground:#e6ebf2;
        --card:#142133; --elevated:#1b2a3e; --border:#2a394e;
        --muted:#a1b0c5; --teal:#22c5b7;
        font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;
    }
    html,body,[data-testid="stAppViewContainer"],.stApp,[data-testid="stMain"] {
        min-height:100vh !important; width:100%; background:var(--background) !important;
        color:var(--foreground) !important; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;
    }
    html,body { overflow-x:hidden; }
    [data-testid="stSidebar"],[data-testid="collapsedControl"] { display:none !important; width:0 !important; }
    [data-testid="stHeader"] { height:0; background:transparent; }
    [data-testid="stMain"] { margin-left:0 !important; }
    .block-container { width:100% !important; max-width:none !important; min-height:100vh !important; padding:18px 20px 14px !important; box-sizing:border-box; }
    [data-testid="stHorizontalBlock"] { width:100%; align-items:stretch; gap:18px; }
    [data-testid="stColumn"] { min-width:0; }
    h1,h2,h3,p,label,[data-testid="stWidgetLabel"] { color:var(--foreground) !important; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif; }
    h1 { margin:0 0 5px !important; font-size:clamp(28px,2.5vw,34px) !important; line-height:1.25; font-weight:750 !important; letter-spacing:-.035em; }
    h2 { margin:0 !important; font-size:20px !important; line-height:1.4; font-weight:700 !important; letter-spacing:-.02em; }
    h3 { font-size:17px !important; font-weight:650 !important; }
    p,label,[data-testid="stWidgetLabel"] { font-size:15px; line-height:1.5; }
    [data-testid="stCaptionContainer"] { color:var(--muted) !important; font-size:13px !important; line-height:1.5; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        display:flow-root !important; position:relative !important; width:100%; min-width:0;
        height:auto !important; min-height:0 !important; overflow:visible !important;
        margin-bottom:12px !important; box-sizing:border-box; background:var(--card) !important;
        border:1px solid var(--border) !important; border-radius:18px !important; box-shadow:none !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        height:auto !important; min-height:0 !important; overflow:visible !important;
        box-sizing:border-box !important; padding:18px !important;
    }
    [data-testid="stVerticalBlock"] { min-height:0; overflow:visible !important; }
    .st-key-module1_upload_card,.st-key-module1_controls_card,
    .st-key-module1_upload_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-module1_controls_card [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:clamp(420px,58vh,540px) !important; height:100% !important;
        align-self:stretch !important; box-sizing:border-box !important;
    }
    .st-key-module1_upload_preview_frame,
    .st-key-module1_upload_preview_frame [data-testid="stVerticalBlockBorderWrapper"] {
        min-height:360px !important; box-sizing:border-box !important;
    }
    .st-key-module1_upload_preview_frame [data-testid="stVerticalBlock"],
    .st-key-module1_upload_preview_frame[data-testid="stVerticalBlock"] {
        min-height:330px !important; display:flex !important; flex-direction:column !important;
        align-items:center !important; justify-content:center !important;
    }
    .st-key-module1_upload_preview_frame [data-testid="stImage"] {
        display:flex !important; width:100% !important; max-height:none !important;
        justify-content:center !important; overflow:visible !important; margin:auto !important;
    }
    .st-key-module1_upload_preview_frame [data-testid="stImage"] img {
        width:auto !important; height:auto !important; max-width:520px !important;
        max-height:320px !important; object-fit:contain !important; margin:auto !important;
    }
    .st-key-module1_controls_card,
    .st-key-module1_controls_card[data-testid="stVerticalBlock"],
    .st-key-module1_controls_card > [data-testid="stVerticalBlock"] {
        display:flex !important; flex-direction:column !important;
        justify-content:space-between !important; gap:16px !important;
    }
    .st-key-module1_controls_card > [data-testid="stVerticalBlock"] { flex:1 1 auto; }
    .wc-eyebrow { margin-bottom:5px; color:var(--teal); font-size:12px; font-weight:750; letter-spacing:.08em; text-transform:uppercase; }
    .wc-intro { max-width:920px; margin:0 0 18px; color:var(--muted); font-size:15px; line-height:1.55; }
    .wc-card-heading { display:flex; align-items:flex-start; gap:12px; margin-bottom:18px; }
    .wc-card-icon { display:flex; width:40px; height:40px; flex:0 0 40px; align-items:center; justify-content:center; border-radius:13px; background:#123b42; color:#45d4c5; }
    .wc-card-icon svg { width:20px; height:20px; stroke:currentColor; fill:none; stroke-width:1.7; stroke-linecap:round; stroke-linejoin:round; }
    .wc-card-subtitle { margin-top:3px; color:var(--muted); font-size:13px; line-height:1.5; }
    .wc-selection { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:13px 14px; border:1px solid var(--border); border-radius:12px; background:var(--elevated); }
    .wc-selection-label { color:var(--muted); font-size:12px; }
    .wc-selection-value { margin-top:3px; color:var(--foreground); font-size:15px; font-weight:700; }
    .wc-pill { padding:5px 9px; border:1px solid #23635f; border-radius:999px; background:#153b43; color:#7ce7dc; font-size:11px; font-weight:700; white-space:nowrap; }
    .wc-field-label { margin:16px 0 7px; color:var(--muted); font-size:12px; font-weight:750; letter-spacing:.06em; text-transform:uppercase; }
    .wc-upload-state { padding:11px 12px; border:1px solid var(--border); border-radius:10px; background:var(--elevated); color:var(--muted); font-size:13px; overflow-wrap:anywhere; }
    .wc-model-state { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:11px 12px; border-radius:10px; background:var(--elevated); color:var(--muted); font-size:12px; }
    .wc-model-state strong { color:var(--foreground); font-size:12px; font-weight:700; }
    [data-testid="stFileUploader"] { margin-top:5px; }
    [data-testid="stFileUploaderDropzone"] {
        width:100% !important; min-height:140px !important;
        display:flex !important; flex-direction:column; align-items:center; justify-content:center;
        gap:12px; box-sizing:border-box; padding:20px !important;
        border:2px dashed #3b5068 !important; border-radius:17px !important;
        background:#1a293d !important; color:var(--foreground) !important;
        transition:border-color .18s ease,background .18s ease;
    }
    [data-testid="stFileUploaderDropzone"]:hover { border-color:var(--teal) !important; background:#1a3042 !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { color:var(--muted) !important; font-size:0 !important; text-align:center; }
    [data-testid="stFileUploaderDropzoneInstructions"]::after {
        display:block; content:"Drag and drop your breast ultrasound image here";
        color:#d7e1ef; font-size:15px; font-weight:650; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;
    }
    [data-testid="stFileUploaderDropzone"] svg { width:32px !important; height:32px !important; color:var(--teal) !important; fill:var(--teal) !important; }
    [data-testid="stFileUploaderDropzone"] button {
        position:relative; top:12px; min-height:40px !important; padding:0 18px !important;
        border:1px solid #3b5068 !important; border-radius:11px !important;
        background:#23364b !important; color:var(--foreground) !important; font-size:14px !important; font-weight:700 !important;
    }
    [data-testid="stFileUploaderDropzone"] button:hover { border-color:var(--teal) !important; background:#29445a !important; color:#fff !important; }
    [data-testid="stFileUploader"] small { color:var(--muted) !important; font-size:12px !important; }
    [data-testid="stMetric"] { padding:13px 14px; border:1px solid var(--border); border-top:2px solid var(--teal); border-radius:12px; background:var(--elevated); }
    [data-testid="stMetricLabel"] { color:var(--muted) !important; font-size:12px !important; }
    [data-testid="stMetricValue"] { margin-top:6px; color:var(--foreground) !important; font-size:22px !important; font-weight:750 !important; }
    [data-testid="stSuccess"],[data-testid="stWarning"],[data-testid="stError"] { border-radius:11px !important; }
    [data-testid="stSuccess"] { background:#173a3b !important; color:#c8f1e8 !important; border:1px solid #28675b !important; }
    [data-testid="stWarning"] { background:#3a3020 !important; color:#f8d890 !important; border:1px solid #715725 !important; }
    [data-testid="stError"] { background:#3b222a !important; color:#ffc1c9 !important; border:1px solid #74404b !important; }
    [data-testid="stSuccess"] p,[data-testid="stWarning"] p,[data-testid="stError"] p { color:inherit !important; font-size:16px !important; }
    [data-testid="stAlert"],[role="alert"] {
        background:#173347 !important; background-color:#173347 !important;
        color:#eef5f8 !important; border:1px solid #31566b !important;
        border-radius:11px !important;
    }
    [data-testid="stAlert"] p,[data-testid="stAlert"] span,
    [data-testid="stAlert"] div,[role="alert"] p,[role="alert"] span,
    [role="alert"] div {
        color:#eef5f8 !important; background:transparent !important;
    }
    .wc-empty { display:flex; min-height:120px; flex-direction:column; align-items:center; justify-content:center; padding:20px; border:1px dashed var(--border); border-radius:13px; background:var(--elevated); text-align:center; }
    .wc-empty-title { color:var(--foreground); font-size:15px; font-weight:700; }
    .wc-empty-copy { margin-top:5px; color:var(--muted); font-size:13px; }
    .wc-results-bottom-spacer { display:block; width:100%; height:20px; min-height:20px; }
    .wc-disclaimer { display:flex; align-items:flex-start; gap:11px; margin-top:18px; padding:14px 16px; border:1px solid #51452a; border-radius:13px; background:#211f20; color:#ead7a3; font-size:12px; line-height:1.6; }
    .wc-disclaimer strong { display:block; margin-bottom:3px; color:#f3d47b; font-size:13px; font-weight:750; }
    .wc-disclaimer svg { width:19px; height:19px; flex:0 0 19px; margin-top:1px; stroke:#eab43c; fill:none; stroke-width:1.8; }
    .wc-footer { padding:14px 0 2px; color:var(--muted); text-align:center; font-size:11px; }
    div.stButton > button,div[data-testid="stFormSubmitButton"] > button {
        min-height:44px; border:0; border-radius:11px; background:var(--teal) !important;
        color:#06212a !important; font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;
        font-size:14px; font-weight:750; box-shadow:0 5px 15px rgba(34,197,183,.14);
    }
    div.stButton > button:hover,div[data-testid="stFormSubmitButton"] > button:hover { background:#48d7ca !important; color:#06212a !important; }
    div.stButton > button:disabled { background:#2b5a60 !important; color:#9eb9bb !important; box-shadow:none; }
    [data-testid="stProgressBar"] > div { background:#26364b !important; border-radius:999px; }
    [data-testid="stProgressBar"] > div > div { background:var(--teal) !important; border-radius:999px; }
    [data-testid="stProgress"] label { color:var(--foreground) !important; font-size:13px !important; }
    @media (max-width:640px) {
        .block-container { padding:12px 10px !important; }
        h1 { font-size:25px !important; }
        [data-testid="stVerticalBlockBorderWrapper"] > div { padding:14px !important; }
        .st-key-module1_upload_card,.st-key-module1_controls_card,
        .st-key-module1_upload_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-module1_controls_card [data-testid="stVerticalBlockBorderWrapper"] { min-height:0 !important; height:auto !important; }
        .st-key-module1_upload_preview_frame,
        .st-key-module1_upload_preview_frame [data-testid="stVerticalBlockBorderWrapper"] { min-height:290px !important; }
        .st-key-module1_upload_preview_frame [data-testid="stVerticalBlock"],
        .st-key-module1_upload_preview_frame[data-testid="stVerticalBlock"] { min-height:260px !important; }
        .st-key-module1_upload_preview_frame [data-testid="stImage"] img { max-width:360px !important; max-height:250px !important; }
        .st-key-module1_controls_card,.st-key-module1_controls_card[data-testid="stVerticalBlock"],
        .st-key-module1_controls_card > [data-testid="stVerticalBlock"] { justify-content:flex-start !important; gap:14px !important; }
        [data-testid="stFileUploaderDropzone"] { min-height:140px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="wc-eyebrow">Image Analysis · Breast Cancer</div>', unsafe_allow_html=True)
st.title("Breast Ultrasound Image Analysis")
st.markdown(
    '<div class="wc-intro">Upload a breast ultrasound image to run it through the connected BUSI research models. Results include validator status, class prediction and probabilities.</div>',
    unsafe_allow_html=True,
)


def section_heading(icon_svg: str, title: str, subtitle: str) -> None:
    """Render a dashboard card heading with a small turquoise icon."""
    st.markdown(
        f'<div class="wc-card-heading"><div class="wc-card-icon">{icon_svg}</div>'
        f'<div><h2>{title}</h2><div class="wc-card-subtitle">{subtitle}</div></div></div>',
        unsafe_allow_html=True,
    )


if "module1_image_result" not in st.session_state:
    st.session_state["module1_image_result"] = None

upload_panel, controls_panel = st.columns([3, 2], gap="large")
uploaded_image = None
image_bytes = None

with upload_panel:
    with st.container(border=True, key="module1_upload_card"):
        section_heading(
            '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>',
            "Image Upload",
            "Breast ultrasound image · JPG, JPEG or PNG · Max 10 MB",
        )
        uploaded_image = st.file_uploader(
            "Breast ultrasound image upload",
            type=["png", "jpg", "jpeg"],
            key="module1_ultrasound_upload",
            label_visibility="collapsed",
        )
        if uploaded_image is not None:
            image_bytes = uploaded_image.getvalue()
            try:
                with Image.open(uploaded_image) as source_image:
                    preview = source_image.convert("RGB")
                with st.container(border=True, key="module1_upload_preview_frame"):
                    st.image(
                        preview,
                        width=520,
                    )
                    st.caption(f"Uploaded ultrasound image: {uploaded_image.name}")
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                st.warning(f"Image preview unavailable: {exc}")


with controls_panel:
    with st.container(border=True, key="module1_controls_card"):
        section_heading(
            '<svg viewBox="0 0 24 24"><path d="M12 8v4l3 2"/><circle cx="12" cy="12" r="9"/><path d="M12 3v2M21 12h-2"/></svg>',
            "Analysis Controls",
            "Configure and run the analysis.",
        )
        st.markdown(
            '<div class="wc-selection"><div><div class="wc-selection-label">Selected module</div>'
            '<div class="wc-selection-value">Breast Cancer</div></div><span class="wc-pill">Prototype</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="wc-field-label">Uploaded image</div>', unsafe_allow_html=True)
        if uploaded_image is None:
            st.markdown('<div class="wc-upload-state">No image selected yet.</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="wc-upload-state">Selected file · {uploaded_image.name}<br>Size · {uploaded_image.size / 1024:.1f} KB</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="wc-model-state"><strong>Model pipeline</strong><span>BUSI validator + MobileNetV2</span></div>',
            unsafe_allow_html=True,
        )
        run_analysis = st.button(
            "Analyze Ultrasound",
            type="primary",
            disabled=uploaded_image is None,
            width="stretch",
            key="module1_run_analysis",
        )

        if run_analysis and uploaded_image is not None and image_bytes is not None:
            if predict_ultrasound is None:
                result = {
                    "status":"dependency_unavailable", "prediction":None, "confidence":None,
                    "validator_probability":None,
                    "class_probabilities":{name:None for name in ("Normal", "Benign", "Malignant")},
                    "message":f"Image predictor could not be imported: {IMAGE_ADAPTER_ERROR}",
                }
            else:
                temporary_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=Path(uploaded_image.name).suffix.lower(), delete=False) as temporary_file:
                        temporary_file.write(image_bytes)
                        temporary_path = Path(temporary_file.name)
                    result = predict_ultrasound(temporary_path)
                except Exception as exc:
                    result = {
                        "status":"prediction_error", "prediction":None, "confidence":None,
                        "validator_probability":None,
                        "class_probabilities":{name:None for name in ("Normal", "Benign", "Malignant")},
                        "message":f"Image analysis failed: {type(exc).__name__}: {exc}",
                    }
                finally:
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)
            st.session_state["module1_image_result"] = {"image_name":uploaded_image.name, **result}


with st.container(border=True, key="module1_results_card"):
    section_heading(
        '<svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-5 5"/></svg>',
        "Research Results",
        "Model output, explanation and metadata.",
    )
    result = st.session_state["module1_image_result"]
    if result is None:
        st.markdown(
            '<div class="wc-empty"><div class="wc-empty-title">No analysis yet</div>'
            '<div class="wc-empty-copy">Upload an image and select Analyze Ultrasound to view research output here.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"Image · {result['image_name']}")
        status = result.get("status", "unknown")
        if status == "success":
            st.success(f"Prediction · {result.get('prediction')}")
        elif status == "uncertain":
            st.warning("Prediction · Uncertain")
        elif status == "rejected":
            st.warning("Image rejected by the validator")
        elif status == "invalid_image":
            st.warning("The uploaded file is not a readable image")
        else:
            st.error(result.get("message", "Image analysis is unavailable."))

        confidence = result.get("confidence")
        validator_probability = result.get("validator_probability")
        metric_a, metric_b = st.columns(2)
        metric_a.metric("Class confidence", f"{confidence:.1%}" if confidence is not None else "—")
        metric_b.metric("Validator probability", f"{validator_probability:.1%}" if validator_probability is not None else "—")

        probabilities = result.get("class_probabilities", {})
        if any(value is not None for value in probabilities.values()):
            st.markdown("**Class probabilities**")
            probability_columns = st.columns(3)
            for column, class_name in zip(probability_columns, ("Normal", "Benign", "Malignant")):
                value = probabilities.get(class_name)
                with column:
                    st.caption(class_name)
                    if value is not None:
                        st.progress(float(value), text=f"{float(value):.1%}")
        st.caption(result.get("message", ""))

    st.markdown('<div class="wc-results-bottom-spacer"></div>', unsafe_allow_html=True)


st.markdown(
    '<div class="wc-disclaimer"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></svg>'
    '<div><strong>Research Disclaimer</strong>This platform is an academic AI research prototype. Its outputs are experimental and are not intended for clinical diagnosis or treatment decisions. All medical decisions must be made by qualified healthcare professionals. A validator score below 0.50 rejects an image; class confidence below 0.60 is shown as Uncertain.</div></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="wc-footer">WeCure · Academic AI research prototype · Not for clinical diagnosis or treatment decisions.</div>',
    unsafe_allow_html=True,
)
