# Brain Cancer Module

Brain-specific MRI, clinical, and multimodal backend code and evaluation artifacts are grouped here. The shared Next.js routes, pages, and UI components remain in the repository-level `frontend/` directory.

```text
Brain_cancer/
  clinical/       Clinical subtype pipeline, API, training, and saved pipeline artifact
  image/          MRI preprocessing and inference service
  multimodal/     Image plus clinical API/service
  evaluation/     Clinical audit and evaluation reports
  data/           Local-only clinical CSV goes here (not included)
  weights/        Original MRI checkpoint goes here (not included)
```

From the repository root, start the API with:

```powershell
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

The MRI route expects `Brain_cancer/weights/best_model.pth`; the clinical route expects `Brain_cancer/data/brain cancer/IPD_Brain.csv`. Those inputs are not included, so the corresponding runtime predictions require locally supplied files.

Brain routes: `/brain-image`, `/brain-clinical`, and `/brain-multimodal`. Outputs are research results, not medical diagnoses.
