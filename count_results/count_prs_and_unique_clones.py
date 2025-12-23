import os
import csv
from collections import defaultdict

# Pasta onde estão os CSVs
BASE_DIR = "clones_classified"

# Conjuntos para evitar repetições
prs_unique = set()
prs_recurrent = set()

# Conjunto de fingerprints únicos
unique_fingerprints = set()

# Categorias consideradas unique e recorrente
UNIQUE_PREFIX = "unique"
RECURRENT_PREFIXES = {"ini", "mei", "final", "ini_mei", "mei_final", "ini_final", "ini_mei_final"}

# ---------------------------------------------------------

for filename in os.listdir(BASE_DIR):
    if not filename.endswith("_clone_classified.csv"):
        continue

    filepath = os.path.join(BASE_DIR, filename)

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            project = row["project"]
            pr = row["pr"]
            fingerprint = row["clone_fingerprint"]
            categoria = row["category"].strip().lower()

            # Registrar fingerprint único
            unique_fingerprints.add(fingerprint)

            # Classificação da PR
            if categoria.startswith(UNIQUE_PREFIX):
                prs_unique.add((project, pr))
            else:
                # Se entrar aqui, é recorrente
                prs_recurrent.add((project, pr))

# ---------------------------------------------------------
# Calcular interseção
intersection = prs_unique.intersection(prs_recurrent)

# Valores finais
num_unique_prs = len(prs_unique - intersection)
num_recurrent_prs = len(prs_recurrent - intersection)
num_intersection = len(intersection)
num_unique_clones = len(unique_fingerprints)

# ---------------------------------------------------------
# Imprimir resultado
print("=== RESULTADOS FINAIS ===")
print(f"PRs Únicas: {num_unique_prs}")
print(f"PRs Recorrentes: {num_recurrent_prs}")
print(f"PRs Interseção (ambas): {num_intersection}")
print(f"Clones únicos (fingerprints únicos): {num_unique_clones}")
