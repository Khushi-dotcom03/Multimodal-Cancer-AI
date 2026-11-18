"""End-to-end multipart route smoke test against the original checkpoint."""

import io
import unittest

import numpy as np
import torch
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from api import brain_image_analysis
from Brain_cancer.image.service import CLASS_NAMES


class BrainAnalysisRouteTests(unittest.TestCase):
    def test_multipart_file_reaches_real_model_and_returns_result(self):
        # Valid PNG test input exercises upload/decode/inference plumbing; it is not an MRI
        # and its predicted class is not used as a model quality measurement.
        pixels = np.zeros((224, 224, 3), dtype=np.uint8)
        pixels[40:180, 50:170] = (115, 125, 140)
        buffer = io.BytesIO()
        Image.fromarray(pixels).save(buffer, format="PNG")
        upload = UploadFile(
            file=io.BytesIO(buffer.getvalue()),
            filename="brain-upload-smoke.png",
            headers=Headers({"content-type": "image/png"}),
        )
        original_threads = torch.get_num_threads()
        torch.set_num_threads(min(original_threads, 2))
        try:
            result = brain_image_analysis(upload)
        finally:
            torch.set_num_threads(original_threads)

        self.assertEqual(result["moduleId"], "brain-tumour")
        self.assertIn(result["prediction"], CLASS_NAMES)
        self.assertEqual(set(result["classScores"]), set(CLASS_NAMES))
        self.assertAlmostEqual(sum(result["classScores"].values()), 1.0, places=5)
        self.assertTrue(result["analysisId"])
        self.assertEqual(result["inferenceStatus"], "completed")
        self.assertTrue(result["gradcam"]["available"])
        self.assertTrue(result["gradcam"]["overlay"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
