"""Prepare a small, attributable skin/OOD research set from approved sources.

Raw source files and extracted images stay under ignored backend/data paths.
Open Images samples are filtered to individual CC BY 2.0 image licenses and
human-verified animal/object labels before any pixels are downloaded.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from PIL import Image
from PIL import ImageDraw, ImageFont
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "skin_ood"
OPEN_IMAGES = RAW / "open_images_v5_validation"
PROCESSED = ROOT / "data" / "processed" / "skin_ood"
MANIFEST = ROOT / "data" / "manifests" / "skin-ood-v1.json"
LICENSE = "https://creativecommons.org/licenses/by/2.0/"
SEED = 4032026
PER_GROUP = 600
CLASSES = {
    "animal": {"Dog", "Cat", "Bird", "Fish", "Horse", "Cattle", "Cow", "Animal",
               "Carnivore", "Insect", "Reptile", "Mammal", "Rabbit", "Hamster"},
    "object": {"Car", "Vehicle", "Bicycle", "Airplane", "Train", "Bottle", "Book",
               "Computer monitor", "Mobile phone", "Chair", "Table", "Clock", "Computer keyboard",
               "Computer mouse", "Cupboard", "Sofa bed", "Television", "Microwave oven",
               "Laptop", "Camera", "Toy", "Musical instrument"},
}


def deterministic_split(image_id: str) -> str:
    value = int(hashlib.sha256((str(SEED) + image_id).encode()).hexdigest()[:8], 16) % 100
    return "train" if value < 70 else "validation" if value < 85 else "test"


def download(url: str, destination: Path) -> bytes:
    if destination.is_file():
        return destination.read_bytes()
    request = Request(url, headers={"User-Agent": "WeCure-Skin-OOD-Research/1.0"})
    last_error = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            return payload
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"Download failed: {url}: {last_error}")


def prepare_open_images() -> list[dict]:
    labels = pd.read_csv(OPEN_IMAGES / "validation-annotations-human-imagelabels-boxable.csv")
    names = pd.read_csv(OPEN_IMAGES / "class-descriptions-boxable.csv", header=None,
                        names=["LabelName", "DisplayName"])
    image_info = pd.read_csv(OPEN_IMAGES / "validation-images-with-rotation.csv")
    verified = labels[(labels.Confidence == 1) &
                      labels.Source.isin(["verification", "crowdsource-verification"])].merge(names, on="LabelName")
    verified = verified[verified.DisplayName.isin(set.union(*CLASSES.values()))]

    rows = []
    used_ids: set[str] = set()
    for group, group_classes in CLASSES.items():
        candidates = (verified[verified.DisplayName.isin(group_classes)]
                      .drop_duplicates("ImageID").merge(image_info, on="ImageID"))
        candidates = candidates[(candidates.License == LICENSE) &
                                candidates.OriginalLandingURL.notna() &
                                candidates.Author.notna() &
                                candidates.Thumbnail300KURL.notna() &
                                ~candidates.ImageID.isin(used_ids)]
        candidates = candidates.sort_values("ImageID").to_dict("records")
        rng = random.Random(SEED + (group == "object"))
        rng.shuffle(candidates)
        selected = candidates[:PER_GROUP]
        used_ids.update(row["ImageID"] for row in selected)
        rows.extend((group, row) for row in selected)

    def materialize(sample: tuple[str, dict]) -> dict:
        group, source = sample
        image_id = source["ImageID"]
        relpath = Path("open_images") / group / deterministic_split(image_id) / f"{image_id}.jpg"
        path = PROCESSED / relpath
        if path.is_file():
            return {"source": "Open Images V5 validation", "imageId": image_id,
                    "group": group, "split": deterministic_split(image_id),
                    "status": "accepted", "path": relpath.as_posix(),
                    "license": source["License"], "author": source["Author"],
                    "authorProfileUrl": source.get("AuthorProfileURL"),
                    "sourceUrl": source["OriginalLandingURL"],
                    "imageUrl": source["Thumbnail300KURL"], "title": source.get("Title"),
                    "label": source.get("DisplayName")}
        try:
            content = download(source["Thumbnail300KURL"], path)
            image = Image.open(io.BytesIO(content)).convert("RGB")
            rotation = source.get("Rotation")
            if pd.notna(rotation) and int(rotation) in (90, 180, 270):
                image = image.rotate(int(rotation), expand=True)
            image.save(path, format="JPEG", quality=95)
        except Exception as exc:  # Keep each rejected source visible in the manifest.
            return {"source": "Open Images V5 validation", "imageId": image_id,
                    "group": group, "split": deterministic_split(image_id),
                    "status": "rejected", "reason": str(exc),
                    "license": source.get("License"), "author": source.get("Author"),
                    "sourceUrl": source.get("OriginalLandingURL")}
        return {"source": "Open Images V5 validation", "imageId": image_id,
                "group": group, "split": deterministic_split(image_id),
                "status": "accepted", "path": relpath.as_posix(),
                "license": source["License"], "author": source["Author"],
                "authorProfileUrl": source.get("AuthorProfileURL"),
                "sourceUrl": source["OriginalLandingURL"],
                "imageUrl": source["Thumbnail300KURL"], "title": source.get("Title"),
                "label": source.get("DisplayName")}

    records = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(materialize, sample) for sample in rows]
        for count, future in enumerate(as_completed(futures), start=1):
            records.append(future.result())
            if count % 100 == 0 or count == len(futures):
                print(f"Curated {count}/{len(futures)} Open Images samples", flush=True)
    return records


def prepare_symage() -> dict:
    source = RAW / "symage_synthetic_us_forms_preview"
    root = PROCESSED / "symage_forms"
    counts = defaultdict(int)
    records = []
    for source_split in ("train", "test"):
        source_file = source / "data" / f"{source_split}-00000-of-00001.parquet"
        rows = pq.read_table(source_file, columns=["id", "identity_id", "form_id", "page", "image"]).to_pylist()
        for row in rows:
            payload = row["image"]["bytes"]
            split = "train" if source_split == "train" else "test"
            path = root / split / f"{row['id']}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            Image.open(io.BytesIO(payload)).verify()
            counts[split] += 1
            records.append({"id": row["id"], "identityId": row["identity_id"],
                            "formId": row["form_id"], "page": row["page"],
                            "path": path.relative_to(PROCESSED).as_posix(),
                            "split": split, "label": "document_form"})
    return {"name": "SymageDocs Synthetic US Forms Preview", "datasetUrl":
            "https://huggingface.co/datasets/Symage/synthetic-us-forms-preview",
            "license": "CC-BY-4.0", "attribution": "SymageDocs; https://symagedocs.ai/",
            "sourceFiles": {p.relative_to(source).as_posix(): p.stat().st_size
                            for p in source.rglob("*") if p.is_file()},
            "counts": dict(counts), "records": records, "status": "processed"}


def prepare_synthetic_screenshots() -> dict:
    """Generate copyright-clean website-like screenshots with template-held-out splits."""
    root = PROCESSED / "synthetic_screenshots"
    rng = random.Random(SEED)
    templates = {
        0: ("#f4f7fb", "#135da8", "#ffffff"),
        1: ("#f8f5ef", "#7d332b", "#fffdfa"),
        2: ("#f0f6f2", "#287258", "#ffffff"),
        3: ("#f4f1f8", "#69479b", "#ffffff"),
        4: ("#eff4f7", "#145b66", "#ffffff"),
        5: ("#f8f3f2", "#a14f27", "#ffffff"),
    }
    labels = ["Community", "Library", "Travel", "Gardening", "Music", "Food", "Local news", "Learning"]
    records = []
    for template, (background, accent, card) in templates.items():
        split = "train" if template < 4 else ("validation" if template == 4 else "test")
        for index in range(100):
            image_id = f"synthetic-web-{template}-{index:03d}"
            image = Image.new("RGB", (640, 480), background)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 640, 48), fill=accent)
            draw.text((22, 16), rng.choice(labels) + "  |  Home    Topics    About", fill="white")
            draw.rectangle((22, 70, 618, 137), fill=card)
            draw.text((38, 84), rng.choice(labels) + " — Updates and information", fill="#202b38")
            draw.text((38, 108), "A generated page layout for visual scope testing.", fill="#596674")
            for column in range(3):
                x = 22 + column * 199
                top = 158 + rng.randrange(-8, 9)
                draw.rounded_rectangle((x, top, x + 184, 430), radius=6, fill=card,
                                       outline="#d4dce3", width=2)
                # Generated abstract thumbnail block, deliberately not a medical or web asset.
                color = "#" + "".join(rng.choice("6789abcde") for _ in range(6))
                draw.rectangle((x + 12, top + 14, x + 172, top + 91), fill=color)
                draw.text((x + 12, top + 106), rng.choice(labels), fill="#202b38")
                for line in range(3):
                    line_y = top + 132 + line * 22
                    width = rng.randint(74, 150)
                    draw.rounded_rectangle((x + 12, line_y, x + 12 + width, line_y + 7),
                                           radius=3, fill="#b8c2cc")
                draw.rounded_rectangle((x + 12, top + 224, x + 87, top + 248),
                                       radius=5, fill=accent)
            path = root / split / f"{image_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path, format="PNG")
            records.append({"imageId": image_id, "path": path.relative_to(PROCESSED).as_posix(),
                            "split": split, "templateId": template, "label": "website_screenshot",
                            "license": "CC0-1.0; generated for this project"})
    return {"name": "WeCure synthetic website screenshot fixtures", "license": "CC0-1.0",
            "source": "Generated locally by backend/training/prepare_skin_ood_data.py",
            "splitMethod": "template-disjoint (templates 0-3 train, 4 validation, 5 test)",
            "counts": {split: sum(row["split"] == split for row in records)
                       for split in ("train", "validation", "test")},
            "records": records}


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    records = prepare_open_images()
    manifest = {
        "datasetId": "skin-ood-v1",
        "createdBy": "backend/training/prepare_skin_ood_data.py",
        "randomSeed": SEED,
        "status": "curated-source-samples",
        "openImages": {"name": "Open Images V5 validation", "datasetUrl":
                       "https://storage.googleapis.com/openimages/web/download_v7.html",
                       "sourceFilesUrl": {
                           "labels": "https://storage.googleapis.com/openimages/v5/validation-annotations-human-imagelabels-boxable.csv",
                           "imageInfo": "https://storage.googleapis.com/openimages/2018_04/validation/validation-images-with-rotation.csv",
                           "classNames": "https://storage.googleapis.com/openimages/v5/class-descriptions-boxable.csv"},
                       "annotationFiles": {
                           p.name: p.stat().st_size for p in OPEN_IMAGES.iterdir() if p.is_file()},
                       "licenseFilter": LICENSE,
                       "labelFilter": "human-verified positive image-level labels only",
                       "selectedPerGroup": PER_GROUP,
                       "records": records},
        "symageForms": prepare_symage(),
        "syntheticScreenshots": prepare_synthetic_screenshots(),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    counts = defaultdict(int)
    for row in records:
        counts[(row["group"], row["split"], row["status"])] += 1
    print(json.dumps({"openImagesCounts": {"/".join(k): v for k, v in counts.items()},
                      "manifest": str(MANIFEST)}, indent=2))


if __name__ == "__main__":
    main()
