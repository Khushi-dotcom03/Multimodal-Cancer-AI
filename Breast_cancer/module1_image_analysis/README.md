# Module 1: BUSI Breast Ultrasound Image Classification

## Objective

Module 1 is an educational image-classification prototype for breast ultrasound images. It classifies an ultrasound image as **Normal**, **Benign**, or **Malignant**. It does not predict cancer stage or grade.

## Dataset

The image classifier uses the BUSI dataset, which contains **780 original images**:

| Class | Original images |
| --- | ---: |
| Normal | 133 |
| Benign | 437 |
| Malignant | 210 |
| **Total** | **780** |

Segmentation mask files are excluded from classification. The dataset is split into **70% training, 15% validation, and 15% testing**, stratified by class at the image level. These splits are not patient-level splits.

## Image classifier

The classifier uses **ImageNet-pretrained MobileNetV2 transfer learning** with a 224×224 image input and a three-class output: Normal, Benign, and Malignant.

Reported test accuracy is **82.91%**. Class-wise test metrics are:

| Class | Precision | Recall | F1 score |
| --- | ---: | ---: | ---: |
| Normal | 75% | 90% | 81.82% |
| Benign | 94.44% | 77.27% | 85% |
| Malignant | 71.79% | 90.32% | 80% |

These are reported results for this prototype and dataset split; they do not establish clinical performance.

## Invalid-image validator

An additional binary CNN validator was trained using BUSI ultrasound images as valid inputs and CIFAR-10 images as negative inputs. Its reported BUSI-versus-CIFAR-10 test accuracy was **100%**.

This result only describes separation on that test set. It does **not** prove that the validator can reliably reject every kind of real-world invalid image, such as unrelated medical images, low-quality scans, or images from other sources.

## Prediction

Run `predict.py` with an image path to use the validator and classifier. The script loads both model files from this folder. It first resizes the image to 128×128 for validation; validator probabilities below **0.50** reject the input. Images that pass are resized to 224×224 and classified. When the highest class probability is below **0.60**, the prediction is displayed as **Uncertain**.

Sample outputs recorded for this prototype:

- Normal: **95.03%**
- Benign: **79.34%**
- Malignant: **87.89%**
- A car image was rejected by the invalid-image validator.

Sample predictions illustrate example outputs and are not a guarantee of accuracy on new images.

## Module files

- `BUSI_Image_Classification.ipynb` — Google Colab notebook for data preparation, MobileNetV2 model definition, optional training, and evaluation.
- `busi_mobilenetv2.keras` — MobileNetV2 three-class image classifier.
- `busi_ultrasound_validator.keras` — binary ultrasound validity classifier.
- `predict.py` — command-line prediction script using the validator and classifier.

## Intended use

This is an **educational research prototype**, not a medical diagnostic tool. It has not been clinically validated and must not be used to diagnose, rule out, stage, or grade cancer. Medical decisions should be made by qualified healthcare professionals using appropriate clinical evaluation.
