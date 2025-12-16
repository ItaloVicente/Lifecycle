#!/usr/bin/env python3
import os
import csv
import glob
import random
import xml.etree.ElementTree as ET
import pandas as pd
import subprocess
from pathlib import Path

# CONFIG
CLASSIFIED_DIR = "clones_classified"
SEARCH_RESULTS_DIR = "search_results"
METADATA_DIRS = ["metadata"]  # try both locations
GIT_REPOS_DIR = os.path.join("..", "git_repos")  # default relative path (adjust if needed)
OUTPUT_CSV = os.path.join(CLASSIFIED_DIR, "random_samples_detailed.csv")
SNIPPETS_DIR = os.path.join(CLASSIFIED_DIR, "sample_snippets")

# How many unique fingerprints to sample in total
N_SAMPLES = 20

random.seed(42)

os.makedirs(SNIPPETS_DIR, exist_ok=True)

# Helper: locate metadata csv for a project
def find_metadata_csv(project):
    for base in METADATA_DIRS:
        p = os.path.join(base, f"{project}.csv")
        if os.path.exists(p):
            return p
    return None

# Helper: read XML and try to find element by fingerprint attribute (Simian-like)
def find_set_by_fingerprint(xml_path, fingerprint):
    if fingerprint == 0 or fingerprint == "0":
        fingerprint = "0000000000000000"
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        return None, f"XML_PARSE_ERROR: {e}"

    # 1) Try find any element with attribute fingerprint equal to the value
    for elem in root.iter():
        if 'fingerprint' in elem.attrib and elem.attrib.get('fingerprint') == fingerprint:
            # In Simian XML the <set> contains <block> children with sourceFile/startLineNumber/endLineNumber
            blocks = []
            for blk in elem.findall('.//block'):
                # attribute names vary, support both 'sourceFile' and 'sourcefile' etc.
                src = blk.attrib.get('sourceFile') or blk.attrib.get('sourcefile') or blk.attrib.get('file') or blk.attrib.get('source')
                start = blk.attrib.get('startLineNumber') or blk.attrib.get('startline') or blk.attrib.get('startLine') or blk.attrib.get('startlineNumber')
                end = blk.attrib.get('endLineNumber') or blk.attrib.get('endline') or blk.attrib.get('endLine') or blk.attrib.get('endlineNumber')
                blocks.append((src, start, end))
            if blocks:
                return blocks, None

    # 2) If not found, attempt to search textual occurrence of fingerprint in file (some tools embed it as text)
    try:
        txt = Path(xml_path).read_text(encoding='utf-8', errors='ignore')
        if fingerprint in txt:
            # fall back: find nearest <set ...> that encloses that position
            idx = txt.find(fingerprint)
            # find opening '<set' before idx and closing '</set>' after idx
            start_idx = txt.rfind('<set', 0, idx)
            end_idx = txt.find('</set>', idx)
            if start_idx != -1 and end_idx != -1:
                segment = txt[start_idx:end_idx+6]
                # parse segment
                try:
                    segroot = ET.fromstring(segment)
                    blocks = []
                    for blk in segroot.findall('.//block'):
                        src = blk.attrib.get('sourceFile') or blk.attrib.get('sourcefile') or blk.attrib.get('file') or blk.attrib.get('source')
                        start = blk.attrib.get('startLineNumber') or blk.attrib.get('startline') or blk.attrib.get('startLine') or blk.attrib.get('startlineNumber')
                        end = blk.attrib.get('endLineNumber') or blk.attrib.get('endline') or blk.attrib.get('endLine') or blk.attrib.get('endlineNumber')
                        blocks.append((src, start, end))
                    if blocks:
                        return blocks, None
                except Exception:
                    pass
        # 3) If still not found, try Nicad-style: look for <class> elements that contain sources. We can't match fingerprint here, so return None.
    except Exception:
        pass

    return None, "FINGERPRINT_NOT_FOUND_IN_XML"

# Helper: extract snippet from file (1-indexed lines: start..end)
def extract_snippet(file_path, start, end):
    try:
        lines = Path(file_path).read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception as e:
        return None, f"READ_ERROR: {e}"
    try:
        s = int(start) - 1
        eidx = int(end)  # exclusive index in slice usage below will handle
        snippet_lines = lines[s:eidx]
        snippet = "\n".join(snippet_lines)
        return snippet, None
    except Exception as e:
        return None, f"LINE_IDX_ERROR: {e}"

