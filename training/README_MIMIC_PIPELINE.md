# MIMIC-CXR Lobe Label Pipeline (Multi-Label)

This pipeline builds weakly supervised lobe labels from MIMIC-CXR reports and trains a 5-label multi-label classifier.

Labels:
- Right Upper (RUL)
- Right Middle (RML)
- Right Lower (RLL)
- Left Upper (LUL)
- Left Lower (LLL)

Grad-CAM is for explanation only and is not used to infer lobes.

## 1) Prerequisites
- Access to MIMIC-CXR-JPG and MIMIC-CXR Reports on PhysioNet.
- Python 3.9+.

Suggested Python packages:
- numpy
- pandas
- pillow
- scikit-learn
- torch
- torchvision
- tqdm

## 2) Expected MIMIC files
These scripts expect the CSVs from MIMIC-CXR v2:
- `mimic-cxr-2.0.0-reports.csv.gz`
- `mimic-cxr-2.0.0-metadata.csv.gz`

Images are expected under the MIMIC-CXR-JPG root, usually:
`mimic-cxr-jpg/2.0.0/files/pXX/pXXXXXX/sXXXXXX/<dicom_id>.jpg`

## 3) Build labels from reports
Example:
```
python training/extract_lobe_labels.py ^
  --reports_csv D:\mimic\mimic-cxr-2.0.0-reports.csv.gz ^
  --out_csv D:\mimic\lobe_labels.csv
```

## 4) Build training dataset
Example:
```
python training/build_lobe_dataset.py ^
  --metadata_csv D:\mimic\mimic-cxr-2.0.0-metadata.csv.gz ^
  --labels_csv D:\mimic\lobe_labels.csv ^
  --images_root D:\mimic\mimic-cxr-jpg\2.0.0\files ^
  --out_csv D:\mimic\lobe_dataset.csv ^
  --view_filter PA,AP
```

## 5) Train a multi-label model
Example:
```
python training/train_lobe_multilabel.py ^
  --dataset_csv D:\mimic\lobe_dataset.csv ^
  --images_root D:\mimic\mimic-cxr-jpg\2.0.0\files ^
  --epochs 12 ^
  --batch_size 32 ^
  --lr 1e-4 ^
  --output_dir D:\mimic\outputs
```

## Notes
- This is weak supervision. Report mentions can be incomplete.
- Consider filtering to samples with at least one lobe label.
- For production, calibrate thresholds per class.
