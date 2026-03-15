"""
Extract weak lobe labels from MIMIC-CXR reports using regex + simple negation handling.
Outputs a CSV with columns:
study_id, RUL, RML, RLL, LUL, LLL
"""

import argparse
import re
import sys

import pandas as pd

LOBE_PATTERNS = {
    "RUL": [r"right\s+upper\s+lobe", r"\brul\b"],
    "RML": [r"right\s+middle\s+lobe", r"\brml\b"],
    "RLL": [r"right\s+lower\s+lobe", r"\brll\b"],
    "LUL": [r"left\s+upper\s+lobe", r"\blul\b"],
    "LLL": [r"left\s+lower\s+lobe", r"\blll\b"],
}

NEGATIONS = [
    "no",
    "without",
    "free of",
    "negative for",
    "absence of",
    "absent",
    "not",
]

SECTION_HEADERS = [
    "FINDINGS",
    "IMPRESSION",
]


def _select_sections(text: str) -> str:
    if not text:
        return ""
    upper = text.upper()
    pieces = []
    for header in SECTION_HEADERS:
        idx = upper.find(header)
        if idx >= 0:
            start = idx + len(header)
            pieces.append(text[start:])
    if pieces:
        return "\n".join(pieces)
    return text


def _is_negated(text: str, match_start: int, window: int = 6) -> bool:
    tokens = re.findall(r"\b\w+\b", text)
    if not tokens:
        return False

    # Approximate token index by splitting on whitespace before match.
    prefix = text[:match_start]
    prefix_tokens = re.findall(r"\b\w+\b", prefix)
    idx = len(prefix_tokens)
    start = max(0, idx - window)
    scope = " ".join(tokens[start:idx]).lower()
    return any(neg in scope for neg in NEGATIONS)


def extract_lobes(report_text: str) -> dict:
    report_text = report_text or ""
    report_text = _select_sections(report_text)
    lowered = report_text.lower()

    labels = {k: 0 for k in LOBE_PATTERNS.keys()}

    for lobe, patterns in LOBE_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, lowered):
                if not _is_negated(lowered, match.start()):
                    labels[lobe] = 1
                    break
            if labels[lobe] == 1:
                break

    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports_csv", required=True, help="Path to mimic-cxr-2.0.0-reports.csv(.gz)")
    parser.add_argument("--out_csv", required=True, help="Output CSV for lobe labels")
    args = parser.parse_args()

    reports = pd.read_csv(args.reports_csv)
    if "study_id" not in reports.columns or "text" not in reports.columns:
        print("reports_csv must contain columns: study_id, text", file=sys.stderr)
        sys.exit(1)

    rows = []
    for _, row in reports.iterrows():
        labels = extract_lobes(row.get("text", ""))
        rows.append({
            "study_id": row["study_id"],
            "RUL": labels["RUL"],
            "RML": labels["RML"],
            "RLL": labels["RLL"],
            "LUL": labels["LUL"],
            "LLL": labels["LLL"],
        })

    out = pd.DataFrame(rows)
    out.to_csv(args.out_csv, index=False)
    print(f"Wrote {len(out)} rows to {args.out_csv}")


if __name__ == "__main__":
    main()
