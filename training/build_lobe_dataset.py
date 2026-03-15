"""
Join MIMIC-CXR metadata with lobe labels and resolve image paths.
Outputs a CSV with:
image_path, study_id, subject_id, view_position, RUL, RML, RLL, LUL, LLL
"""

import argparse
import os
import sys

import pandas as pd


def resolve_image_path(images_root: str, row: pd.Series) -> str:
    # MIMIC-CXR-JPG uses: files/pXX/pXXXXXX/sXXXXXX/<dicom_id>.jpg
    subject_id = str(row["subject_id"])
    study_id = str(row["study_id"])
    dicom_id = str(row["dicom_id"])

    p_prefix = f"p{subject_id[:2]}"
    p_folder = f"p{subject_id}"
    s_folder = f"s{study_id}"
    filename = f"{dicom_id}.jpg"

    return os.path.join(images_root, p_prefix, p_folder, s_folder, filename)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata_csv", required=True, help="Path to mimic-cxr-2.0.0-metadata.csv(.gz)")
    parser.add_argument("--labels_csv", required=True, help="Output from extract_lobe_labels.py")
    parser.add_argument("--images_root", required=True, help="Path to mimic-cxr-jpg/2.0.0/files")
    parser.add_argument("--out_csv", required=True, help="Output dataset CSV")
    parser.add_argument("--view_filter", default="", help="Comma-separated list of views, e.g. PA,AP")
    parser.add_argument("--require_label", action="store_true", help="Drop rows with no positive lobe labels")
    args = parser.parse_args()

    meta = pd.read_csv(args.metadata_csv)
    labels = pd.read_csv(args.labels_csv)

    required_cols = {"subject_id", "study_id", "dicom_id", "ViewPosition"}
    if not required_cols.issubset(set(meta.columns)):
        print(f"metadata_csv must contain columns: {sorted(required_cols)}", file=sys.stderr)
        sys.exit(1)

    merged = meta.merge(labels, on="study_id", how="left")

    for col in ["RUL", "RML", "RLL", "LUL", "LLL"]:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = merged[col].fillna(0).astype(int)

    if args.view_filter:
        allowed = {v.strip().upper() for v in args.view_filter.split(",") if v.strip()}
        merged = merged[merged["ViewPosition"].str.upper().isin(allowed)]

    if args.require_label:
        merged = merged[(merged[["RUL", "RML", "RLL", "LUL", "LLL"]].sum(axis=1) > 0)]

    merged["image_path"] = merged.apply(lambda r: resolve_image_path(args.images_root, r), axis=1)
    merged = merged.rename(columns={"ViewPosition": "view_position"})

    out_cols = [
        "image_path",
        "study_id",
        "subject_id",
        "view_position",
        "RUL",
        "RML",
        "RLL",
        "LUL",
        "LLL",
    ]
    merged[out_cols].to_csv(args.out_csv, index=False)
    print(f"Wrote {len(merged)} rows to {args.out_csv}")


if __name__ == "__main__":
    main()
