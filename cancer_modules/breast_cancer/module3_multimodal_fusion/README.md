# Breast Cancer Combined Analysis

## Objective and architecture

- evidence_viewer.py - a Streamlit page that runs both analyses separately, displays each result, and shows an experimental score when both outputs are usable.\r\n
The components are:

- `image_adapter.py` — validates and classifies an ultrasound image using Module 1 model files.
- `clinical_adapter.py` — predicts a histologic grade using the saved Module 2 sklearn pipeline.
- evidence_viewer.py - a Streamlit page that runs both analyses separately, displays each result, and shows an experimental score when both outputs are usable.\r\n
There is no learned multimodal model. When both model outputs are available, the interface displays an experimental late-fusion research score: 80% of the image model's malignant-class score plus 20% of an ordinal histologic grade index (Grade 1 = 0, Grade 2 = 0.5, Grade 3 = 1). This fixed heuristic is uncalibrated; it is not a cancer probability, risk estimate, or diagnosis.

## Independent evidence streams

The BUSI dataset and Module 2 clinical records are not patient-matched. Module 3 does not pair training records, and no patient-level multimodal training or joint validation has been performed. The displayed score is a fixed calculation over two separate outputs, not a learned fusion model. An image classification and a clinical grade prediction describe different model outputs and should be interpreted separately.

## Image adapter

`image_adapter.py` loads the existing model files from Module 1 using paths relative to the adapter:

- `Breast_cancer/module1_image_analysis/busi_ultrasound_validator.keras`
- `Breast_cancer/module1_image_analysis/busi_mobilenetv2.keras`

The public function is:

```python
predict_ultrasound(image_path: str | Path) -> dict[str, Any]
```

The adapter follows the Module 1 preprocessing and thresholds:

1. Open the input image, convert it to RGB, resize to 128×128, and apply MobileNetV2 `preprocess_input` for validation.
2. Reject the image if the validator probability is below **0.50**.
3. If it passes validation, resize to 224×224, apply MobileNetV2 `preprocess_input`, and classify in the order **Normal, Benign, Malignant**.
4. Mark the result **Uncertain** when the highest class probability is below **0.60**.

The returned dictionary contains `status`, `prediction`, `confidence`, `class_probabilities`, `validator_probability`, and `message`. Model files that are missing, invalid images, prediction errors, and TensorFlow import failures are returned with explanatory statuses. The adapter does not attempt to install TensorFlow or change system security settings.

## Clinical grade adapter

`clinical_adapter.py` loads `Breast_cancer/module2_clinical_analysis/clinical_grade_model.pkl` with joblib, using a path relative to the adapter file.

The public function is:

```python
predict_clinical_grade(features: Mapping[str, Any]) -> dict[str, Any]
```

The input mapping must contain exactly these five feature names:

- `Age at Diagnosis` — numeric, 0–120
- `Tumor Size` — numeric, zero or greater
- `ER Status` — `Positive` or `Negative`
- `PR Status` — `Positive` or `Negative`
- `HER2 Status` — `Positive` or `Negative`

Missing values are passed to the saved pipeline for its fitted preprocessing steps; the adapter does not manually scale, impute, or encode features. The result dictionary contains `status`, `predicted_grade`, `grade_label`, and `message`. A successful output is **Grade 1**, **Grade 2**, or **Grade 3**. It is not a cancer diagnosis or probability.

## Evidence Viewer

- evidence_viewer.py - a Streamlit page that runs both analyses separately, displays each result, and shows an experimental score when both outputs are usable.\r\n
- **Ultrasound Image Analysis:** accepts PNG, JPG, or JPEG; previews the upload; saves it temporarily for the image adapter; and displays status, prediction, confidence, validator probability, and class probabilities where available.
- **Clinical Grade Analysis:** collects the five model features and displays the prediction status and grade.
- **Experimental late-fusion score:** when both outputs are usable, computes `0.8 × malignant-class score + 0.2 × ordinal clinical grade index`. The grade index maps Grade 1 to 0, Grade 2 to 0.5, and Grade 3 to 1. A score at or above 0.5 is labeled **Cancer-like**; a lower score is labeled **Non-cancer-like**. These are heuristic display categories, not diagnoses.

Image and clinical results are stored in separate Streamlit session-state variables. Running one analysis does not clear the other result. The image upload is written to a temporary file for inference and removed afterward.

From the **outer repository root** in PowerShell, enter the project folder and launch the interface:

```powershell
cd Multimodal-Cancer-AI
- evidence_viewer.py - a Streamlit page that runs both analyses separately, displays each result, and shows an experimental score when both outputs are usable.\r\n```

The clinical adapter requires pandas, NumPy, joblib, and a compatible scikit-learn installation (the shared requirements pin scikit-learn to 1.6.1). Image inference requires TensorFlow, NumPy, and Pillow. Both existing requirements files (`requirements.txt` and `Multimodal-Cancer-AI/requirements.txt`) include `tensorflow==2.21.0`.

## Windows setup on another laptop

1. Install Python 3.12.
2. Open PowerShell in the outer repository root.
3. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

4. Install the dependencies from the outer root:

```powershell
python -m pip install -r requirements.txt
```

5. Follow the launch instructions above to enter `Multimodal-Cancer-AI` and start the Evidence Viewer.

Successful package installation does not guarantee that TensorFlow image inference will work on every Windows laptop. Test actual loading of both image models and image prediction on the target laptop. Windows Application Control blocks TensorFlow DLL loading in the current local environment; the recorded image predictions were tested in Google Colab, not on local Windows.

## Recorded implementation checks

The following checks were reported for this implementation:

| Check | Reported result |
|---|---|
| Clinical adapter local test | Grade 3; status `success` |
| Image adapter in Google Colab — `benign (105).png` | Benign; confidence 99.05% |
| Image adapter in Google Colab — `normal (7).png` | Normal; confidence 95.03% |
| Evidence Viewer | Opened successfully |
| Clinical panel prediction in Streamlit | Grade 3; status `success` |
| Independent result retention | Clinical result remained visible after image prediction failed |

The image tests were run in Google Colab. **Local Windows image inference is not verified:** Windows Application Control blocks TensorFlow DLL loading in the local environment. The successful Colab results do not establish that TensorFlow image inference works on Windows.

## Clean Environment Portability Test (Windows)

A fresh temporary Python 3.12 virtual environment was created and tested on the same Windows laptop. This test does not represent testing on another physical laptop.

- Dependencies installed with `python -m pip install -r .\requirements.txt`.
- `python -m pip check` reported: `No broken requirements found`.
- TensorFlow imported successfully; version: `2.21.0`.
- Module 3 image inference succeeded for `benign (6).png`:
  - Prediction: **Benign**
  - Confidence: **94.8%**
  - Validator probability: **100.0%**
  - Class probabilities: Normal **0.3%**, Benign **94.8%**, Malignant **4.9%**
- Clinical inference succeeded: predicted histologic grade **Grade 3**.

Only the listed benign image was tested for image inference in this clean environment; this test does not establish clean-environment results for all three image classes.
## Limitations and intended use

- BUSI images and clinical records are not patient-matched; there is no patient-level multimodal training or joint fusion validation.
- The weighted late-fusion score is an uncalibrated research heuristic, not a cancer probability, personal risk percentage, or diagnostic conclusion. Its 50% threshold is only a display rule.
- The clinical model predicts histologic grade only; the ordinal grade index used in the heuristic is not a clinical risk score and does not classify normal versus cancer.
- This is an educational research prototype, not a medical diagnostic tool. It has not undergone external clinical validation. Independent external validation is required before any clinical use could be considered.
