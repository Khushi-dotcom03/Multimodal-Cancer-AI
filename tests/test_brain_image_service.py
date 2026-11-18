import io
import uuid
import unittest
from pathlib import Path

from PIL import Image

from Brain_cancer.image.service import (
    BrainImageError,
    BrainModelUnavailable,
    BrainMRIService,
    CLASS_NAMES,
    PREPROCESS,
)


class BrainImageServiceTests(unittest.TestCase):
    def setUp(self):
        buffer = io.BytesIO()
        Image.new("RGB", (128, 96), color=(120, 80, 60)).save(buffer, format="PNG")
        self.png = buffer.getvalue()

    def test_original_class_index_order_is_preserved(self):
        self.assertEqual(CLASS_NAMES, ["Glioma", "Meningioma", "No Tumor", "Pituitary Tumor"])

    def test_preprocessing_matches_checkpoint_input_contract(self):
        image = Image.open(io.BytesIO(self.png)).convert("RGB")
        tensor = PREPROCESS(image)
        self.assertEqual(tuple(tensor.shape), (3, 224, 224))

    def test_decode_png_and_convert_to_rgb(self):
        image = BrainMRIService.decode_image(self.png, "scan.png", "image/png")
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (128, 96))

    def test_decode_png_when_browser_reports_generic_mime_type(self):
        image = BrainMRIService.decode_image(self.png, "scan.png", "application/octet-stream")
        self.assertEqual(image.size, (128, 96))

    def test_decode_jpg_when_browser_reports_image_jpg(self):
        buffer = io.BytesIO()
        Image.new("RGB", (128, 96)).save(buffer, format="JPEG")
        image = BrainMRIService.decode_image(buffer.getvalue(), "scan.jpg", "image/jpg")
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (128, 96))

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(BrainImageError):
            BrainMRIService.decode_image(self.png, "scan.webp", "image/png")

    def test_missing_original_checkpoint_is_reported(self):
        missing = Path(__file__).parent / f"missing-{uuid.uuid4().hex}.pth"
        service = BrainMRIService(missing, "cpu")
        with self.assertRaises(BrainModelUnavailable):
            service.load_model()


if __name__ == "__main__":
    unittest.main()
