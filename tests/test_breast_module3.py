import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from api import app
from cancer_modules.breast_cancer.module3_multimodal_fusion import api as module3_api


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "cancer_modules" / "breast_cancer" / "module3_multimodal_fusion"
client = TestClient(app)


def _png_bytes() -> bytes:
    from io import BytesIO

    output = BytesIO()
    Image.new("RGB", (12, 12), "white").save(output, format="PNG")
    return output.getvalue()


def test_dataset_compatibility_audit_blocks_invalid_fusion():
    report = json.loads((MODULE_DIR / "reports" / "paired_feature_compatibility_audit.json").read_text(encoding="utf-8"))
    breast = report["local_datasets"]["BrEaST_TCIA"]
    assert breast["case_image_matches"] == 256
    assert set(breast["missing_required_module2_fields"]) == {"Tumor Size", "ER Status", "PR Status", "HER2 Status"}
    assert report["active_fusion_model_exists"] is False
    assert report["previous_breast_paired_fusion_artifact_preserved_but_used"] is False


def test_endpoint_passes_image_and_exact_module2_fields_to_existing_pipelines(monkeypatch):
    seen = {}

    def fake_image(path):
        seen["image_exists_during_inference"] = Path(path).is_file()
        return {
            "status": "success",
            "prediction": "Benign",
            "confidence": 0.91,
            "class_probabilities": {"Normal": 0.01, "Benign": 0.91, "Malignant": 0.08},
            "validator_probability": 0.99,
            "message": "ok",
        }

    def fake_clinical(features):
        seen["features"] = features
        return {"status": "success", "predicted_grade": 2, "grade_label": "Grade 2", "message": "grade only"}

    monkeypatch.setattr(module3_api, "predict_ultrasound", fake_image)
    monkeypatch.setattr(module3_api, "predict_clinical_grade", fake_clinical)
    values = {
        "Age at Diagnosis": 48,
        "Tumor Size": 2.4,
        "ER Status": "Positive",
        "PR Status": "Negative",
        "HER2 Status": "Negative",
    }
    response = client.post(
        "/api/v1/analysis/breast-cancer-fusion",
        files={"file": ("ultrasound.png", _png_bytes(), "image/png")},
        data={"features": json.dumps(values)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert seen["image_exists_during_inference"] is True
    assert seen["features"] == values
    assert payload["imageResult"]["probabilities"]["Benign"] == 0.91
    assert payload["clinicalResult"]["predictedGradeLabel"] == "Grade 2"
    assert payload["fusionResult"] == {
        "status": "unavailable",
        "prediction": None,
        "score": None,
        "reason": payload["fusionResult"]["reason"],
    }
    assert "cancer probability" in payload["fusionResult"]["reason"].lower()


def test_invalid_image_does_not_prevent_clinical_inference(monkeypatch):
    called = []
    monkeypatch.setattr(module3_api, "predict_clinical_grade", lambda features: (called.append(features) or {
        "status": "success", "predicted_grade": 1, "grade_label": "Grade 1", "message": "ok"
    }))
    response = client.post(
        "/api/v1/analysis/breast-cancer-fusion",
        files={"file": ("not-image.txt", b"bad image", "text/plain")},
        data={"features": json.dumps({"Age at Diagnosis": 40, "Tumor Size": 1.2, "ER Status": "Positive", "PR Status": "Positive", "HER2 Status": "Negative"})},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["imageResult"]["status"] == "invalid_image"
    assert payload["clinicalResult"]["predictedGradeLabel"] == "Grade 1"
    assert called
    assert payload["fusionResult"]["status"] == "unavailable"


def test_invalid_clinical_json_does_not_suppress_image_inference(monkeypatch):
    called = []
    monkeypatch.setattr(module3_api, "predict_ultrasound", lambda path: (called.append(path) or {
        "status": "success", "prediction": "Malignant", "confidence": 0.8,
        "class_probabilities": {"Normal": 0.0, "Benign": 0.2, "Malignant": 0.8},
        "validator_probability": 1.0, "message": "ok"
    }))
    response = client.post(
        "/api/v1/analysis/breast-cancer-fusion",
        files={"file": ("ultrasound.png", _png_bytes(), "image/png")},
        data={"features": "not-json"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert called
    assert payload["imageResult"]["prediction"] == "Malignant"
    assert payload["clinicalResult"]["status"] == "invalid_input"
    assert payload["fusionResult"]["score"] is None


def test_frontend_uses_exact_module2_fields_and_has_no_fusion_score():
    source = (ROOT / "frontend" / "components" / "analysis" / "breast-combined-analysis-workspace.tsx").read_text(encoding="utf-8")
    assert "/api/proxy/breast-cancer-fusion" in source
    for field in ("Age at Diagnosis", "Tumor Size", "ER Status", "PR Status", "HER2 Status"):
        assert field in source
    assert "Tissue Composition" not in source
    assert "Experimental fusion score" not in source
    assert "Fusion result unavailable." in source
    assert "Cancer / Non-cancer combined result" in source
    assert source.count("Not estimated") == 2
    proxy = (ROOT / "frontend" / "app" / "api" / "proxy" / "breast-cancer-fusion" / "route.ts").read_text(encoding="utf-8")
    assert "/api/v1/analysis/breast-cancer-fusion" in proxy
