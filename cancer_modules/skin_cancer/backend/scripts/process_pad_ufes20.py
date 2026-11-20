"""Quality-audit and make patient-disjoint PAD-UFES-20 processing manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError


BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "data"
VERSION = 1
BASE = DATA / "extracted" / "PAD-UFES-20" / f"v{VERSION}"
RAW = DATA / "raw" / "PAD-UFES-20" / f"v{VERSION}"
IMAGE_ROOT = BASE / "images"
METADATA = RAW / "metadata.csv"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
LABEL_COLUMNS = {"diagnostic", "diagnosis", "dx", "label", "class", "target"}
PATIENT_COLUMNS = {"patient_id", "patientid", "patient"}
LESION_COLUMNS = {"lesion_id", "lesionid", "lesion"}


def normalize(value: object) -> str:
    return str(value).strip().casefold()


def normalized_headers(headers: list[str]) -> dict[str, str]:
    return {re.sub(r"[^a-z0-9]+", "", header.casefold()): header for header in headers}


def choose_column(columns: dict[str, str], candidates: set[str]) -> str | None:
    for candidate in sorted(candidates):
        if candidate in columns:
            return columns[candidate]
    return None


def patient_lesion_key(row: dict[str, str], patient_col: str | None, lesion_col: str | None) -> str | None:
    if not patient_col or not lesion_col:
        return None
    patient = normalize(row.get(patient_col, ""))
    lesion = normalize(row.get(lesion_col, ""))
    if not patient or not lesion or patient in {"nan", "none"} or lesion in {"nan", "none"}:
        return None
    return f"{patient}|{lesion}"


def image_keys(path: Path) -> set[str]:
    keys = {normalize(path.stem)}
    match = re.fullmatch(r"PAT_(\d+)_(\d+)_(\d+)", path.stem, flags=re.IGNORECASE)
    if match:
        keys.add("|".join(part.casefold() for part in match.groups()))
        keys.add(match.group(3).casefold())
        keys.add(f"pat_{match.group(1)}_{match.group(2)}_{match.group(3)}".casefold())
    return keys


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_by_patient(rows: list[dict], patient_field: str, seed: int = 42) -> dict[str, str]:
    """Greedy multilabel patient-group allocation targeting 70/15/15 by class."""
    fractions = {"train": 0.70, "validation": 0.15, "test": 0.15}
    classes = sorted({row["label"] for row in rows})
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row[patient_field]].append(row)
    if len(grouped) < 10:
        raise ValueError("Too few distinct patient groups to create stable grouped splits")
    global_counts = Counter(row["label"] for row in rows)
    targets = {split: {label: global_counts[label] * fraction for label in classes} for split, fraction in fractions.items()}
    targets["_total"] = {split: len(rows) * fraction for split, fraction in fractions.items()}
    current = {split: Counter() for split in fractions}
    totals = Counter()
    rng = random.Random(seed)
    patients = list(grouped.items())
    rng.shuffle(patients)
    patients.sort(key=lambda pair: (-len(pair[1]), pair[0]))
    assignment: dict[str, str] = {}
    for patient, patient_rows in patients:
        label_counts = Counter(row["label"] for row in patient_rows)
        candidates = []
        for candidate in fractions:
            cost = 0.0
            for split in fractions:
                for label in classes:
                    value = current[split][label] + (label_counts[label] if split == candidate else 0)
                    target = targets[split][label]
                    cost += ((value - target) / max(target, 1.0)) ** 2
                value_total = totals[split] + (len(patient_rows) if split == candidate else 0)
                target_total = targets["_total"][split]
                cost += ((value_total - target_total) / max(target_total, 1.0)) ** 2
            candidates.append((cost, rng.random(), candidate))
        split = min(candidates)[2]
        assignment[patient] = split
        current[split].update(label_counts)
        totals[split] += len(patient_rows)
    return assignment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=METADATA)
    parser.add_argument("--images", type=Path, default=IMAGE_ROOT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.metadata.is_file() or not args.images.is_dir():
        raise SystemExit("PAD-UFES-20 metadata/images are not present; run download_pad_ufes20.py first")

    with args.metadata.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("The metadata CSV has no header")
        headers = list(reader.fieldnames)
        source_rows = list(reader)
    if not source_rows:
        raise ValueError("The metadata CSV is empty")
    columns = normalized_headers(headers)
    label_col = choose_column(columns, LABEL_COLUMNS)
    patient_col = choose_column(columns, PATIENT_COLUMNS)
    lesion_col = choose_column(columns, LESION_COLUMNS)
    if not label_col or not patient_col or not lesion_col:
        raise ValueError(f"Required diagnosis/patient/lesion columns not found. Available: {headers}")

    id_col = choose_column(columns, {"imgid", "imageid", "image", "filename", "file", "imagefilename"})
    rows_by_key: dict[str, list[int]] = defaultdict(list)
    rows_by_lesion: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(source_rows):
        lesion_key = patient_lesion_key(row, patient_col, lesion_col)
        if lesion_key:
            rows_by_lesion[lesion_key].append(index)
        if id_col and row.get(id_col, "").strip():
            value = normalize(Path(row[id_col].strip()).stem)
            rows_by_key[value].append(index)
            if value.isdigit():
                rows_by_key[value.lstrip("0") or "0"].append(index)

    image_paths = sorted(path for path in args.images.rglob("*") if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS)
    invalid_images = []
    image_dimensions = Counter()
    image_hashes: dict[str, list[str]] = defaultdict(list)
    matched_rows: list[dict] = []
    matched_image_paths: set[str] = set()
    image_to_metadata: dict[int, int] = {}
    ambiguous = []
    unmatched_images = []
    for image_path in image_paths:
        try:
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                width, height = image.size
                image_format = image.format or image_path.suffix.lstrip(".").upper()
            image_dimensions[f"{width}x{height}"] += 1
            digest = hash_file(image_path)
            image_hashes[digest].append(str(image_path.relative_to(args.images)))
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            invalid_images.append({"path": str(image_path.relative_to(args.images)), "reason": type(exc).__name__})
            continue

        candidate_indices: set[int] = set()
        for key in image_keys(image_path):
            candidate_indices.update(rows_by_key.get(key, []))
        if not candidate_indices:
            match = re.fullmatch(r"PAT_(\d+)_(\d+)_(\d+)", image_path.stem, flags=re.IGNORECASE)
            if match:
                candidate_indices.update(rows_by_lesion.get(f"{match.group(1)}|{match.group(2)}", []))
        if len(candidate_indices) == 1:
            metadata_index = next(iter(candidate_indices))
            image_to_metadata[metadata_index] = image_to_metadata.get(metadata_index, 0) + 1
            matched_image_paths.add(str(image_path.relative_to(args.images)))
            metadata_row = source_rows[metadata_index]
            row = dict(metadata_row)
            row["image_path"] = str(image_path.relative_to(args.images))
            row["patient_group"] = normalize(metadata_row[patient_col])
            row["label"] = metadata_row[label_col].strip()
            row["image_format"] = image_format
            row["image_width"] = width
            row["image_height"] = height
            row["image_sha256"] = digest
            matched_rows.append(row)
        elif len(candidate_indices) > 1:
            ambiguous.append({"image": str(image_path.relative_to(args.images)), "candidate_metadata_rows": len(candidate_indices)})
        else:
            unmatched_images.append(str(image_path.relative_to(args.images)))

    metadata_duplicate_rows = len(source_rows) - len({tuple((key, row.get(key, "")) for key in headers) for row in source_rows})
    unique_patients = {normalize(row[patient_col]) for row in source_rows if row.get(patient_col, "").strip()}
    patient_split = split_by_patient(matched_rows, "patient_group", args.seed) if matched_rows else {}
    for row in matched_rows:
        row["split"] = patient_split[row["patient_group"]]

    class_counts = Counter(row["label"] for row in matched_rows)
    split_counts = {split: dict(Counter(row["label"] for row in matched_rows if row["split"] == split)) for split in ("train", "validation", "test")}
    missing = {header: sum(not row.get(header, "").strip() for row in source_rows) for header in headers}
    duplicate_image_groups = [paths for paths in image_hashes.values() if len(paths) > 1]
    image_split = {row["image_path"]: row["split"] for row in matched_rows}
    duplicate_group_split_counts = Counter(
        "/".join(sorted({image_split[path] for path in group if path in image_split}))
        for group in duplicate_image_groups
    )
    lesion_patients: dict[str, set[str]] = defaultdict(set)
    for row in source_rows:
        lesion = normalize(row.get(lesion_col, ""))
        patient = normalize(row.get(patient_col, ""))
        if lesion and patient and lesion not in {"nan", "none"} and patient not in {"nan", "none"}:
            lesion_patients[lesion].add(patient)
    summary = {
        "dataset": "PAD-UFES-20",
        "dataset_version": VERSION,
        "license": "CC BY 4.0",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "metadata_path": str(args.metadata),
        "image_root": str(args.images),
        "metadata_rows": len(source_rows),
        "metadata_columns": headers,
        "metadata_inferred_types": {header: "numeric" if all((not row.get(header, "").strip()) or _looks_numeric(row[header]) for row in source_rows) else "categorical/text" for header in headers},
        "metadata_missing_values": missing,
        "exact_duplicate_metadata_rows": metadata_duplicate_rows,
        "unique_patient_count": len(unique_patients),
        "unique_lesion_id_values": len(lesion_patients),
        "unique_patient_lesion_pairs": len(rows_by_lesion),
        "lesion_id_values_associated_with_multiple_patient_ids": sum(len(patients) > 1 for patients in lesion_patients.values()),
        "image_files_found": len(image_paths),
        "valid_images": len(image_paths) - len(invalid_images),
        "invalid_image_count": len(invalid_images),
        "invalid_image_reasons": dict(Counter(item["reason"] for item in invalid_images)),
        "image_dimensions": dict(image_dimensions),
        "byte_identical_duplicate_image_group_count": len(duplicate_image_groups),
        "byte_identical_duplicate_image_rows": sum(len(group) for group in duplicate_image_groups),
        "byte_identical_duplicate_group_size_counts": dict(Counter(str(len(group)) for group in duplicate_image_groups)),
        "byte_identical_duplicate_group_split_counts": dict(duplicate_group_split_counts),
        "byte_identical_duplicate_groups_crossing_splits": sum(len({image_split[path] for path in group if path in image_split}) > 1 for group in duplicate_image_groups),
        "image_match_count": len(matched_rows),
        "unmatched_image_count": len(unmatched_images),
        "ambiguous_image_match_count": len(ambiguous),
        "metadata_rows_with_no_matched_image": len(source_rows) - len(image_to_metadata),
        "metadata_rows_with_multiple_images": sum(count > 1 for count in image_to_metadata.values()),
        "label_column": label_col,
        "label_distribution_matched_images": dict(class_counts),
        "patient_disjoint_split_counts": split_counts,
        "split_method": "deterministic greedy multilabel group allocation by patient; seed " + str(args.seed),
        "clinical_numeric_encoding": "Not applied in this audit; no imputation or fabricated values are introduced.",
    }

    processed_dir = DATA / "processed" / "PAD-UFES-20" / f"v{VERSION}"
    processed_dir.mkdir(parents=True, exist_ok=True)
    matched_csv = processed_dir / "matched_images.csv"
    with matched_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[*headers, "image_path", "patient_group", "label", "image_format", "image_width", "image_height", "image_sha256", "split"])
        writer.writeheader()
        writer.writerows(matched_rows)

    reports_dir = DATA / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "pad_ufes20_quality.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("metadata_rows", "unique_patient_count", "unique_patient_lesion_pairs", "image_files_found", "valid_images", "image_match_count", "label_distribution_matched_images", "patient_disjoint_split_counts")}, indent=2))
    print(f"Detailed aggregate audit: {report_path}")
    print(f"Matched table (Git-ignored): {matched_csv}")
    return 0


def _looks_numeric(value: str) -> bool:
    try:
        float(value.replace(",", "."))
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
