import os
import pandas as pd
import configparser
from tqdm import tqdm
from paths import lifetimes_path, clones_classified_path

# === Read configuration ===
config = configparser.ConfigParser()
config.read("settings.ini")

with open("projects_filtered.txt", "r", encoding="utf-8") as f:
    projects = f.read().split('\n')

os.makedirs(lifetimes_path, exist_ok=True)
os.makedirs(clones_classified_path, exist_ok=True)

def classify_clone(start, end, total):
    # start, end, total are integers here

    # 1. First, check the "full span" case
    #    This correctly captures (1, 1, 1) AND (1, 5, 5).
    if start == 1 and end == total:
        return "ini_mei_final"

    # 2. If it is not a full span, check the "unique" cases (start == end)
    elif start == end:
        if start == 1:
            # We already know end != total, otherwise it would have matched the 'if' above
            return "unique_ini"
        elif start == total:
            # We already know start != 1
            return "unique_final"
        else:
            # Neither start=1 nor end=total
            return "unique_mei"

    # 3. If it is not "full span" nor "unique", it is a "partial span"
    else:  # start != end
        if start == 1 and end < total:
            return "ini_mei"
        elif 1 < start and end < total:
            return "mei"
        elif start > 1 and end == total:
            return "mei_final"
        else:
            # Safety case, should not be reached
            return "unknown"

for project in projects:
    input_csv = os.path.join(lifetimes_path, f"{project}_clone_lifetimes.csv")
    if not os.path.exists(input_csv):
        print(f"⚠️ File not found: {input_csv}")
        continue

    try:
        df = pd.read_csv(input_csv)
    except pd.errors.EmptyDataError:
        # If the file is completely empty (0 bytes), pandas raises this error
        print(f"⚠️ Empty CSV (EmptyDataError): {input_csv}")
        continue  # <-- THIS IS THE CRITICAL FIX
    except Exception as e:
        # Catch other read errors
        print(f"🚨 Error reading CSV {input_csv}: {e}")
        continue  # <-- Also skip on other errors

    if df.empty:
        # If the file has headers but no data rows
        print(f"⚠️ Empty CSV (no data rows): {input_csv}")
        continue

    # Check minimum expected columns
    required_cols = {"pr", "clone_fingerprint", "start_commit", "end_commit", "total_commits_in_pr"}
    if not required_cols.issubset(set(df.columns)):
        print(f"⚠️ Missing columns in {input_csv}. Expected: {required_cols}. Found: {set(df.columns)}")
        continue

    print(f"\n📌 Classifying CLONES for project: {project}")

    # Normalize/force types and remove invalid rows
    # Coerce -> converts non-numeric values to NaN
    df["start_commit"] = pd.to_numeric(df["start_commit"], errors="coerce")
    df["end_commit"] = pd.to_numeric(df["end_commit"], errors="coerce")
    df["total_commits_in_pr"] = pd.to_numeric(df["total_commits_in_pr"], errors="coerce")

    # Remove rows with NaN or total_commits_in_pr <= 0
    invalid_mask = (
        df["start_commit"].isna()
        | df["end_commit"].isna()
        | df["total_commits_in_pr"].isna()
        | (df["total_commits_in_pr"] <= 0)
    )
    if invalid_mask.any():
        n_invalid = invalid_mask.sum()
        print(f"⚠️ {n_invalid} invalid/removed rows in {input_csv} (NaN or total <= 0).")
        df = df[~invalid_mask]

    if df.empty:
        print(f"⚠️ After cleaning, CSV is empty: {input_csv}")
        continue

    # Force integers (commit indices are integers)
    df["start_commit"] = df["start_commit"].astype(int)
    df["end_commit"] = df["end_commit"].astype(int)
    df["total_commits_in_pr"] = df["total_commits_in_pr"].astype(int)

    clone_rows = []

    # itertuples is faster and safer regarding indices
    for row in tqdm(df.itertuples(index=False), total=len(df), desc=f"Clones {project}"):
        # Assuming field order according to CSV:
        # row.pr, row.clone_fingerprint, row.start_commit, row.end_commit, row.total_commits_in_pr
        # Since we use index=False, names follow CSV columns (pandas replaces dots with _)
        pr = getattr(row, "pr")
        fp = getattr(row, "clone_fingerprint")
        start = int(getattr(row, "start_commit"))
        end = int(getattr(row, "end_commit"))
        total = int(getattr(row, "total_commits_in_pr"))

        # Classification
        categoria = classify_clone(start, end, total)

        # Distance
        if total <= 1:
            distancia = 0.0
        else:
            distancia = 0.0 if start == 1 else (start / total)

        # Duration (division-by-zero protection already handled)
        duracao = (end - start + 1) / total if total > 0 else 0.0

        clone_rows.append({
            "project": project,
            "pr": pr,
            "clone_fingerprint": fp,
            "start_commit": start,
            "end_commit": end,
            "total_commits": total,
            "categoria": categoria,
            "distancia": round(distancia, 4),
            "duracao": round(duracao, 4)
        })

    out_csv = os.path.join(clones_classified_path, f"{project}_clone_classified.csv")
    pd.DataFrame(clone_rows).to_csv(out_csv, index=False)
    print(f"✅ Result saved to: {out_csv}")
