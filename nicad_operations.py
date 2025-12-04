import subprocess
from pathlib import Path
from paths import search_results_path, git_repos_path
import shutil
import os


def remove_logs_and_xml_files(directory):
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)

        if os.path.isfile(file_path) and (file_name.endswith(".log") or file_name.endswith(".xml")):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Remove error {file_path}: {e}")


def run_nicad(git_repository_path, language, number_pr, number_commit, mode):
    """
    mode = 'parent' or 'child'
    """
    print(" >>> Running nicad6...")
    subprocess.run(["./nicad6", "functions", language, git_repository_path],
                cwd="../../NiCad",
                check=True)

    project = git_repository_path.split("/")[-1]
    nicad_xml = f"{git_repository_path}_functions-clones/{project}_functions-clones-0.60-classes.xml"
    
    old_xml_name = f"{search_results_path}/{project}_functions-clones-0.60-classes.xml"
    old_path = Path(old_xml_name)
    
    if old_path.exists():
        old_path.unlink()

    shutil.move(nicad_xml, search_results_path)
    clones_dir = Path(f"{git_repository_path}_functions-clones")
    shutil.rmtree(clones_dir, ignore_errors=True)
    remove_logs_and_xml_files(git_repos_path)

    new_xml_name = f"{search_results_path}/nicad-result-{project}-{number_pr}-{number_commit}-{mode}.xml"
    new_path = Path(new_xml_name)
    old_path.rename(new_path)

    print("Finished clone detection.\n")
