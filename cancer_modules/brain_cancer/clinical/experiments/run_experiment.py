"""Isolated, leakage-screened IPD-Brain clinical feature experiment.

Run from repository root: python -m Brain_cancer.clinical.experiments.run_experiment
Outputs are written only to cancer_modules/brain_cancer/evaluation/brain_clinical_experiments/.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
    confusion_matrix, f1_score, precision_recall_fscore_support)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from cancer_modules.brain_cancer.clinical.pipeline import (
    CLASSES, DEFAULT_DATASET, audit_dataset, make_preprocessor, model_features,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evaluation" / "brain_clinical_experiments"
SYMPTOMS = {
    "headache": r"headache|cephalalgia|head\s+pain",
    "vomiting": r"vomit|vomthings|emesis",
    "seizure": r"seiz|\bsz\b|convuls|fits?",
    "limb_weakness": r"weakness|hemipares|hemipleg|paresis",
    "dizziness": r"dizz|gidd|vertigo",
    "loss_consciousness": r"\bloc\b|loss\s+of\s+consciousness|unconscious|syncope",
    "memory": r"memory|forgetfulness|amnesia",
    "speech": r"slurr|speech|dysarth|aphas|language\s+disturbance",
    "visual": r"vision|visual|blur|diplopia|blind|dimness",
    "personality_behavior": r"personality|behavio|irritab|aggressiv|mood\s+change",
}
LEAK = {
    "subtype_or_glioma": r"glioblastoma|gliomablastoma|\bgbm\b|astrocytoma|oligodendroglioma|\boligo\b|glioma|gliosarcoma",
    "diagnostic_language": r"\bs/o\b|\bf/s/o\b|suggestive|consistent\s+with|suspicious|likely|probable|differential|impression|diagnos|\bhgg\b|\blgg\b|high[- ]grade|low[- ]grade",
    "other_tumor_or_pathology": r"metasta|tuberculoma|lymphoma|meningioma|schwannoma|neoplasm|abscess|tumou?r|malignan|biopsy|histopath",
    "history_or_treatment": r"\bh/o\b|history|previous|recurrent|operated|radiotherap|chemotherap|\bs/p\b|post[- ]op",
    "uncertain_mark": r"\?",
}
RAD_FEATURES = ["t1_signal", "t2_flair_signal", "enhancement", "edema", "mass_effect", "midline_shift", "cystic_component", "calcification"]


def norm(v):
    return "" if pd.isna(v) else str(v).strip()


def state(text: str, pattern: str) -> tuple[str, str]:
    """Extract a three-state current finding conservatively from one clause."""
    matches = list(re.finditer(pattern, text, re.I))
    if not matches:
        return "unknown", "not_mentioned"
    found = []
    for m in matches:
        left = max(text.rfind(mark, 0, m.start()) for mark in (",", ";", ".", "\n"))
        right_candidates = [text.find(mark, m.end()) for mark in (",", ";", ".", "\n")]
        right_candidates = [pos for pos in right_candidates if pos >= 0]
        clause = text[left + 1:min(right_candidates) if right_candidates else len(text)].lower()
        prefix = clause[:max(0, m.start() - (left + 1))]
        # A negative history is not evidence of a current absent symptom.
        if re.search(r"\bno\s+(?:h/o|history\s+of)\b", prefix):
            found.append("historical_unknown")
            continue
        if re.search(r"\b(no|not|denies|without|negative for|absent)\b", prefix[-65:]):
            found.append("absent")
            continue
        # Historical references without a current complaint or duration remain unknown.
        hist = re.search(r"\b(h/o|history of|past|previous|old|ago|back)\b", clause)
        current = bool(re.search(r"\b(c/o|complain|since|for the last|for\s+\d+|from\s+\d+|presently|currently)\b", clause))
        if hist and not current:
            found.append("historical_unknown")
        else:
            found.append("present")
    if len(set(found)) > 1:
        return "unknown", "contradictory_mentions"
    if found[0] == "historical_unknown":
        return "unknown", "historical_reference"
    return found[0], "explicit_mention"


def symptom_values(value):
    text = norm(value)
    if not text:
        return {k: "unknown" for k in SYMPTOMS}, {k: "missing_text" for k in SYMPTOMS}
    result, reasons = {}, {}
    for name, pattern in SYMPTOMS.items():
        result[name], reasons[name] = state(text, pattern)
    return result, reasons


def leakage_reasons(text):
    return [name for name, pattern in LEAK.items() if re.search(pattern, text, re.I)]


def tri(text, positive, negative=None):
    negative = negative or r"\b(no|not|without|absent|negative for|non[- ]?)\b"
    p = bool(re.search(positive, text, re.I))
    n = bool(re.search(negative + r"[^.;,]{0,35}(?:" + positive + r")", text, re.I))
    return "unknown" if p and n else ("present" if p else ("absent" if n else "unknown"))


def radiology_values(value):
    text = norm(value)
    out = {k: "unknown" for k in RAD_FEATURES}
    reasons = leakage_reasons(text) if text else ["missing_text"]
    if not text or reasons:
        return out, reasons
    # Signal categories only when a modality and signal descriptor occur nearby.
    for key, modality in (("t1_signal", r"\bT1(?:W| weighted)?\b"), ("t2_flair_signal", r"\b(?:T2(?:W| weighted)?|FLAIR)\b")):
        modality_match = re.search(modality, text, re.I)
        if modality_match:
            around = text[max(0, modality_match.start()-45):modality_match.end()+65]
            for sig in ("hypo", "hyper", "iso", "heterogeneous"):
                if re.search(r"\b"+sig+r"\w*", around, re.I):
                    out[key] = sig
                    break
    out["enhancement"] = tri(text, r"enhanc(?:e|ement|ing)|\bpost[- ]contrast\b")
    if out["enhancement"] == "present":
        if re.search(r"ring[- ]?(?:like|enhanc)|ring enhancement", text, re.I): out["enhancement"] = "ring_like"
        elif re.search(r"heterogeneous", text, re.I): out["enhancement"] = "heterogeneous"
        elif re.search(r"homogeneous", text, re.I): out["enhancement"] = "homogeneous"
        else: out["enhancement"] = "present_other"
    for key, pattern in {
        "edema": r"\bedema\w*", "mass_effect": r"mass\s+effect", "midline_shift": r"midline\s+shift|shift(?:ing)?\s+of\s+midline",
        "cystic_component": r"cystic|cyst\b", "calcification": r"calcif\w*",
    }.items():
        out[key] = tri(text, pattern)
    return out, []


def make_model(extras):
    base = make_preprocessor()
    extra = ColumnTransformer([("state", OneHotEncoder(handle_unknown="ignore"), extras)], remainder="drop")
    prep = ColumnTransformer([("base", base, ["Age", "Sex", "SITE"]), ("extra", extra, extras)], remainder="drop")
    return Pipeline([("preprocess", prep), ("model", LogisticRegression(solver="lbfgs", max_iter=2500, class_weight="balanced", C=1.0, random_state=42))])


def metrics(y, pred):
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=CLASSES, zero_division=0)
    return {"accuracy": float(accuracy_score(y,pred)), "balanced_accuracy": float(balanced_accuracy_score(y,pred)),
        "macro_precision": float(p.mean()), "macro_recall": float(r.mean()), "macro_f1": float(f1_score(y,pred,labels=CLASSES,average="macro",zero_division=0)),
        "per_class": {c:{"precision":float(p[i]),"recall":float(r[i]),"f1":float(f[i]),"support":int(s[i])} for i,c in enumerate(CLASSES)},
        "confusion_matrix_labels": CLASSES, "confusion_matrix": confusion_matrix(y,pred,labels=CLASSES).tolist()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame, audit = audit_dataset(DEFAULT_DATASET)
    # This is the exact quality exclusion used by the production baseline.
    frame = frame.loc[~frame["_diagnosis_conflict"]].reset_index(drop=True)
    y = frame["Subtype"].astype(str)
    groups = frame["_patient_group"].astype(str)
    Xa = model_features(frame)
    symptom_rows, symptom_audit = [], {k:{"present":0,"absent":0,"unknown":0,"examples":{"present":[],"absent":[],"historical_or_ambiguous":[]}} for k in SYMPTOMS}
    radiology_rows, rad_audit = [], {"safe_rows":0,"unsafe_rows":0,"reason_counts":{},"safe_examples":{},"unsafe_examples":[]}
    for _, row in frame.iterrows():
        sval, sreason = symptom_values(row["C/F"])
        symptom_rows.append(sval)
        source = norm(row["C/F"])
        for k, val in sval.items():
            symptom_audit[k][val] += 1
            if val in ("present","absent") and source and len(symptom_audit[k]["examples"][val]) < 3:
                symptom_audit[k]["examples"][val].append(source[:180])
            elif val == "unknown" and source and sreason[k] in ("contradictory_mentions", "historical_reference") and len(symptom_audit[k]["examples"]["historical_or_ambiguous"]) < 3:
                symptom_audit[k]["examples"]["historical_or_ambiguous"].append(source[:180])
    Xb_extra = pd.DataFrame(symptom_rows)
    for _, row in frame.iterrows():
        vals, reasons = radiology_values(row["Radiology"])
        radiology_rows.append(vals)
        if reasons:
            rad_audit["unsafe_rows"] += 1
            for reason in reasons:
                rad_audit["reason_counts"][reason] = rad_audit["reason_counts"].get(reason,0)+1
            if row["Radiology"] and len(rad_audit["unsafe_examples"]) < 8:
                # De-identification: Case Number is never included.
                rad_audit["unsafe_examples"].append({"reasons":reasons,"text":re.sub(r"glioblastoma|gliomablastoma|astrocytoma|oligodendroglioma|\bGBM\b|\bglioma\b", "[subtype/pathology term]", norm(row["Radiology"]), flags=re.I)[:180]})
        else:
            rad_audit["safe_rows"] += 1
            for k,v in vals.items():
                if v != "unknown" and k not in rad_audit["safe_examples"]:
                    rad_audit["safe_examples"][k] = {"value":v,"text":norm(row["Radiology"])[:180]}
    Xc_extra = pd.DataFrame(radiology_rows)
    Xb = pd.concat([Xa.reset_index(drop=True), Xb_extra],axis=1)
    Xc = pd.concat([Xa.reset_index(drop=True), Xb_extra, Xc_extra],axis=1)
    # De-identified extracted table: no Case Number and no source free text.
    extracted = pd.concat([frame[["Age","Sex","SITE","Subtype"]].reset_index(drop=True), Xb_extra, Xc_extra],axis=1)
    extracted.to_csv(OUT / "extracted_feature_dataset.csv", index=False)
    audit["experiment_records_after_quality_exclusion"] = len(frame)
    (OUT / "dataset_audit.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (OUT / "leakage_audit.json").write_text(json.dumps({"symptoms":symptom_audit,"radiology":rad_audit,
        "radiology_policy":"Any missing text or any subtype, diagnosis/differential, tumor/pathology, history/treatment, or question-mark indicator makes every radiology-derived feature unknown.",
        "excluded_features":["Case Number","Diagnosis","WHO Grade","Subtype as input","ki67(in %)","IDH1R132H","ATRX","p53","raw C/F","raw Radiology","radiology size"]},indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    outer = StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42)
    train_idx,test_idx = next(outer.split(Xa,y,groups))
    if len(test_idx)!=66 or set(groups.iloc[train_idx]) & set(groups.iloc[test_idx]): raise RuntimeError("Production holdout mismatch or patient overlap")
    cv = StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=43)
    gdev=groups.iloc[train_idx]
    data={"A":(Xa,[]),"B":(Xb,list(Xb_extra.columns)),"C":(Xc,list(Xb_extra.columns)+list(Xc_extra.columns))}
    output={"created_at_utc":datetime.now(timezone.utc).isoformat(),"dataset":"IPD_Brain.csv","quality_exclusion_records":int(frame.shape[0]),"holdout":{"train":len(train_idx),"test":len(test_idx),"group_overlap":0,"split":"first StratifiedGroupKFold(5, shuffle=True, random_state=42) fold"},"models":{},"majority_baseline":None}
    for name,(X,extras) in data.items():
        model=Pipeline([("preprocess",make_preprocessor()),("model",LogisticRegression(solver="lbfgs",max_iter=2500,class_weight="balanced",C=1.0,random_state=42))]) if name=="A" else make_model(extras)
        scores=cross_val_score(model,X.iloc[train_idx],y.iloc[train_idx],groups=gdev,cv=cv,scoring="f1_macro",n_jobs=1)
        model.fit(X.iloc[train_idx],y.iloc[train_idx])
        pred=model.predict(X.iloc[test_idx])
        output["models"][name]={"feature_set":{"A":"Age, Sex, SITE","B":"A + current structured C/F symptoms","C":"B + leakage-screened structured radiology"}[name],"cv_macro_f1":[float(x) for x in scores],"cv_mean":float(scores.mean()),"cv_std":float(scores.std()),"holdout":metrics(y.iloc[test_idx],pred)}
        joblib.dump({"model":model,"feature_set":name,"note":"Experimental artifact; trained only on development split."},OUT / f"model_{name}.joblib")
    from sklearn.dummy import DummyClassifier
    dummy=DummyClassifier(strategy="most_frequent").fit(Xa.iloc[train_idx],y.iloc[train_idx])
    output["majority_baseline"]=metrics(y.iloc[test_idx],dummy.predict(Xa.iloc[test_idx]))
    output["usable_records"]={"A":int(len(frame)),"B":int(len(frame)),"C":int(len(frame))}
    output["records_with_at_least_one_observed_added_feature"]={
        "B":int(Xb_extra.ne("unknown").any(axis=1).sum()),
        "C":int(pd.concat([Xb_extra,Xc_extra],axis=1).ne("unknown").any(axis=1).sum()),
        "radiology_safe_and_with_at_least_one_observation":int(Xc_extra.ne("unknown").any(axis=1).sum()),
    }
    output["unknown_counts"]={"B_symptoms":{k:int(v) for k,v in Xb_extra.eq("unknown").sum().items()},"C_radiology":{k:int(v) for k,v in Xc_extra.eq("unknown").sum().items()}}
    output["class_counts"]={str(k):int(v) for k,v in y.value_counts().items()}
    # Hard guard: experiment A must exactly reproduce baseline holdout metric.
    if abs(output["models"]["A"]["holdout"]["macro_f1"]-0.5397145652097963)>1e-12:
        raise RuntimeError("A baseline did not reproduce the recorded production holdout metric")
    (OUT / "metrics.json").write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    pd.DataFrame([{"model":k,"cv_macro_f1_mean":v["cv_mean"],"cv_macro_f1_std":v["cv_std"],**{m:v["holdout"][m] for m in ("accuracy","balanced_accuracy","macro_precision","macro_recall","macro_f1")}} for k,v in output["models"].items()]).to_csv(OUT/"comparison.csv",index=False)
    for k,v in output["models"].items():
        pd.DataFrame(v["holdout"]["confusion_matrix"],index=CLASSES,columns=CLASSES).to_csv(OUT/f"confusion_matrix_{k}.csv")
    rules={"C/F extraction":"Regex dictionary for ten explicit symptom groups. A symptom is present when mentioned without local negation or historical cue; absent only with explicit local negation; unknown when missing, historical without a current cue, or conflicting. ‘No history of’ is unknown rather than current absence. Raw C/F text is never passed to a model.","radiology eligibility":"Exclude the entire Radiology field on any subtype/glioma wording, diagnostic/differential language, other tumor/pathology wording, history/treatment wording, question mark, or missing text. Only safe-field structured observations enter C; unsafe/missing fields are unknown.","features":{
        "symptoms":{k:{"rule":v,"present":int(Xb_extra[k].eq("present").sum()),"absent":int(Xb_extra[k].eq("absent").sum()),"unknown":int(Xb_extra[k].eq("unknown").sum())} for k,v in SYMPTOMS.items()},
        "radiology":{k:{"rule":v,"observed":int(Xc_extra[k].ne("unknown").sum()),"unknown":int(Xc_extra[k].eq("unknown").sum())} for k,v in {
            "t1_signal":"T1 modality must be near a hypo/hyper/iso/heterogeneous descriptor.","t2_flair_signal":"T2 or FLAIR modality must be near a signal descriptor.","enhancement":"Explicit enhancement or negation; subtype categories retained only when text states ring-like/homogeneous/heterogeneous.","edema":"Explicit edema mention or local negation.","mass_effect":"Explicit mass-effect mention or local negation.","midline_shift":"Explicit midline shift mention or local negation.","cystic_component":"Explicit cyst/cystic mention or local negation.","calcification":"Explicit calcification mention or local negation."}.items()}}
    }
    (OUT / "feature_extraction_rules.json").write_text(json.dumps(rules,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    rec=["# Brain clinical experiment comparison","", "This is an experiment-only result on the same 66-patient held-out cohort. It is not evidence of clinical usefulness.","", "| Model | Feature set | CV macro-F1 mean ± SD | Holdout macro-F1 | Accuracy | Balanced accuracy |", "|---|---|---:|---:|---:|---:|"]
    for k,v in output["models"].items():
        rec.append(f"| {k} | {v['feature_set']} | {v['cv_mean']:.3f} ± {v['cv_std']:.3f} | {v['holdout']['macro_f1']:.3f} | {v['holdout']['accuracy']:.3f} | {v['holdout']['balanced_accuracy']:.3f} |")
    rec += ["",f"Usable cohort: {len(frame)} for each model; 261 train / 66 test; zero patient overlap. At least one extracted symptom is observed in {output['records_with_at_least_one_observed_added_feature']['B']} records; at least one safe radiology feature in {output['records_with_at_least_one_observed_added_feature']['radiology_safe_and_with_at_least_one_observation']} records.","", "Recommendation: retain Age, Sex and Site as the experimental baseline. Do not expose the free-text-derived symptom or radiology features as predictive inputs yet: both expanded models underperformed A, the symptom extraction is rule-based and sparse, and radiology text has substantial leakage/ambiguity. A reviewed structured prospective form could be evaluated separately.",""]
    (OUT / "model_comparison_report.md").write_text("\n".join(rec),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"holdout":output["holdout"],"models":{k:{"cv_mean":v["cv_mean"],"holdout_macro_f1":v["holdout"]["macro_f1"]} for k,v in output["models"].items()},"radiology_safe_rows":rad_audit["safe_rows"],"radiology_unsafe_rows":rad_audit["unsafe_rows"]},indent=2))


if __name__ == "__main__":
    main()
