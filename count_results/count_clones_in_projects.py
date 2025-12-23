import csv
import os

# Script para contar PRs únicos afetados e total de clones (com recorrências)

with open("projects_filtered.txt", "r", encoding="utf-8") as f:
    projects = f.read().split('\n')

prs_por_projeto = {}
clones_por_projeto = {}

for projeto in projects:
    caminho = os.path.join("clones_classified", projeto + "_clone_classified.csv")

    if not os.path.exists(caminho):
        print(f"Arquivo não encontrado para o projeto {projeto}: {caminho}")
        continue

    prs_unicos = set()
    total_clones = 0  # soma das recorrências

    with open(caminho, newline='') as arquivo_csv:
        leitor_csv = csv.reader(arquivo_csv)
        cabecalho = next(leitor_csv)  # ignora header

        for linha in leitor_csv:
            pr = linha[1]
            start_commit = int(linha[3])
            end_commit = int(linha[4])

            prs_unicos.add(pr)

            recorrencia = end_commit - start_commit + 1
            total_clones += recorrencia

    prs_por_projeto[projeto] = list(prs_unicos)
    clones_por_projeto[projeto] = total_clones


# --- CONTABILIZAÇÃO FINAL ---
total_prs_unicos = sum(len(lst) for lst in prs_por_projeto.values())
total_clones = sum(clones_por_projeto.values())

print("=== PRs únicos afetados por projeto ===")
for projeto, lst in prs_por_projeto.items():
    print(f"{projeto}: {len(lst)} PRs únicos")

print("\n=== Total de clones (com recorrência) por projeto ===")
for projeto, total in clones_por_projeto.items():
    print(f"{projeto}: {total} clones")

print("\n===============================================")
print("TOTAL FINAL DE PRs ÚNICOS AFETADOS:", total_prs_unicos)
print("TOTAL FINAL DE CLONES (COM RECORRÊNCIA):", total_clones)
print("===============================================")
