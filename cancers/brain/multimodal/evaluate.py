"""Print the held-out patient-level metrics produced by the training run."""

import json
from pathlib import Path

from cancers.brain.multimodal.config import REPORT_DIR


def main() -> None:
    report = REPORT_DIR / "brain_idh_multimodal_metrics.json"
    if not report.is_file():
        raise FileNotFoundError(f"No saved evaluation report at {report}; train the models first.")
    result = json.loads(report.read_text(encoding="utf-8"))
    print(f"Held-out patient test set: {result['split_counts']['test']} patients")
    for name, metrics in result["test_results"].items():
        print(f"{name:10s} macro-F1={metrics['macro_f1']:.4f} accuracy={metrics['accuracy']:.4f} "
              f"balanced-accuracy={metrics['balanced_accuracy']:.4f} ROC-AUC={metrics['roc_auc_mutated_positive']}")
    print(f"Full metrics: {report}")


if __name__ == "__main__": main()
