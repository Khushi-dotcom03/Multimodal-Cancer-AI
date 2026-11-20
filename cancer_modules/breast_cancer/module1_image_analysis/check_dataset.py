
from pathlib import Path

dataset_path = Path(__file__).parent / "Dataset_BUSI_with_GT"

for category in ["normal", "benign", "malignant"]:
    folder = dataset_path / category
    files = list(folder.glob("*.png"))

    original_images = [
        file for file in files
        if "_mask" not in file.stem.lower()
    ]

    masks = [
        file for file in files
        if "_mask" in file.stem.lower()
    ]

    print(f"\n{category.upper()}")
    print("Original Images:", len(original_images))
    print("Segmentation Masks:", len(masks))

print("\nDataset verification completed!")
