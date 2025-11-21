import pandas as pd
from tqdm import tqdm
import configparser
import matplotlib.pyplot as plt
import requests

# === Ler token do arquivo .ini ===
config = configparser.ConfigParser()
config.read("token.ini")
GITHUB_TOKEN = config.get("github", "token")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# === Ler linguagem do settings.ini ===
config.read("settings.ini")
LANGUAGE = config["DETAILS"]["language"]
print(f"Filtrando PRs para a linguagem: {LANGUAGE}")

# === Ler datasets ===
repo_df = pd.read_parquet("hf://datasets/hao-li/AIDev/repository.parquet")
pr_df = pd.read_parquet("hf://datasets/hao-li/AIDev/pull_request.parquet")
pr_commits = pd.read_parquet("hf://datasets/hao-li/AIDev/pr_commits.parquet")
pr_commit_details = pd.read_parquet("hf://datasets/hao-li/AIDev/pr_commit_details.parquet")

# === Filtrar PRs mergeadas ===
merged_prs = pr_df[pr_df["merged_at"].notna()].copy()

# === Juntar com os repositórios ===
merged_prs = merged_prs.merge(
    repo_df,
    left_on="repo_url",
    right_on="url",
    how="left",
    suffixes=("_pr", "_repo")
)

# === Filtrar somente PRs na linguagem especificada ===
valid_prs_lang = merged_prs[merged_prs["language"] == LANGUAGE].copy()

# === Pegar commits com pelo menos uma adição ===
commits_with_details = pr_commits.merge(
    pr_commit_details.drop(columns=["pr_id"]),
    on="sha",
    how="inner"
)

# === Manter commits que têm adições (>0) ===
commits_with_additions = commits_with_details[commits_with_details["additions"] > 0]

# === Garantir commits únicos por PR ===
commits_unique = commits_with_additions.drop_duplicates(subset=["sha", "pr_id"])

# === Filtrar commits que pertencem a PRs da linguagem escolhida ===
commits_unique = commits_unique[commits_unique["pr_id"].isin(valid_prs_lang["id_pr"])]

# === Função auxiliar: obter SHA base da PR via GitHub API ===
def get_base_sha(repo_url: str, pr_number: int) -> str:
    try:
        parts = repo_url.replace("https://github.com/", "").split("/")
        owner, repo = parts[4], parts[5]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

        r = requests.get(api_url, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            return data.get("base", {}).get("sha", None)
        else:
            print(f"Falha ao buscar base SHA para {api_url} ({r.status_code})")
            return None
    except Exception as e:
        print(f"Erro ao obter base SHA: {e}")
        return None


# === Construir CSV final ===
rows = []

for pr_id, group in tqdm(commits_unique.groupby("pr_id"), desc=f"Processando PRs ({LANGUAGE})"):
    group_sorted = group.sort_values("committed_at") if "committed_at" in group.columns else group

    pr_info = valid_prs_lang[valid_prs_lang["id_pr"] == pr_id]
    if pr_info.empty:
        continue  # segurança extra

    repo_url = pr_info["repo_url"].values[0]
    pr_number = pr_info["number"].values[0]
    pr_html_url = pr_info["html_url"].values[0]
    merged_at = pr_info["merged_at"].values[0]  # <-- Data da merge

    base_sha = get_base_sha(repo_url, pr_number)  # SHA base da PR

    previous_sha = base_sha  # parent inicial

    for i, (_, row) in enumerate(group_sorted.iterrows(), start=1):
        current_sha = row["sha"]

        rows.append({
            "id": f"{pr_number}_rev{i}",
            "number_pr": pr_number,
            "number_commit": i,
            "repo_url": repo_url,
            "merged_at": merged_at,
            "id_pr": pr_id,
            "sha_commit": current_sha,
            "url_commit": f"{repo_url}/commit/{current_sha}",
            "url_pr": pr_html_url,
            "parent": None,
            "child": current_sha
        })

        previous_sha = current_sha  # atual vira o próximo parent

# === Criar DataFrame e reordenar colunas ===
commit_df = pd.DataFrame(rows)
col_order = [
    "id",
    "number_pr",
    "number_commit",
    "repo_url",
    "merged_at",  # <-- nova coluna
    "id_pr",
    "sha_commit",
    "url_commit",
    "url_pr",
    "parent",
    "child"
]
commit_df = commit_df[col_order]

# === Salvar CSV final ===
output_csv = f"{LANGUAGE.lower()}_pr_commits_without_parents.csv"
commit_df.to_csv(output_csv, index=False)
print(f"CSV gerado com sucesso: {output_csv} {commit_df.shape}")

# === Ler CSV gerado ===
df = pd.read_csv(output_csv)

# === Contar commits por PR ===
commits_per_pr = df.groupby("id_pr")["sha_commit"].count().reset_index()
commits_per_pr.rename(columns={"sha_commit": "num_commits"}, inplace=True)

# === Estatísticas básicas ===
print("\nEstatísticas gerais:")
print(commits_per_pr["num_commits"].describe())

# === Criar boxplot ===
plt.figure(figsize=(10,6))
plt.boxplot(commits_per_pr["num_commits"], vert=True, patch_artist=True,
            boxprops=dict(facecolor="skyblue", color="blue"),
            medianprops=dict(color="red"),
            whiskerprops=dict(color="blue"),
            capprops=dict(color="blue"))
plt.title(f"Distribuição de commits por PR ({LANGUAGE})")
plt.ylabel("Número de commits")
plt.xticks([1], ["PRs"])
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.savefig(f"boxplot_{LANGUAGE.lower()}.png")
plt.show()

# === Separar grupos de PRs ===
single_commit_prs = commits_per_pr[commits_per_pr["num_commits"] == 1]
multi_commit_prs = commits_per_pr[commits_per_pr["num_commits"] > 1]

print(f"\nPRs com apenas 1 commit: {len(single_commit_prs)}")
print(f"PRs com mais de 1 commit: {len(multi_commit_prs)}")

# === Salvar resultados ===
single_commit_prs.to_csv(f"{LANGUAGE.lower()}_prs_single_commit.csv", index=False)
multi_commit_prs.to_csv(f"{LANGUAGE.lower()}_prs_multi_commit.csv", index=False)

print("\nArquivos gerados:")
print(f"- {output_csv} (commits com parent/child e id customizado)")
print(f"- {LANGUAGE.lower()}_prs_single_commit.csv (PRs com 1 commit)")
print(f"- {LANGUAGE.lower()}_prs_multi_commit.csv (PRs com >1 commit)")