# Collect all classified files
classified_files = glob.glob(os.path.join(CLASSIFIED_DIR, "*_clone_classified.csv"))
if not classified_files:
    print("No classified files found in", CLASSIFIED_DIR)
    raise SystemExit(1)

# Track sampled fingerprints per file to avoid duplicates within same file
sampled_per_file = {cf: set() for cf in classified_files}

# Final rows
rows = []

attempts = 0
while len(rows) < N_SAMPLES and attempts < N_SAMPLES * 10:
    attempts += 1
    # choose a random classified file (files may repeat)
    file_path = random.choice(classified_files)
    try:
        df = pd.read_csv(file_path, dtype=str)
    except Exception as e:
        print("Failed to read", file_path, ":", e)
        continue
    if df.empty:
        continue

    # choose a random fingerprint from this file that was not already picked from this same file
    unique_fps = df['clone_fingerprint'].dropna().unique().tolist()
    available = [fp for fp in unique_fps if fp not in sampled_per_file[file_path]]
    if not available:
        # nothing left in this file, try another
        continue
    fp = random.choice(available)
    sampled_per_file[file_path].add(fp)

    # get one row that has this fingerprint (if multiple, pick first)
    row = df[df['clone_fingerprint'] == fp].iloc[0].to_dict()

    project = row.get('project')
    pr = row.get('pr')
    start_commit = row.get('start_commit')

    # Save basic fields from the classified file row (keep many common columns if present)
    out = {k: row.get(k, "") for k in ['project','pr','clone_fingerprint','start_commit','end_commit','total_commits','categoria','distancia','duracao']}
    out['source_classified_file'] = os.path.basename(file_path)

    # find corresponding search_results XML (child)
    xml_name = f"nicad-result-{project}-{pr}-{start_commit}-child.xml"
    xml_path = os.path.join(SEARCH_RESULTS_DIR, xml_name)
    if not os.path.exists(xml_path):
        out['xml_path'] = "XML_NOT_FOUND"
        out['xml_error'] = "XML not found at expected path: " + xml_path
        rows.append(out)
        print(f"XML not found for sample: {xml_path}")
        continue
    out['xml_path'] = xml_path

    # parse XML and find blocks for fingerprint
    blocks, err = find_set_by_fingerprint(xml_path, fp)
    if err is not None:
        out['xml_error'] = err
        rows.append(out)
        print(f"Fingerprint {fp} not found in XML {xml_path}: {err}")
        continue

    # Expecting at least two blocks in the set; take first two
    if len(blocks) < 2:
        out['xml_error'] = "LESS_THAN_2_BLOCKS_IN_SET"
        rows.append(out)
        print(f"Fingerprint {fp} in {xml_path} has less than 2 blocks.")
        continue

    # normalize block data and add to out
    file1, start1, end1 = blocks[0]
    file2, start2, end2 = blocks[1]
    out['clone1_file'] = file1
    out['clone1_start'] = start1
    out['clone1_end'] = end1
    out['clone2_file'] = file2
    out['clone2_start'] = start2
    out['clone2_end'] = end2

    # find metadata csv for the project to retrieve child sha
    meta_csv = find_metadata_csv(project)
    sha_child = None
    if meta_csv is None:
        out['meta_csv'] = "METADATA_NOT_FOUND"
        rows.append(out)
        print(f"Metadata CSV not found for project {project}")
        continue
    out['meta_csv'] = meta_csv

    try:
        df_meta = pd.read_csv(meta_csv, dtype=str)
    except Exception as e:
        out['meta_csv_error'] = f"READ_ERROR: {e}"
        rows.append(out)
        continue

    # try to find row with number_pr and number_commit == start_commit
    # attempt several likely column names
    possible_pr_cols = [c for c in df_meta.columns if 'pr' in c.lower()]
    possible_commit_cols = [c for c in df_meta.columns if 'commit' in c.lower() or 'number_commit' in c.lower()]
    pr_col = None
    commit_col = None
    for c in possible_pr_cols:
        if (df_meta[c].astype(str) == str(pr)).any():
            pr_col = c
            break
    for c in possible_commit_cols:
        if (df_meta[c].astype(str) == str(start_commit)).any():
            commit_col = c
            break

    if pr_col is None or commit_col is None:
        # fallback: try exact columns 'number_pr' and 'number_commit' or 'number_commit' etc
        for c in ['number_pr','pr','PR','number_commit','number_commit']:
            if c in df_meta.columns and pr_col is None and (df_meta[c].astype(str) == str(pr)).any():
                pr_col = c
            if c in df_meta.columns and commit_col is None and (df_meta[c].astype(str) == str(start_commit)).any():
                commit_col = c

    if pr_col is None or commit_col is None:
        out['meta_lookup_error'] = f"Could not find matching PR/commit columns in {meta_csv}. Columns: {df_meta.columns.tolist()}"
        rows.append(out)
        print(out['meta_lookup_error'])
        continue

    matched = df_meta[(df_meta[pr_col].astype(str) == str(pr)) & (df_meta[commit_col].astype(str) == str(start_commit))]
    if matched.empty:
        out['meta_lookup_error'] = f"No matching row for PR={pr} and commit={start_commit} in {meta_csv}"
        rows.append(out)
        print(out['meta_lookup_error'])
        continue

    # find child sha column (common names: child, child_sha, sha_child, sha)
    child_sha_col = None
    for cname in ['child','child_sha','sha_child','sha','commit_sha']:
        if cname in matched.columns:
            child_sha_col = cname
            break
    if child_sha_col is None:
        # attempt to find any column with values that look like sha (40 hex chars)
        for c in matched.columns:
            sample_val = str(matched[c].iloc[0])
            if isinstance(sample_val, str) and len(sample_val) >= 7:  # loose heuristic
                child_sha_col = c
                break

    if child_sha_col is None:
        out['meta_lookup_error'] = "Could not determine child sha column in metadata file."
        rows.append(out)
        print(out['meta_lookup_error'])
        continue

    sha_child = matched[child_sha_col].iloc[0]
    out['sha_child'] = sha_child

    # perform git reset --hard in the repository
    repo_dir_guesses = [
        os.path.join("git_repos", project),
        os.path.join(os.getcwd(), "git_repos", project),
        os.path.join(os.getcwd(), "..", "git_repos", project)
    ]
    repo_dir = None
    for guess in repo_dir_guesses:
        if os.path.exists(guess):
            repo_dir = guess
            break
    if repo_dir is None:
        out['repo_error'] = "git_repos project path not found. Tried: " + str(repo_dir_guesses)
        rows.append(out)
        print(out['repo_error'])
        continue

    # run git reset --hard <sha_child>
    try:
        subprocess.run(["git", "reset", "--hard", sha_child], cwd=repo_dir, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out['git_reset'] = f"reset OK in {repo_dir}"
    except Exception as e:
        out['git_reset_error'] = f"GIT_RESET_FAILED: {e}"
        rows.append(out)
        print(out['git_reset_error'])
        continue

    # extract code snippets for both clones
    snippet1, err1 = extract_snippet(file1, start1, end1)
    snippet2, err2 = extract_snippet(file2, start2, end2)
    if err1:
        out['snippet1_error'] = err1
    if err2:
        out['snippet2_error'] = err2

    # save snippets to files
    s1_path = os.path.join(SNIPPETS_DIR, f"{project}_{pr}_{start_commit}_1.txt")
    s2_path = os.path.join(SNIPPETS_DIR, f"{project}_{pr}_{start_commit}_2.txt")
    try:
        if snippet1 is not None:
            Path(s1_path).write_text(snippet1, encoding='utf-8', errors='ignore')
            out['snippet1_path'] = s1_path
        if snippet2 is not None:
            Path(s2_path).write_text(snippet2, encoding='utf-8', errors='ignore')
            out['snippet2_path'] = s2_path
    except Exception as e:
        out['snippet_save_error'] = str(e)

    rows.append(out)
    print(f"Sampled: project={project} pr={pr} start={start_commit} fp={fp}")

# Save results to CSV
if rows:
    keys = list({k for r in rows for k in r.keys()})
    with open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print("\\nSaved samples to", OUTPUT_CSV)
else:
    print("No samples collected.")

