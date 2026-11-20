# Skin Cancer Module

This folder contains the Skin Cancer branch backend, its trained model artifacts, PAD-UFES-20 workflows, processing scripts, manifests, metrics, and module-specific dependencies. The shared Next.js frontend remains in the repository-level `frontend/` directory; the Skin branch integration updates its shared analysis pages and services.

## Structure

```text
Skin_cancer/
  backend/
    api.py
    cancer_registry/
    models/
    preprocessing/
    scripts/
    training/
    data/manifests/
    results/
    requirements.txt
```

## Run the Skin API from the repository root

```powershell
python -m pip install -r Skin_cancer/backend/requirements.txt
python -m uvicorn Skin_cancer.backend.api:app --host 0.0.0.0 --port 8000
```

Raw datasets are not bundled. Follow the backend scripts and manifests to provide authorized source data before running dataset preparation or training workflows.

This is an academic research prototype and is not for clinical diagnosis or treatment decisions.
