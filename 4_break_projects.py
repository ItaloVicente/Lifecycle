import os
import pandas as pd
from tqdm import tqdm
import configparser
from paths import metadata_path

# === Main CSV path ===
config = configparser.ConfigParser()
config.read("settings.ini")
LANGUAGE = config["DETAILS"]["language"]
csv_path = f"{metadata_path}/{LANGUAGE.lower()}_pr_commits_with_parents.csv"

# === Read main CSV ===
df = pd.read_csv(csv_path)

# === Extract repository name from the API URL ===
# Example: https://api.github.com/repos/domaframework/doma → "doma"
df["repo_name"] = df["repo_url"].apply(
    lambda x: x.rstrip("/").split("/")[-1] if isinstance(x, str) else "unknown"
)

# === Group by repository ===
for repo_name, group in tqdm(df.groupby("repo_name"), desc="Generating CSVs per repository"):
    # Optionally sort by PR number and commit number
    group_sorted = group.sort_values(["number_pr", "number_commit"])

    # Output path
    out_path = os.path.join(metadata_path, f"{repo_name}.csv")

    # Save individual CSV
    group_sorted.to_csv(out_path, index=False)
    print(f"✅ Generated: {out_path} ({len(group_sorted)} rows)")

print("\n🎯 All CSVs have been generated in:", os.path.abspath(metadata_path))
