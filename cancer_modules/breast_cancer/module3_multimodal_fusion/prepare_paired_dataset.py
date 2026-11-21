"""Validate and prepare official patient/case-paired BrEaST records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
from zipfile import ZipFile

import pandas as pd
from PIL import Image, UnidentifiedImageError


MODULE_DIR = Path(__file__).resolve().parent
RAW_DIR = MODULE_DIR / "data" / "raw"
ZIP_NAME = "BrEaST-Lesions_USG-images_and_masks-Dec-15-2023.zip"
XLSX_NAME = "BrEaST-Lesions-USG-clinical-data-Dec-15-2023.xlsx"
EXPECTED_FILES = {
    "Image_filename",
    "Mask_tumor_filename",
    "Mask_other_filename",
    "CaseID",
    "Age",
    "Tissue_composition",
    "Signs",
    "Symptoms",
    "Verification",
    "Diagnosis",
    "Classification",
}
LABELS = {"benign", "malignant", "normal"}
LEAKAGE_FIELDS = {
    "Interpretation",
    "BIRADS",
    "Verification",
    "Diagnosis",
    "Classification",
}
CLINICAL_FEATURES = ("Age", "Tissue_composition", "Signs", "Symptoms")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_zip_members(archive: ZipFile) -> list[str]:
    names = []
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe path in official image archive: {info.filename}")
        if info.is_dir():
            continue
        names.append(info.filename)
    if len(names) != len(set(names)):
        raise ValueError("The image archive contains duplicate member names.")
    return names


def _mask_names(value: Any) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [part.strip() for part in str(value).split("&") if part.strip()]


def validate_and_prepare(
    *,
    raw_dir: Path = RAW_DIR,
    extract_dir: Path | None = None,
    manifest_path: Path | None = None,
    audit_path: Path | None = None,
    overwrite_outputs: bool = False,
) -> dict[str, Any]:
    raw_dir = Path(raw_dir)
    extract_dir = Path(extract_dir or MODULE_DIR / "data" / "processed" / "BrEaST-Lesions_USG-images_and_masks")
    manifest_path = Path(manifest_path or MODULE_DIR / "data" / "processed" / "paired_cases.csv")
    audit_path = Path(audit_path or MODULE_DIR / "reports" / "paired_dataset_audit.json")
    zip_path, xlsx_path = raw_dir / ZIP_NAME, raw_dir / XLSX_NAME
    for path in (zip_path, xlsx_path):
        if not path.is_file():
            raise FileNotFoundError(f"Official BrEaST data file is missing: {path}")
    for path in (manifest_path, audit_path):
        if path.exists() and not overwrite_outputs:
            raise FileExistsError(f"Refusing to overwrite existing preparation output: {path}")

    clinical = pd.read_excel(xlsx_path, engine="openpyxl")
    missing_columns = sorted(EXPECTED_FILES - set(clinical.columns))
    if missing_columns:
        raise ValueError(f"Official XLSX is missing expected columns: {missing_columns}")
    if clinical["CaseID"].isna().any() or clinical["Image_filename"].isna().any():
        raise ValueError("Official metadata contains a missing CaseID or image filename.")
    if clinical["CaseID"].duplicated().any():
        raise ValueError("Official CaseID values are duplicated; refusing ambiguous patient matching.")
    if clinical["Image_filename"].duplicated().any():
        raise ValueError("Official image filenames are duplicated; refusing ambiguous patient matching.")

    with ZipFile(zip_path) as archive:
        members = _safe_zip_members(archive)
        corrupt_member = archive.testzip()
        if corrupt_member:
            raise ValueError(f"Image ZIP CRC check failed at {corrupt_member}")
        basename_to_member: dict[str, str] = {}
        for member in members:
            basename = PurePosixPath(member).name
            if basename in basename_to_member:
                raise ValueError(f"Duplicate archive basename cannot be mapped safely: {basename}")
            basename_to_member[basename] = member

        image_names = set(clinical["Image_filename"].astype(str))
        missing_images = sorted(name for name in image_names if name not in basename_to_member)
        if missing_images:
            raise ValueError(f"Official image references missing from ZIP ({len(missing_images)}): {missing_images[:10]}")
        expected_masks = {
            mask_name
            for column in ("Mask_tumor_filename", "Mask_other_filename")
            for value in clinical[column]
            for mask_name in _mask_names(value)
        }
        missing_masks = sorted(name for name in expected_masks if name not in basename_to_member)
        if missing_masks:
            raise ValueError(f"Official mask references missing from ZIP ({len(missing_masks)}): {missing_masks[:10]}")

        if extract_dir.exists():
            if not extract_dir.is_dir():
                raise FileExistsError(f"Extraction path exists and is not a directory: {extract_dir}")
            existing_names = {p.name for p in extract_dir.rglob("*") if p.is_file()}
            required_names = image_names | expected_masks
            missing_extracted = sorted(required_names - existing_names)
            if missing_extracted:
                raise FileExistsError(
                    f"Extraction directory is incomplete; refusing to overwrite/extract into it: "
                    f"{extract_dir} (missing {len(missing_extracted)} files)"
                )
        else:
            extract_dir.mkdir(parents=True)
            for member in members:
                relative = PurePosixPath(member)
                destination = extract_dir.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("xb") as output:
                    output.write(source.read())

    basename_to_path: dict[str, Path] = {}
    for path in extract_dir.rglob("*"):
        if path.is_file():
            if path.name in basename_to_path:
                raise ValueError(f"Duplicate extracted basename cannot be mapped safely: {path.name}")
            basename_to_path[path.name] = path.resolve()

    rows = []
    invalid_labels = []
    invalid_images = []
    for record in clinical.to_dict(orient="records"):
        label = str(record["Classification"]).strip().lower()
        if label not in LABELS:
            invalid_labels.append({"CaseID": str(record["CaseID"]), "label": label})
            continue
        image_path = basename_to_path.get(str(record["Image_filename"]))
        if image_path is None:
            raise ValueError(f"Extracted image not found for official CaseID {record['CaseID']}.")
        try:
            with Image.open(image_path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            invalid_images.append({"CaseID": str(record["CaseID"]), "file": str(image_path), "error": str(exc)})
            continue
        rows.append({
            "case_id": str(record["CaseID"]),
            "image_filename": str(record["Image_filename"]),
            "image_path": str(image_path),
            "tumor_mask_filenames": "&".join(_mask_names(record["Mask_tumor_filename"])),
            "other_mask_filenames": "&".join(_mask_names(record["Mask_other_filename"])),
            "age": record["Age"],
            "tissue_composition": record["Tissue_composition"],
            "signs": record["Signs"],
            "symptoms": record["Symptoms"],
            "verification": record["Verification"],
            "label": label,
        })
    if invalid_labels or invalid_images:
        raise ValueError(json.dumps({"invalid_labels": invalid_labels, "invalid_images": invalid_images}, indent=2))
    manifest = pd.DataFrame(rows)
    if manifest["case_id"].duplicated().any() or manifest["image_filename"].duplicated().any():
        raise ValueError("Prepared data contains duplicate case or image keys.")
    label_counts = manifest["label"].value_counts().sort_index().to_dict()
    if set(label_counts) != LABELS:
        raise ValueError(f"Expected official benign/malignant/normal labels; found {label_counts}")

    feature_missingness = {}
    for field in CLINICAL_FEATURES:
        normalized = manifest[field.lower() if field != "Tissue_composition" else "tissue_composition"]
        feature_missingness[field] = int(normalized.isna().sum() + normalized.astype(str).str.strip().str.lower().isin({"", "not available", "na", "n/a"}).sum())

    audit: dict[str, Any] = {
        "dataset": "BrEaST / TCIA Breast-Lesions-USG",
        "citation": "Pawlowska et al. (2024), Scientific Data 11, 148, DOI: 10.1038/s41597-024-02984-z; TCIA DOI: 10.7937/9WKK-Q141",
        "license": "CC BY 4.0; cite the dataset and follow TCIA Data Usage Policy",
        "sources": {
            "images_url": "https://www.cancerimagingarchive.net/wp-content/uploads/BrEaST-Lesions_USG-images_and_masks-Dec-15-2023.zip",
            "clinical_xlsx_url": "https://www.cancerimagingarchive.net/wp-content/uploads/BrEaST-Lesions-USG-clinical-data-Dec-15-2023.xlsx",
            "image_zip_sha256": sha256_file(zip_path),
            "clinical_xlsx_sha256": sha256_file(xlsx_path),
        },
        "matching": {
            "method": "official XLSX CaseID row + Image_filename + official mask filename columns",
            "rows": int(len(manifest)),
            "unique_case_ids": int(manifest.case_id.nunique()),
            "unique_image_filenames": int(manifest.image_filename.nunique()),
            "all_images_matched": True,
            "official_mask_references": int(len(expected_masks)),
            "all_mask_references_matched": True,
            "patient_group_key": "CaseID (one official case per patient in this release)",
        },
        "labels": {
            "all_cases": {str(k): int(v) for k, v in label_counts.items()},
            "binary_training_cases": int(manifest.label.isin({"benign", "malignant"}).sum()),
            "normal_cases_excluded_from_binary_task": int((manifest.label == "normal").sum()),
            "binary_training_labels": {str(k): int(v) for k, v in label_counts.items() if k in {"benign", "malignant"}},
            "verification_by_label": {
                str(label): {str(k): int(v) for k, v in group.value_counts(dropna=False).items()}
                for label, group in manifest.groupby("label")["verification"]
            },
        },
        "clinical_features": {
            "included_at_prediction_time": list(CLINICAL_FEATURES),
            "missing_or_not_available_counts": feature_missingness,
            "excluded_leakage_fields": sorted(LEAKAGE_FIELDS),
        },
        "data_quality": {
            "duplicate_case_ids": int(manifest.case_id.duplicated().sum()),
            "duplicate_image_refs": int(manifest.image_filename.duplicated().sum()),
            "duplicate_rows": int(manifest.duplicated().sum()),
            "normal_cases_with_no_tumor_mask": int(((manifest.label == "normal") & manifest.tumor_mask_filenames.eq("")).sum()),
            "images_verified_readable": int(len(manifest)),
            "sha256_duplicate_image_files": _duplicate_image_hashes(manifest),
        },
        "limitations": [
            "Only four normal cases are present; they are excluded from binary malignant-versus-benign model fitting and no normal-class performance is claimed.",
            "The cohort is small and a single public dataset; internal cross-validation does not establish independent external validation.",
            "The research score is not calibrated as a cancer probability and is not a diagnosis.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(manifest_path, index=False)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def _duplicate_image_hashes(manifest: pd.DataFrame) -> list[list[str]]:
    seen: dict[str, list[str]] = {}
    for row in manifest.itertuples(index=False):
        digest = sha256_file(Path(row.image_path))
        seen.setdefault(digest, []).append(str(row.case_id))
    return [case_ids for case_ids in seen.values() if len(case_ids) > 1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--extract-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--overwrite-outputs", action="store_true", help="Replace only the generated manifest and audit, never source data or extracted files.")
    args = parser.parse_args()
    audit = validate_and_prepare(
        raw_dir=args.raw_dir,
        extract_dir=args.extract_dir,
        manifest_path=args.manifest,
        audit_path=args.audit,
        overwrite_outputs=args.overwrite_outputs,
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
