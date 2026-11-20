"""Match the checked-in HAM split to official ISIC images and clinical metadata."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError


BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "data"
RAW = DATA / "raw" / "HAM10000" / "ISIC2018-Task3"
IMAGE_ROOT = DATA / "extracted" / "HAM10000" / "ISIC2018-Task3"
SPLIT_FILE = DATA / "split.csv"
METADATA_FILE = RAW / "ISIC_2019_Training_Metadata.csv"
GROUPINGS_FILE = RAW / "ISIC2018_Task3_Training_LesionGroupings.csv"
IMAGE_EXTENSIONS = {".jpg", ".jpeg"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path.name}")
        return list(reader.fieldnames), list(reader)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    for path in (SPLIT_FILE, METADATA_FILE, GROUPINGS_FILE):
        if not path.is_file():
            raise SystemExit(f"Required HAM10000 source file is missing: {path}")

    split_headers, split_rows = read_csv(SPLIT_FILE)
    metadata_headers, metadata_rows = read_csv(METADATA_FILE)
    grouping_headers, grouping_rows = read_csv(GROUPINGS_FILE)
    required_split = {"image_id", "lesion_id", "dx", "label", "split"}
    if not required_split.issubset(split_headers):
        raise ValueError(f"Unexpected checked-in split schema: {split_headers}")
    if "image" not in metadata_headers:
        raise ValueError(f"Expected image ID key in metadata CSV: {metadata_headers}")
    if "image" not in grouping_headers:
        raise ValueError(f"Expected image ID key in lesion grouping CSV: {grouping_headers}")

    def indexed(rows: list[dict[str, str]], key: str) -> tuple[dict[str, dict[str, str]], list[str]]:
        lookup: dict[str, dict[str, str]] = {}
        duplicates = []
        for row in rows:
            value = Path((row.get(key) or "").strip()).stem
            if value in lookup:
                duplicates.append(value)
            else:
                lookup[value] = row
        return lookup, duplicates

    metadata_by_image, duplicate_metadata_ids = indexed(metadata_rows, "image")
    group_by_image, duplicate_group_ids = indexed(grouping_rows, "image")
    split_by_image, duplicate_split_ids = indexed(split_rows, "image_id")
    image_paths = sorted(path for path in IMAGE_ROOT.rglob("*") if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS)
    paths_by_id: dict[str, list[Path]] = defaultdict(list)
    invalid_images = []
    dimensions = Counter()
    hashes: dict[str, list[str]] = defaultdict(list)
    for path in image_paths:
        paths_by_id[path.stem].append(path)
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                dimensions[f"{image.width}x{image.height}"] += 1
            hashes[sha256_file(path)].append(path.stem)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            invalid_images.append({"image_id": path.stem, "reason": type(exc).__name__})

    duplicate_file_ids = {key: len(paths) for key, paths in paths_by_id.items() if len(paths) > 1}
    valid_image_ids = {key for key, paths in paths_by_id.items() if len(paths) == 1} - {row["image_id"] for row in invalid_images}
    split_ids = set(split_by_image)
    metadata_ids = set(metadata_by_image)
    grouping_ids = set(group_by_image)
    matched_ids = split_ids & metadata_ids & grouping_ids & valid_image_ids
    missing_images = sorted(split_ids - valid_image_ids)
    images_without_split = sorted(set(paths_by_id) - split_ids)
    missing_metadata = sorted(split_ids - metadata_ids)
    missing_grouping = sorted(split_ids - grouping_ids)
    matched_rows = []
    image_hash_splits: dict[str, set[str]] = defaultdict(set)
    for image_id in sorted(matched_ids):
        split_row = split_by_image[image_id]
        metadata_row = metadata_by_image[image_id]
        group_row = group_by_image[image_id]
        path = paths_by_id[image_id][0]
        record = {**split_row, **{f"metadata_{key}": value for key, value in metadata_row.items() if key != "image"}}
        record["diagnosis_confirm_type"] = group_row.get("diagnosis_confirm_type", "")
        record["image_path"] = str(path.relative_to(IMAGE_ROOT))
        record["image_sha256"] = sha256_file(path)
        matched_rows.append(record)
        image_hash_splits[record["image_sha256"]].add(split_row["split"])

    duplicate_hash_groups = [ids for ids in hashes.values() if len(ids) > 1]
    crossing_duplicate_groups = sum(
        len(image_hash_splits[sha256_file(paths_by_id[group[0]][0])]) > 1
        for group in duplicate_hash_groups
        if group and group[0] in paths_by_id and len(paths_by_id[group[0]]) == 1
    )
    missing_values = {
        key: sum(not (metadata_by_image[image_id].get(key) or "").strip() for image_id in matched_ids)
        for key in metadata_headers
        if key != "image"
    }
    labels = Counter(row["dx"] for row in matched_rows)
    split_counts = Counter(row["split"] for row in matched_rows)
    report = {
        "dataset": "HAM10000 / ISIC 2018 Task 3",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "license": "CC BY-NC 4.0",
        "image_count": len(image_paths),
        "valid_images": len(image_paths) - len(invalid_images),
        "invalid_image_count": len(invalid_images),
        "invalid_image_reasons": dict(Counter(row["reason"] for row in invalid_images)),
        "dimensions": dict(dimensions),
        "exact_duplicate_image_hash_group_count": len(duplicate_hash_groups),
        "exact_duplicate_image_hash_size_counts": dict(Counter(str(len(group)) for group in duplicate_hash_groups)),
        "duplicate_image_ids_in_archive_count": len(duplicate_file_ids),
        "duplicate_metadata_image_ids_count": len(duplicate_metadata_ids),
        "duplicate_grouping_image_ids_count": len(duplicate_group_ids),
        "duplicate_split_image_ids_count": len(duplicate_split_ids),
        "split_records": len(split_rows),
        "metadata_records": len(metadata_rows),
        "grouping_records": len(grouping_rows),
        "matched_records": len(matched_rows),
        "split_records_missing_image_count": len(missing_images),
        "images_without_split_record_count": len(images_without_split),
        "split_records_missing_metadata_count": len(missing_metadata),
        "split_records_missing_grouping_count": len(missing_grouping),
        "metadata_missing_values": missing_values,
        "label_distribution": dict(labels),
        "split_distribution": dict(split_counts),
        "duplicate_hash_groups_crossing_existing_splits": crossing_duplicate_groups,
        "patient_id_available": any("patient" in header.casefold() for header in metadata_headers),
        "split_independence": "lesion-disjoint according to checked-in split.csv; patient-level separation cannot be checked because patient IDs are absent",
        "clinical_metadata_fields": metadata_headers,
    }
    processed = DATA / "processed" / "HAM10000" / "ISIC2018-Task3"
    processed.mkdir(parents=True, exist_ok=True)
    table = processed / "matched_images.csv"
    output_headers = [*split_headers, *[f"metadata_{key}" for key in metadata_headers if key != "image"], "diagnosis_confirm_type", "image_path", "image_sha256"]
    with table.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(matched_rows)
    report_dir = DATA / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "ham10000_quality.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("image_count", "valid_images", "split_records", "metadata_records", "grouping_records", "matched_records", "label_distribution", "split_distribution", "duplicate_hash_groups_crossing_existing_splits", "patient_id_available")}, indent=2))
    print(f"Aggregate quality report: {report_path}")
    print(f"Matched table (Git-ignored): {table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
