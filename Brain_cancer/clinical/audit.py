"""Write aggregate-only audit for the locally supplied IPD-Brain clinical CSV."""

from __future__ import annotations

import json
from pathlib import Path

from Brain_cancer.clinical.pipeline import DEFAULT_DATASET, audit_dataset


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "brain_clinical_dataset_audit.json"


def main() -> None:
    _frame, audit = audit_dataset(DEFAULT_DATASET)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "dataset": audit["path"],
        "records": audit["record_count"],
        "unique_patient_groups": audit["unique_patient_groups"],
        "subtypes": audit["subtype_counts"],
        "diagnosis_conflicts": audit["diagnosis_target_quality"]["explicit_conflict_records"],
        "audit_output": str(OUTPUT.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
