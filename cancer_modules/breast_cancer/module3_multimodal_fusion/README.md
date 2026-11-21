# Breast Cancer Combined Analysis (Module 3)

Module 3 runs the existing Module 1 breast ultrasound inference and Module 2 histologic-grade inference independently. It displays their original kinds of outputs and explicitly reports that multimodal fusion is unavailable. It does not produce a combined prediction, score, or cancer probability.

## Input and inference contract

- Image: JPG, JPEG, or PNG upload passed to the same `predict_ultrasound` function used by the Module 1 API. That adapter loads the existing Module 1 validator and classifier and preserves its preprocessing and result semantics.
- Clinical: exactly `Age at Diagnosis`, `Tumor Size`, `ER Status`, `PR Status`, and `HER2 Status`, passed to the same `predict_clinical_grade` function used by the Module 2 API. That adapter loads the saved Module 2 pipeline and its fitted preprocessing unchanged.
- Histologic grade is displayed only as grade. It is never mapped to cancer probability or used as a fusion weight.

The Module 3 endpoint is `POST /api/v1/analysis/breast-cancer-fusion`. It accepts multipart `file` plus `features` (JSON object using the five exact Module 2 feature names). Image and clinical inference run independently: a failed/invalid input on one side does not suppress the other side's output. The response's `fusionResult.status` is always `unavailable` until suitable paired, labelled training data is verified and a valid fusion model is trained and evaluated.

## Dataset compatibility audit

The local BrEaST / TCIA images and clinical XLSX were checked by official CaseID and Image_filename: 256 unique cases map to 256 images; all official mask references resolve. Labels include 154 benign, 98 malignant, and 4 normal cases. Its clinical columns include Age, Tissue composition, Signs, and Symptoms. It does **not** contain Tumor Size, ER Status, PR Status, or HER2 Status, and its Age field is not asserted equivalent to Module 2's Age at Diagnosis. Therefore BrEaST is not compatible with Module 2's five-input feature contract, even though it has linked ultrasound and benign/malignant labels.

The local BUSI image dataset has no linked records for Module 2 clinical features. The local Module 2 METABRIC records are not patient-linked to BUSI; their identifiers must not be joined to BUSI filenames. No compatible local dataset was found. Publicly described datasets such as BUSI-WHU advertise ultrasound, benign/malignant images, patient information, and an XLSX file, but the published metadata inspected does not verify that every one of the five required Module 2 fields is present and mapped per image. That candidate is not treated as compatible without a direct schema and identifier audit. A small published research cohort that reports ultrasound, age, lesion size, ER/PR/HER2, and benign/malignant cases is not enough by itself: a reproducible patient-level image-to-row dataset with access terms and complete records must be available before use.

Audit details are recorded in `reports/paired_feature_compatibility_audit.json`. The previous BrEaST experiment files and artifact are preserved on disk but are **not loaded or used** by the active Module 3 endpoint. Its metrics do not evaluate the Module 1 + Module 2 combination and must not be presented as such.

## Fusion status and limitations

There is currently no validated fusion method or trained fusion model for the exact Module 1/Module 2 inputs. Training cannot proceed without a dataset that has (1) ultrasound images, (2) all five clinical features available for those same patients, (3) reliable benign/malignant ground truth, and (4) identifiers that verify those links. No synthetic or cross-dataset pairings are allowed. The UI shows separate model outputs and a clear fusion-unavailable explanation. This is a research application, not a medical diagnostic tool.

## Run and test

From the repository root:

```powershell
..\venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8002 --reload
..\venv\Scripts\python.exe -m pytest tests/test_breast_module3.py -q
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Open `/breast-evidence-review`. The Module 3 Next.js proxy forwards to port 8002 by default; set `BREAST_MODULE3_API_URL` to use another backend address.

## Dataset references

- Pawłowska et al. (2024), “A Curated benchmark dataset for ultrasound based breast lesion analysis,” *Scientific Data* 11, 148. [Article DOI](https://doi.org/10.1038/s41597-024-02984-z); [TCIA collection](https://www.cancerimagingarchive.net/collection/breast-lesions-usg/), DOI 10.7937/9WKK-Q141. BrEaST data are CC BY 4.0; retain attribution and follow the [TCIA Data Usage Policy](https://www.cancerimagingarchive.net/data-usage-policies/).
- Huang et al. (2025), [BUSI-WHU dataset](https://data.mendeley.com/datasets/k6cpmwybk3/3), DOI 10.17632/k6cpmwybk3.3, CC BY 4.0. Public metadata lists 927 ultrasound images and a patient-information XLSX; exact compatibility with the five Module 2 fields is not verified, so this dataset is not used here.
# Local class-balanced clinical-grade candidate

To address the repeated Grade 3 output, the local Breast Clinical and Combined Analysis pages use a separate, versioned class-balanced candidate served on port `8003`. The original Module 2 model artifact and API remain untouched. The candidate uses the exact five existing clinical inputs and Grade 1/2/3 labels; it does not estimate cancer probability.

The candidate was compared using five-fold stratified patient-grouped cross-validation. The dataset has 2,388 labeled records and 2,388 unique patient IDs. Mean accuracy was `0.5486`, macro F1 was `0.4592`, and mean recall was `0.2522` (Grade 1), `0.5113` (Grade 2), and `0.6319` (Grade 3). These retrospective results are modest and do not establish clinical validity. The class-balanced candidate reduces Grade 3 dominance; it does not guarantee a particular grade for any input.

Recreate the candidate and report from the project root:

```powershell
py cancer_modules/breast_cancer/module3_multimodal_fusion/train_balanced_grade_candidate.py
py -3.14 -m uvicorn cancer_modules.breast_cancer.module3_multimodal_fusion.balanced_clinical_api:app --host 127.0.0.1 --port 8003
```

The model is stored as `artifacts/clinical_grade_balanced_candidate.pkl`; evaluation details are in `reports/clinical_grade_balanced_candidate.json`. The API returns the existing Module 2 response fields and keeps its research-only disclaimer. The local frontend proxies Module 2 clinical submissions to this candidate and uses the same output in Module 3. Module 1 inference and both original Module 2 data/model artifacts are unchanged.
