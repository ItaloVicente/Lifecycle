import os
import pandas as pd
import subprocess
import configparser
from pathlib import Path
from tqdm import tqdm
import shutil

# === Read configuration ===
config = configparser.ConfigParser()
config.read("settings.ini")

projects = [p.strip() for p in config.get("DETAILS", "projects").split(",")]
path_to_repo = config.get("DETAILS", "path_to_repo", fallback=".")
search_results_dir = os.path.join(path_to_repo, "search_results")
language = config.get("DETAILS", "language")

os.makedirs(search_results_dir, exist_ok=True)

def remove_logs_and_xml_files(directory):
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)

        if os.path.isfile(file_path) and (file_name.endswith(".log") or file_name.endswith(".xml")):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Remove error {file_path}: {e}")

def run_nicad(git_repository_path, result_path):
    """
    mode = 'parent' or 'child'
    """
    print(" >>> Running nicad6...")
    repo_name = git_repository_path.split("/")[-1]
    git_repository_path = os.path.abspath(git_repository_path)
    subprocess.run(["./nicad6", "functions", languague, git_repository_path],
                cwd="NiCad",
                check=True)

    nicad_xml = f"{git_repository_path}_functions-clones/{repo_name}_functions-clones-0.30-classes.xml"
    shutil.move(nicad_xml, result_path)
    clones_dir = Path(f"{git_repository_path}_functions-clones")
    shutil.rmtree(clones_dir, ignore_errors=True)
    remove_logs_and_xml_files("repos")

    print("Finished clone detection.\n")

# === Function to run Simian ===
def run_simian(repo_path, project, number_pr, number_commit, mode):
    """
    mode = 'parent' or 'child'
    """
    output_xml = os.path.join(
        search_results_dir,
        f"simian-result-{project}-{number_pr}-{number_commit}-{mode}.xml"
    )
    simian_jar = os.path.join(path_to_repo, "simian-4.0.0", "simian-4.0.0.jar")
    options = "-formatter=xml -threshold=6"
    simian_command = f'java -jar "{simian_jar}" {options} -includes="{repo_path}/**/*.{language}" > "{output_xml}"'
    os.system(simian_command)
    print(f"✅ Simian saved to {output_xml}")

# === Loop through projects ===
for project in projects:
    metadata_csv = os.path.join(path_to_repo, "metadata", f"{project}.csv")
    repo_path = os.path.join(path_to_repo, "git_repos", project)

    if not os.path.exists(metadata_csv):
        print(f"⚠️ CSV not found: {metadata_csv}")
        continue
    if not os.path.exists(repo_path):
        print(f"⚠️ Repository not found: {repo_path}")
        continue

    df = pd.read_csv(metadata_csv)
    if df.empty:
        print(f"⚠️ Empty CSV: {metadata_csv}")
        continue

    print(f"\n📦 Processing project: {project} ({len(df)} commits)")

    os.chdir(repo_path)

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Commits for {project}"):

        number_pr = row["number_pr"]
        number_commit = row["number_commit"]

        parent_sha = str(row["parent"]).strip()
        child_sha = str(row["child"]).strip()

        # --- Run simian on parent ---
        if parent_sha and parent_sha != "None" and len(parent_sha) > 5:
            try:
                subprocess.run(
                    ["git", "reset", "--hard", parent_sha],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                run_nicad(repo_path, "test.xml")
                # run_simian(repo_path, project, number_pr, number_commit, "parent")
            except subprocess.CalledProcessError:
                print(f"⚠️ Failed to checkout parent {parent_sha} ({project} PR {number_pr})")

        # --- Run simian on child ---
        if child_sha and len(child_sha) > 5:
            try:
                subprocess.run(
                    ["git", "reset", "--hard", child_sha],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                # run_simian(repo_path, project, number_pr, number_commit, "child")
            except subprocess.CalledProcessError:
                print(f"⚠️ Failed to checkout child {child_sha} ({project} PR {number_pr})")

print("\n✅ Execution completed successfully!")
