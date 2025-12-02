#!/usr/bin/env python3
import os
import subprocess
import configparser
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from nicad_operations import run_nicad
from paths import search_results_path, metadata_path, git_repos_path
from languages import LANGUAGES

# ============================================================
# 1. Load configuration
# ============================================================

with open("projects_filtered.txt", "r", encoding="utf-8") as f:
    projects = f.read().split('\n')

config = configparser.ConfigParser()
config.read("settings.ini")
path_to_repo = config.get("DETAILS", "path_to_repo", fallback=".")
language = LANGUAGES[config.get("DETAILS", "language")]

search_results_path.mkdir(exist_ok=True)

# ============================================================
# 2. Loop through projects
# ============================================================

for project in projects:
    metadata_csv = f"{metadata_path}/{project}.csv"
    repo_path = f"{git_repos_path}/{project}"

    if not Path(metadata_csv).exists():
        print(f"⚠️ CSV not found: {metadata_csv}")
        continue

    if not Path(repo_path).exists():
        print(f"⚠️ Repository not found: {repo_path}")
        continue

    df = pd.read_csv(metadata_csv)

    if df.empty:
        print(f"⚠️ Empty CSV: {metadata_csv}")
        continue

    print(f"\n📦 Processing project: {project} ({len(df)} commits)")

    # Enter repository
    os.chdir(repo_path)

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Commits of {project}"):

        number_pr = row["number_pr"]
        number_commit = row["number_commit"]

        parent_sha = str(row["parent"]).strip()
        child_sha = str(row["child"]).strip()

        # ============================
        # --- Run on PARENT ---
        # ============================
        if parent_sha not in ["", "None"] and len(parent_sha) > 5:
            try:
                subprocess.run(
                    ["git", "reset", "--hard", parent_sha],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                run_nicad(repo_path, language, number_pr, number_commit, "parent")
            except subprocess.CalledProcessError:
                print(f"⚠️ Error checking out parent {parent_sha} (PR {number_pr})")

        # ============================
        # --- Run on CHILD ---
        # ============================
        if child_sha not in ["", "None"] and len(child_sha) > 5:
            try:
                subprocess.run(
                    ["git", "reset", "--hard", child_sha],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                run_nicad(repo_path, language, number_pr, number_commit, "child")
            except subprocess.CalledProcessError:
                print(f"⚠️ Error checking out child {child_sha} (PR {number_pr})")

print("\n🎉 Execution finished successfully!")
