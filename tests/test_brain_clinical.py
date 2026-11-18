import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from api import app
from Brain_cancer.clinical.api import BrainClinicalRequest, brain_clinical_analysis
from Brain_cancer.clinical.pipeline import CLASSES, DEFAULT_DATASET, FEATURE_COLUMNS, audit_dataset
from Brain_cancer.clinical.service import service


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "Brain_cancer" / "evaluation" / "brain_clinical_metrics.json"


class BrainClinicalTests(unittest.TestCase):
    def test_clinical_endpoint_is_registered(self):
        self.assertIn("/api/v1/cancers/brain/clinical-analysis", app.openapi()["paths"])

    def test_dataset_audit_and_leakage_schema(self):
        frame, audit = audit_dataset(DEFAULT_DATASET)
        self.assertEqual(audit["record_count"], 328)
        self.assertEqual(audit["unique_patient_groups"], 328)
        self.assertEqual(audit["duplicate_patient_group_rows"], 0)
        self.assertEqual(set(audit["subtype_counts"]), set(CLASSES))
        self.assertEqual(FEATURE_COLUMNS, ["Age", "Sex", "SITE"])
        self.assertEqual(len(frame.loc[frame["_diagnosis_conflict"]]), 1)
        self.assertIn("C/F", audit["feature_selection"]["excluded"])
        self.assertIn("Radiology", audit["feature_selection"]["excluded"])

    def test_grouped_holdout_has_no_patient_overlap_and_beats_baseline(self):
        report = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        training = report["training"]
        holdout = training["patient_level_holdout"]
        self.assertEqual(holdout["group_overlap"], 0)
        self.assertTrue(training["deployment_eligible"])
        self.assertGreater(
            training["test_metrics"]["selected_model"]["macro_f1"],
            training["test_metrics"]["majority_class_baseline"]["macro_f1"],
        )

    def test_saved_pipeline_returns_actual_three_class_scores(self):
        payload = BrainClinicalRequest(age=45, sex="F", site="left frontal")
        response = brain_clinical_analysis(payload)
        self.assertIn(response["predictedSubtype"], CLASSES)
        self.assertEqual(set(response["classScores"]), set(CLASSES))
        self.assertAlmostEqual(sum(response["classScores"].values()), 1.0, places=6)
        self.assertTrue(response["analysisId"])
        self.assertEqual(response["inferenceStatus"], "completed")
        self.assertEqual(response["model"]["features"], FEATURE_COLUMNS)
        self.assertEqual(response["inputSummary"]["site"], "left frontal")
        self.assertIn("not a diagnosis", response["disclaimer"])
        self.assertIs(service.load(), service.load())

    def test_optional_site_missing_value_is_supported(self):
        response = brain_clinical_analysis(BrainClinicalRequest(age=45, sex="F", site=None))
        self.assertEqual(response["inputSummary"]["site"], "Not provided")
        self.assertAlmostEqual(sum(response["classScores"].values()), 1.0, places=6)

    def test_invalid_age_and_sex_are_rejected(self):
        with self.assertRaises(ValidationError):
            BrainClinicalRequest(age=100, sex="F", site=None)
        with self.assertRaises(ValidationError):
            BrainClinicalRequest(age=45, sex="unknown", site=None)


if __name__ == "__main__":
    unittest.main()
