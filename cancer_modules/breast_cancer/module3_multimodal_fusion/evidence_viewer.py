"""Legacy Streamlit entry point. Use the integrated Next.js Module 3 workspace."""

import streamlit as st

st.set_page_config(page_title="Breast Cancer Combined Analysis", page_icon="🧬", layout="wide")
st.title("Breast Cancer Combined Analysis")
st.warning(
    "The previous BrEaST fusion experiment is not compatible with Module 2's five clinical inputs. "
    "The active Module 3 workflow runs Module 1 and Module 2 independently and does not calculate fusion."
)
st.markdown(
    "Use the main application at `/breast-evidence-review` to submit an ultrasound image and the exact five Module 2 clinical inputs. "
    "Image output and histologic-grade output are displayed separately. A combined cancer result is unavailable "
    "until compatible patient-linked training data are verified. Grade is not cancer probability. This is research output, not a diagnosis."
)
