# Brain clinical experiment comparison

This is an experiment-only result on the same 66-patient held-out cohort. It is not evidence of clinical usefulness.

| Model | Feature set | CV macro-F1 mean ± SD | Holdout macro-F1 | Accuracy | Balanced accuracy |
|---|---|---:|---:|---:|---:|
| A | Age, Sex, SITE | 0.483 ± 0.053 | 0.540 | 0.576 | 0.549 |
| B | A + current structured C/F symptoms | 0.459 ± 0.052 | 0.503 | 0.530 | 0.522 |
| C | B + leakage-screened structured radiology | 0.448 ± 0.054 | 0.407 | 0.455 | 0.414 |

Usable cohort: 327 for each model; 261 train / 66 test; zero patient overlap. At least one extracted symptom is observed in 247 records; at least one safe radiology feature in 106 records.

Recommendation: retain Age, Sex and Site as the experimental baseline. Do not expose the free-text-derived symptom or radiology features as predictive inputs yet: both expanded models underperformed A, the symptom extraction is rule-based and sparse, and radiology text has substantial leakage/ambiguity. A reviewed structured prospective form could be evaluated separately.
