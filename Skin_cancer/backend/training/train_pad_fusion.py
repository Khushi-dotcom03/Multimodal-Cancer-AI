"""Train/evaluate six-class PAD-UFES-20 image+clinical fusion, grouped by patient."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, f1_score
from sklearn.utils.class_weight import compute_class_weight
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.models.pad_fusion_model import PADFusionModel
from backend.preprocessing.pad_clinical_preprocessing import CLINICAL_FEATURES, create_clinical_preprocessor

DATA = ROOT / "backend/data/processed/PAD-UFES-20/v1/matched_images.csv"
IMAGE_ROOT = ROOT / "backend/data/extracted/PAD-UFES-20/v1/images"
OUT = ROOT / "backend/models/pad_ufes20/pad_fusion_best.pth"
RESULTS = ROOT / "backend/results/pad_ufes20/fusion_metrics.json"
CLASSES = ["ACK", "BCC", "MEL", "NEV", "SCC", "SEK"]
SEED = 42
BATCH = 32
EPOCHS = 12
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TRAIN_TF = T.Compose([T.Resize((224, 224)), T.RandomHorizontalFlip(), T.RandomRotation(12), T.ColorJitter(0.08, 0.08, 0.08), T.ToTensor(), T.Normalize([.485,.456,.406],[.229,.224,.225])])
EVAL_TF = T.Compose([T.Resize((224, 224)), T.ToTensor(), T.Normalize([.485,.456,.406],[.229,.224,.225])])


class Paired(Dataset):
    def __init__(self, frame, features, labels, training):
        self.frame, self.features, self.labels = frame.reset_index(drop=True), features, labels
        self.transform = TRAIN_TF if training else EVAL_TF

    def __len__(self): return len(self.frame)

    def __getitem__(self, i):
        row = self.frame.iloc[i]
        path = IMAGE_ROOT / Path(row.image_path.replace("\\", "/"))
        with Image.open(path) as image:
            image = image.convert("RGB")
            return self.transform(image), torch.tensor(self.features[i], dtype=torch.float32), torch.tensor(self.labels[i], dtype=torch.long)


def evaluate(model, loader):
    model.eval(); targets=[]; predictions=[]
    with torch.inference_mode():
        for image, clinical, y in loader:
            logits = model(image.to(DEVICE), clinical.to(DEVICE))
            predictions.extend(logits.argmax(1).cpu().tolist()); targets.extend(y.tolist())
    return np.asarray(targets), np.asarray(predictions)


def main():
    if DEVICE.type == "cpu":
        torch.set_num_threads(4)
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    frame = pd.read_csv(DATA, dtype={"lesion_id":"string"})
    need = set(CLINICAL_FEATURES + ["patient_id","lesion_id","patient_group","img_id","image_path","label","split"])
    if not need.issubset(frame.columns): raise ValueError(f"Missing fields: {sorted(need-set(frame.columns))}")
    if frame[["patient_id","lesion_id","img_id"]].isna().any().any(): raise ValueError("Null pairing identifier")
    if not frame.label.isin(CLASSES).all(): raise ValueError("Unexpected PAD target class")
    if not all((IMAGE_ROOT / Path(p.replace("\\","/"))).is_file() for p in frame.image_path): raise FileNotFoundError("A paired image is missing")
    # Ensure duplicate image rows map to the row's exact image ID + patient/lesion metadata.
    if frame.image_path.duplicated().any(): raise ValueError("Duplicate image paths in paired manifest")
    lesion = frame.groupby(["patient_group","lesion_id"], dropna=False)
    for col in CLINICAL_FEATURES + ["label","split","patient_id"]:
        if lesion[col].nunique(dropna=False).max() > 1: raise ValueError(f"Lesion-level mismatch in {col}")
    groups = {s:set(frame.loc[frame.split==s,"patient_group"]) for s in ("train","validation","test")}
    if any(groups[a]&groups[b] for a,b in (("train","validation"),("train","test"),("validation","test"))): raise ValueError("Patient leakage across splits")
    if any(set(frame.loc[frame.split==s,"label"]) != set(CLASSES) for s in groups): raise ValueError("A split is missing a PAD class")
    train, val, test = (frame[frame.split==s].reset_index(drop=True) for s in ("train","validation","test"))
    pre = create_clinical_preprocessor()
    xtr=pre.fit_transform(train[CLINICAL_FEATURES]).astype("float32")
    xv=pre.transform(val[CLINICAL_FEATURES]).astype("float32")
    xt=pre.transform(test[CLINICAL_FEATURES]).astype("float32")
    mapping={c:i for i,c in enumerate(CLASSES)}
    ytr=train.label.map(mapping).to_numpy(); yv=val.label.map(mapping).to_numpy(); yt=test.label.map(mapping).to_numpy()
    loaders=[DataLoader(Paired(df,x,y,aug),batch_size=BATCH,shuffle=aug,num_workers=0) for df,x,y,aug in ((train,xtr,ytr,True),(val,xv,yv,False),(test,xt,yt,False))]
    model=PADFusionModel(xtr.shape[1],6).to(DEVICE)
    # Preserve existing HAM weights and use only its ResNet feature extractor as initialization.
    ham=torch.load(ROOT/"backend/models/resnet18_best.pth",map_location="cpu",weights_only=True)
    compatible={k:v for k,v in ham.items() if k.startswith("conv1.") or k.startswith("bn1.") or k.startswith(("layer1.","layer2.","layer3.","layer4."))}
    missing, unexpected=model.image_encoder.load_state_dict(compatible,strict=False)
    if unexpected or any(not (key.startswith("fc.") or key in compatible) for key in missing): raise ValueError("HAM encoder initialization mismatch")
    criterion=nn.CrossEntropyLoss(weight=torch.tensor(compute_class_weight("balanced",classes=np.arange(6),y=ytr),dtype=torch.float32,device=DEVICE))
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-4)
    best=-1.; best_epoch=0; stale=0
    OUT.parent.mkdir(parents=True,exist_ok=True)
    for epoch in range(1,EPOCHS+1):
        model.train()
        for image,clinical,y in loaders[0]:
            image,clinical,y=image.to(DEVICE),clinical.to(DEVICE),y.to(DEVICE)
            optimizer.zero_grad(set_to_none=True); loss=criterion(model(image,clinical),y); loss.backward(); optimizer.step()
        vy,vp=evaluate(model,loaders[1]); score=f1_score(vy,vp,average="macro",zero_division=0)
        print(f"epoch={epoch} val_macro_f1={score:.4f}",flush=True)
        if score>best:
            best,best_epoch,stale=float(score),epoch,0
            torch.save({"model_state_dict":model.state_dict(),"classes":CLASSES,"clinical_features":CLINICAL_FEATURES,"input_features":xtr.shape[1],"best_epoch":epoch,"validation_macro_f1":best,"seed":SEED,"dataset":"PAD-UFES-20","split_unit":"patient_group","ham_encoder_initialization":True},OUT)
            joblib.dump(pre,OUT.with_name("pad_fusion_preprocessor.joblib"))
        else: stale+=1
        if stale>=5: break
    ckpt=torch.load(OUT,map_location=DEVICE,weights_only=True); model.load_state_dict(ckpt["model_state_dict"])
    truth,pred=evaluate(model,loaders[2])
    metrics={"dataset":"PAD-UFES-20","task":"paired six-class image+clinical fusion","image_rows":len(frame),"patient_lesion_pairs":int(frame[["patient_group","lesion_id"]].drop_duplicates().shape[0]),"patients_by_split":{s:len(groups[s]) for s in groups},"image_rows_by_split":{s:int((frame.split==s).sum()) for s in groups},"classes":CLASSES,"best_epoch":best_epoch,"validation_macro_f1":best,"test_accuracy":float(accuracy_score(truth,pred)),"test_balanced_accuracy":float(balanced_accuracy_score(truth,pred)),"test_macro_f1":float(f1_score(truth,pred,average="macro",zero_division=0)),"test_weighted_f1":float(f1_score(truth,pred,average="weighted",zero_division=0)),"test_classification_report":classification_report(truth,pred,labels=np.arange(6),target_names=CLASSES,output_dict=True,zero_division=0),"warning":"Research evaluation on a single patient-disjoint split; not clinical validation."}
    RESULTS.parent.mkdir(parents=True,exist_ok=True); RESULTS.write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics,indent=2),flush=True)


if __name__=="__main__": main()
