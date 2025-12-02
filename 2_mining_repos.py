import os
import pandas as pd
from tqdm import tqdm
import subprocess
import requests
import configparser
from dotenv import load_dotenv
from paths import git_repos_path, metadata_path

# === Read token from .ini file ===
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# === Read settings.ini ===
config = configparser.ConfigParser()
config.read("settings.ini")
LANGUAGE = config["DETAILS"]["language"]
print(f"Selected language: {LANGUAGE}")

# === Create output directory ===
os.makedirs(git_repos_path, exist_ok=True)

# === Read CSV ===
csv_path = f"{metadata_path}/{LANGUAGE.lower()}_pr_commits_without_parents.csv"
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV file not found: {csv_path}")

# === Get unique repositories ===
df = pd.read_csv(csv_path)
repos = df["repo_url"].dropna().unique()
print(f"{len(repos)} unique repositories found for {LANGUAGE}.")

def get_clone_url(api_url: str) -> str | None:
    """
    Given the repository API URL (e.g., https://api.github.com/repos/domaframework/doma),
    returns the 'clone_url' field from the JSON response.
    """
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("clone_url", None)
        else:
            print(f"Failed to get clone_url ({r.status_code}) for {api_url}")
            return None
    except Exception as e:
        print(f"Error fetching clone_url for {api_url}: {e}")
        return None


# === Clone repositories ===
for i, api_url in enumerate(tqdm(repos, desc=f"Cloning repositories ({LANGUAGE})")):
    if i == 2:
        break

    clone_url = get_clone_url(api_url)
    if not clone_url:
        print(f"Could not get clone_url for {api_url}")
        continue

    repo_name = clone_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(git_repos_path, repo_name)

    if os.path.exists(repo_path):
        print(f"Repository '{repo_name}' already exists, skipping.")
        continue

    try:
        subprocess.run(["git", "clone", clone_url, repo_path], check=True)
        print(f"Cloned: {repo_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning {repo_name}: {e}")
    except Exception as e:
        print(f"Unexpected error with {repo_name}: {e}")

print(f"\nCloning completed for {LANGUAGE} projects!")
