
from pathlib import Path

dataset_path = Path(__file__).parent / "Dataset_BUSI_with_GT"

for category in ["normal", "benign", "malignant"]:
    folder = dataset_path / category

    images = [
        file for file in folder.glob("*.png")
        if "_mask" not in file.stem.lower()
    ]

    print(f"{category}: {len(images)} original images")

print("Image selection completed!")
