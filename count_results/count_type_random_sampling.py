import pandas as pd
from unidecode import unidecode

# ---------------- CONFIGURATION ----------------
INPUT_FILE = "minerva_vote_sheet.xlsx"
# -----------------------------------------------

def normalize_clone(value):
    """
    Normalize values from 'Clone?' column:
    Sim/sim/SIM -> sim
    Não/nao/não/NAO -> nao
    """
    if pd.isna(value):
        return None

    value = unidecode(str(value)).strip().lower()

    if value == "sim":
        return "sim"
    if value == "nao":
        return "nao"

    return None


def normalize_type(value):
    """
    Normalize 'Tipo' column values to int (1, 2, or 3)
    """
    if pd.isna(value):
        return None

    try:
        return int(value)
    except ValueError:
        return None


# Load Excel file
xls = pd.ExcelFile(INPUT_FILE)

# Global counters
global_sim = 0
global_nao = 0
global_sim_por_tipo = {1: 0, 2: 0, 3: 0}

print("===== Clone Counting per Language =====\n")

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)

    # Per-language counters
    lang_sim = 0
    lang_nao = 0
    lang_sim_por_tipo = {1: 0, 2: 0, 3: 0}

    for _, row in df.iterrows():
        clone = normalize_clone(row.get("Clone?"))
        tipo = normalize_type(row.get("Tipo"))

        if clone == "sim":
            lang_sim += 1
            global_sim += 1

            if tipo in lang_sim_por_tipo:
                lang_sim_por_tipo[tipo] += 1
                global_sim_por_tipo[tipo] += 1

        elif clone == "nao":
            lang_nao += 1
            global_nao += 1

    # -------- Language Results --------
    print(f"Language / Sheet: {sheet_name}")
    print(f"  SIM: {lang_sim}")
    print(f"  NAO: {lang_nao}")
    print("  SIM by Type:")
    for tipo, count in lang_sim_por_tipo.items():
        print(f"    Type {tipo}: {count}")
    print("-" * 40)

# -------- Global Results --------
print("\n===== GLOBAL TOTAL =====")
print(f"Total SIM: {global_sim}")
print(f"Total NAO: {global_nao}")
print("Total SIM by Type:")
for tipo, count in global_sim_por_tipo.items():
    print(f"  Type {tipo}: {count}")
