import os
import pandas as pd
import xml.etree.ElementTree as ET
import configparser
from tqdm import tqdm
from paths import metadata_path, search_results_path, lifetimes_path

# ==========================================
# 1. SETTINGS
# ==========================================
config = configparser.ConfigParser()
config.read(".settings.ini")

with open("projects_filtered.txt", "r", encoding="utf-8") as f:
    projects = f.read().split('\n')

os.makedirs(lifetimes_path, exist_ok=True)

# ==========================================
# 2. EXTRACTION FUNCTION (GRANULARITY: BLOCK/SNIPPET)
# ==========================================
def extract_clone_instances(xml_path):
    """
    Reads the XML and returns a SET of identifier tuples.

    Each clone instance is identified by:
    (fingerprint, source_file, start_line, end_line)
    """
    instances = set()

    if not os.path.exists(xml_path):
        return instances

    try:
        with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Header cleanup
        idx = content.find("<")
        if idx > 0:
            content = content[idx:]

        root = ET.fromstring(content)

        # Look for sets (Simian structure or generic <clones>)
        sets = root.findall(".//set")

        for s in sets:
            fp = s.attrib.get("fingerprint")
            if not fp:
                continue

            # Try to find blocks (Simian <block> or NiCad <source>)
            blocks = s.findall("block")
            if not blocks:
                blocks = s.findall("source")

            for b in blocks:
                # Normalize attributes
                source_file = b.attrib.get("sourceFile") or b.attrib.get("file")
                start_line = b.attrib.get("startLineNumber") or b.attrib.get("startline")
                end_line = b.attrib.get("endLineNumber") or b.attrib.get("endline")

                if source_file and start_line and end_line:
                    # Unique snippet identifier:
                    # If the fingerprint is new, this snippet is new.
                    # If the fingerprint already exists, but this file/line is new, this snippet is new.
                    instance_id = (fp, source_file, start_line, end_line)
                    instances.add(instance_id)

        return instances

    except Exception as e:
        print(f"⚠️ Error reading XML {xml_path}: {e}")
        return set()


# ==========================================
# 3. MAIN LOOP
# ==========================================
for project in projects:
    csv_path = f"{metadata_path}/{project}.csv"
    if not os.path.exists(csv_path):
        print(f"⚠️ CSV not found: {csv_path}")
        continue

    try:
        df = pd.read_csv(csv_path)
    except:
        continue

    if df.empty:
        continue

    print(f"\n📌 Tracking Individual Snippets - Project: {project}")

    results = []

    # Group by PR
    for pr_id, pr_group in tqdm(df.groupby("number_pr"), desc=f"PRs - {project}"):
        pr_group = pr_group.sort_values("number_commit")
        total_commits_in_pr = pr_group.shape[0]

        # ACTIVE INSTANCES TRACKER
        # Key: (fingerprint, source_file, start_line, end_line)
        # Value: starting commit (start_commit)
        active_instances = {}

        for _, row in pr_group.iterrows():
            number_commit = row["number_commit"]

            # File paths (NiCad result pattern according to your last XML)
            xml_parent = os.path.join(
                search_results_path,
                f"nicad-result-{project}-{pr_id}-{number_commit}-parent.xml"
            )
            xml_child = os.path.join(
                search_results_path,
                f"nicad-result-{project}-{pr_id}-{number_commit}-child.xml"
            )

            # 1. Extract sets of instances (unique tuples)
            parent_instances = extract_clone_instances(xml_parent)
            child_instances = extract_clone_instances(xml_child)

            # --- A. CHECK DEATHS (Snippets that disappeared) ---
            # Iterate over instances that were already active
            current_active_keys = list(active_instances.keys())

            for instance_key in current_active_keys:
                # If this specific instance (fp + file + lines) is NOT in the child
                # it means that piece of code changed or was deleted
                if instance_key not in child_instances:
                    # DIED
                    start_commit = active_instances[instance_key]
                    fp, src, start, end = instance_key

                    results.append({
                        "project": project,
                        "pr": pr_id,
                        "clone_fingerprint": fp,
                        "source_file": src,
                        "start_line": start,
                        "end_line": end,
                        "start_commit": start_commit,
                        "end_commit": number_commit - 1,  # Died before this commit
                        "total_commits_in_pr": total_commits_in_pr
                    })
                    del active_instances[instance_key]

            # --- B. CHECK BIRTHS (New snippets) ---
            # The set logic solves your problem here:
            # new_instances contains EVERYTHING that is in child but not in parent.
            # - If the fingerprint is new -> All its snippets appear here.
            # - If the fingerprint already existed but gained a clone -> This new snippet appears here.
            new_instances = child_instances - parent_instances

            for instance_key in new_instances:
                # Only register if we are not already tracking it (safety)
                if instance_key not in active_instances:
                    active_instances[instance_key] = number_commit

        # --- C. CLOSE INSTANCES THAT SURVIVED UNTIL THE END OF THE PR ---
        last_commit = pr_group["number_commit"].max()
        for instance_key, start_commit in active_instances.items():
            fp, src, start, end = instance_key
            results.append({
                "project": project,
                "pr": pr_id,
                "clone_fingerprint": fp,
                "source_file": src,
                "start_line": start,
                "end_line": end,
                "start_commit": start_commit,
                "end_commit": last_commit,
                "total_commits_in_pr": total_commits_in_pr
            })

    # === Save CSV ===
    output_csv = os.path.join(lifetimes_path, f"{project}_clone_lifetimes.csv")

    df_res = pd.DataFrame(results)

    # Order columns to make reading easier
    columns_order = [
        "project", "pr", "clone_fingerprint",
        "start_commit", "end_commit", "total_commits_in_pr",
        "source_file", "start_line", "end_line"
    ]

    if not df_res.empty:
        # Ensure we only select existing columns
        cols_to_use = [c for c in columns_order if c in df_res.columns]
        df_res = df_res[cols_to_use]
        df_res.to_csv(output_csv, index=False)
        print(f"✅ CSV saved: {output_csv}")
    else:
        print(f"⚠️ No clone found or tracked for {project}")
