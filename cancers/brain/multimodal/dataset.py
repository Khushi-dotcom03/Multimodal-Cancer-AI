"""Patient-level pairing of UTSW T1CE slices with clinical metadata."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
from PIL import Image, UnidentifiedImageError
import numpy as np

from cancers.brain.multimodal.config import MAX_SLICES_PER_PATIENT


def load_paired_patients(data_root: str | Path, clinical_file: str | Path) -> tuple[pd.DataFrame, dict]:
    root, clinical_path = Path(data_root), Path(clinical_file)
    if not root.is_dir():
        raise FileNotFoundError(f"MRI patient folder not found: {root}")
    if not clinical_path.is_file():
        raise FileNotFoundError(f"Clinical TSV not found: {clinical_path}")
    metadata = pd.read_csv(clinical_path, sep="\t")
    clinical_row_count = len(metadata)
    needed = {"Subject ID", "IDH", "Age at Imaging", "Sex at birth", "Tumor Grade", "1p19Q CODEL", "MGMT"}
    missing = needed - set(metadata.columns)
    if missing:
        raise ValueError(f"Clinical TSV missing required columns: {sorted(missing)}")
    metadata["Subject ID"] = metadata["Subject ID"].astype(str).str.strip()
    if metadata["Subject ID"].duplicated().any():
        dupes = metadata.loc[metadata["Subject ID"].duplicated(), "Subject ID"].tolist()
        raise ValueError(f"Clinical Subject ID must be unique; duplicates include {dupes[:5]}")
    metadata["IDH"] = metadata["IDH"].astype("string").str.strip().str.casefold()
    unknown_idh_count = int((~metadata["IDH"].isin(["mutated", "wild type"])).sum())
    metadata = metadata[metadata["IDH"].isin(["mutated", "wild type"])].copy()
    metadata["label"] = metadata["IDH"].map({"wild type": 0, "mutated": 1}).astype(int)

    patient_dirs = {p.name: p for p in root.iterdir() if p.is_dir() and p.name.startswith("BT")}
    rows, skipped = [], {"no_t1ce_slices": [], "corrupt_slices": []}
    clinical_ids = set(metadata["Subject ID"])
    for patient_id, folder in sorted(patient_dirs.items()):
        if patient_id not in clinical_ids:
            continue
        slices = sorted((folder / "brain_t1ce").glob("*.png"))
        valid = []
        # Verify only the deterministic training subset; scanning every file in the
        # archive is very slow on CPU and unused slices do not enter this experiment.
        verify_indices = np.linspace(0, len(slices) - 1, min(MAX_SLICES_PER_PATIENT, len(slices)), dtype=int) if slices else []
        for index in verify_indices:
            path = slices[int(index)]
            try:
                with Image.open(path) as im:
                    im.verify()
                valid.append(str(path.resolve()))
            except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
                skipped["corrupt_slices"].append(str(path))
        if not valid:
            skipped["no_t1ce_slices"].append(patient_id)
            continue
        record = metadata.loc[metadata["Subject ID"].eq(patient_id)].iloc[0].to_dict()
        record.update(patient_id=patient_id, slice_paths=valid, n_slices=len(valid))
        rows.append(record)
    paired = pd.DataFrame(rows).reset_index(drop=True)
    if paired.empty:
        raise ValueError("No IDH-labeled patients have both clinical rows and readable T1CE slices.")
    paired["label"] = paired["label"].astype(int)
    report = {
        "clinical_rows": int(clinical_row_count),
        "mri_patient_folders": len(patient_dirs),
        "paired_labeled_patients": int(len(paired)),
        "idh_class_counts": {"wild type": int((paired.label == 0).sum()), "mutated": int((paired.label == 1).sum())},
        "skipped_unknown_idh": unknown_idh_count,
        "mri_patients_without_clinical_record": int(len(set(patient_dirs) - set(pd.read_csv(clinical_path, sep="\t")["Subject ID"].astype(str).str.strip()))),
        "clinical_patients_without_mri_folder": int(len(set(pd.read_csv(clinical_path, sep="\t")["Subject ID"].astype(str).str.strip()) - set(patient_dirs))),
        "skipped_no_t1ce": skipped["no_t1ce_slices"],
        "corrupt_slice_files": skipped["corrupt_slices"],
        "total_valid_t1ce_slices": int(paired["n_slices"].sum()),
    }
    return paired, report
