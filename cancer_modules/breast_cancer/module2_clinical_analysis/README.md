# Breast Cancer Module 2: Clinical Data Analysis

## Overview and objectives

Module 2 explores clinical breast cancer data and develops an educational, three-class model for **histologic grade prediction among records in the dataset**. Its objectives are to:

- inspect clinical variables, distributions, missingness, and data quality;
- select features while avoiding outcome-derived information and identifiers;
- compare clinical-feature modeling approaches for Grades 1, 2, and 3; and
- provide a separate preliminary symptom-assessment interface.

This module does **not** diagnose breast cancer. The dataset contains breast cancer cases; it is not a normal-versus-cancer screening dataset.

## Dataset

`Clinical_dataset.xlsx.txt` contains **2,509 rows and 39 columns**. Despite its filename, the file is tab-separated text and should be loaded with a tab delimiter. It includes patient/sample identifiers, demographic and tumor characteristics, receptor statuses, treatment information, survival and relapse fields, histologic grade, and tumor stage.

The target, `Neoplasm Histologic Grade`, has three classes:

| Grade | Rows with a recorded grade |
|---|---:|
| Grade 1 | 214 |
| Grade 2 | 976 |
| Grade 3 | 1,198 |
| Missing grade | 121 |

Rows with a missing target are excluded from supervised grade modeling. The grade classes are imbalanced, with Grade 1 the least represented.

## Exploratory data analysis and data quality

`Clinical_Data_Analysis.ipynb` contains dataset inspection, missing-value summaries, class distributions, receptor-status visualizations, numerical-feature histograms and boxplots, a numerical correlation heatmap, and basic data-quality checks.

Verified data-quality checks found:

- **0** completely duplicated rows;
- **2,509** unique non-missing Patient IDs and **2,509** unique non-missing Sample IDs, with no repeated IDs;
- observed histologic grades of 1, 2, and 3, with no unexpected grade values;
- observed tumor stages 0 through 4, with no unexpected stage values; and
- no out-of-range values for the reviewed age, tumor size, positive lymph-node count, mutation count, or Nottingham index checks.

Missingness remains material in some fields. `Tumor Stage` has 721 missing values (28.7%); `Cellularity` has 592 (23.6%); PR Status, HER2 Status, Pam50 + Claudin-low subtype, Inferred Menopausal State, and several treatment/outcome fields have 529 missing values each (21.1%). Missingness should be reviewed by feature and cohort before modeling.

The exploratory correlations also show redundancy: Mutation Count and TMB (nonsynonymous) are almost perfectly correlated (r = 0.999), while Overall Survival (Months) and Relapse Free Status (Months) are strongly correlated (r = 0.902). The Nottingham prognostic index is strongly correlated with grade (r = 0.700) and is excluded from the prediction features because it contains grade-related information.

## Feature selection and leakage precautions

The initial feature set for the grade-prediction workflow is:

- Age at Diagnosis
- Tumor Size
- ER Status
- PR Status
- HER2 Status

Preprocessing is designed to use sklearn pipelines: median imputation and scaling for numeric features, and most-frequent imputation and one-hot encoding for categorical features. Pipeline preprocessing is fitted on training data only.

The model excludes Nottingham prognostic index; Patient ID, Sample ID, and Study ID; Overall Survival fields; Relapse Free Status fields; Patient's Vital Status; Number of Samples Per Patient; and other outcome-derived fields. These can directly encode the target, outcome, follow-up, or record identity. Tumor size and receptor results may be measured during the same diagnostic workup as grade, so their availability must be assessed for the intended prediction time.

## Histologic grade prediction

`Clinical_Grade_Prediction.ipynb` defines a stratified train/test split and preprocessing pipelines for a three-class target: **Grade 1, Grade 2, and Grade 3**. The reported experiment compared Logistic Regression and Random Forest, explored class-weighting and SMOTE approaches for imbalance, and used cross-validation for hyperparameter tuning. **Random Forest was selected** as the final model.

### Final reported evaluation

| Metric | Result |
|---|---:|
| Test accuracy | 0.5126 |
| Test macro F1 | 0.4386 |
| Cross-validation macro F1 | 0.4899 |

| Histologic grade | Precision | Recall | F1 |
|---|---:|---:|---:|
| Grade 1 | 0.212 | 0.256 | 0.232 |
| Grade 2 | 0.455 | 0.523 | 0.487 |
| Grade 3 | 0.653 | 0.550 | 0.597 |

The reported feature importance values for the selected model are:

| Feature | Importance |
|---|---:|
| Age at Diagnosis | 0.4287 |
| Tumor Size | 0.3285 |
| ER Status — Negative | 0.0847 |
| ER Status — Positive | 0.0755 |
| PR Status — Negative | 0.0269 |
| PR Status — Positive | 0.0248 |
| HER2 Status — Positive | 0.0170 |
| HER2 Status — Negative | 0.0139 |

### Reproducibility note

The evaluation metrics and feature importances above are the reported project results supplied for this report. The existing notebooks currently have no saved execution outputs. The current `Clinical_Grade_Prediction.ipynb` contains baseline Logistic Regression and Random Forest code plus optional XGBoost detection; it does not currently reproduce the reported class-weight, SMOTE, or cross-validation hyperparameter experiments. Those experiment details and outputs should be added to the notebook if exact reruns are required.

The serialized model artifact is `clinical_grade_model.pkl`.

## Breast Health Assessment

`breast_health_assessment.py` is a separate Streamlit symptom-assessment component. It collects age, sex, responses about new breast/chest changes, and family history; asks symptom duration when a symptom is reported; and displays a summary with an Assessment ID and a recommendation to seek appropriate medical evaluation. It is a preliminary symptom summary, not a cancer diagnosis, and it does not calculate cancer probability or classify a person as cancer-positive or cancer-negative.

## Limitations and intended use

- **Moderate performance:** test accuracy is 0.5126 and test macro F1 is 0.4386. Grade 1 has particularly low precision and recall in the reported evaluation.
- **Class imbalance:** Grade 1 has substantially fewer records than Grades 2 and 3. Class weighting and SMOTE were explored, but imbalance remains a limitation.
- **Prediction-time availability:** tumor size and receptor statuses may not be available until the pathology or diagnostic workup that also determines grade. A valid prospective use case must define when the prediction is made and which values are available then.
- **Test-set reuse:** the test set was reused during experimentation, which can make the final reported performance optimistic. A future evaluation should reserve a truly untouched test set.
- **No clinical validation:** results are based on this dataset and are not clinically validated. The model is an educational research prototype, not a diagnostic tool or substitute for professional care.
- **No matched multimodal cohort:** Module 1 BUSI ultrasound images and Module 2 clinical records are not patient-matched. Genuine patient-level multimodal fusion has therefore not been established.

## Files in this module

- `Clinical_dataset.xlsx.txt` — tab-separated clinical dataset.
- `Clinical_Data_Analysis.ipynb` — exploratory data analysis and data-quality checks.
- `Clinical_Grade_Prediction.ipynb` — feature preparation and grade-prediction workflow.
- `clinical_grade_model.pkl` — serialized final model artifact.
- `breast_health_assessment.py` — standalone preliminary symptom-assessment component.
