import pandas as pd
import os
import glob
import random

# --- 1. Definição dos Caminhos ---
CLASSIFIED_DIR = "results_clones_classifieds"
PARENTS_CSV_PATH = os.path.join("metadata", "dados", "python_pr_commits_with_parents.csv")
OUTPUT_CSV = os.path.join(CLASSIFIED_DIR, "random_sample_with_pr_urls.csv")

N_FILES_TO_SAMPLE = 20

print(f"Diretório de classificados: {CLASSIFIED_DIR}")
print(f"Arquivo de commits/pais: {PARENTS_CSV_PATH}")

# --- 2. Carregar o arquivo principal de lookup (Parents) ---
try:
    df_parents = pd.read_csv(PARENTS_CSV_PATH)
    print(f"\n✅ Arquivo de commits/pais '{PARENTS_CSV_PATH}' carregado.")
except FileNotFoundError:
    print(f"🚨 ERRO: Arquivo de lookup não encontrado em: {PARENTS_CSV_PATH}")
    print("Por favor, verifique o caminho e tente novamente.")
    exit()

# Otimizar o lookup: garantir que colunas de junção sejam numéricas
try:
    df_parents["number_pr"] = pd.to_numeric(df_parents["number_pr"], errors='coerce')
    df_parents["number_commit"] = pd.to_numeric(df_parents["number_commit"], errors='coerce')
    # Remover linhas onde a conversão falhou, pois não servirão para o match
    df_parents = df_parents.dropna(subset=["number_pr", "number_commit", "url_pr"])
except KeyError as e:
    print(f"🚨 ERRO: Coluna esperada não encontrada no arquivo de pais: {e}")
    print(f"Colunas encontradas: {list(df_parents.columns)}")
    exit()

# --- 3. Encontrar e amostrar os arquivos classificados ---
all_classified_files = glob.glob(os.path.join(CLASSIFIED_DIR, "*_clone_classified.csv"))

if not all_classified_files:
    print(f"🚨 ERRO: Nenhum arquivo '*_clone_classified.csv' encontrado em '{CLASSIFIED_DIR}'.")
    exit()

print(f"\n🔎 Encontrados {len(all_classified_files)} arquivos de clones classificados.")

# Selecionar 20 arquivos aleatórios (ou menos, se não houver 20)
if len(all_classified_files) > N_FILES_TO_SAMPLE:
    sampled_files = random.sample(all_classified_files, N_FILES_TO_SAMPLE)
    print(f"✅ Amostrando {N_FILES_TO_SAMPLE} arquivos aleatoriamente.")
else:
    sampled_files = all_classified_files
    print(f"⚠️ Encontrados apenas {len(all_classified_files)} arquivos. Usando todos.")

# --- 4. Processar cada arquivo amostrado ---
final_results = []
print("\n🔄 Processando amostras e buscando URLs de PR...")

for file_path in sampled_files:
    try:
        df_classified = pd.read_csv(file_path)
        if df_classified.empty:
            print(f"ℹ️ Arquivo {file_path} está vazio. Pulando.")
            continue

        # 4a. Selecionar 1 linha aleatória do arquivo
        random_row = df_classified.sample(n=1).iloc[0]

        # Armazenar os dados da linha em um dicionário
        sampled_data = random_row.to_dict()

        # 4b. Preparar dados para o lookup
        try:
            target_project = sampled_data['project']
            # Garantir que os tipos são compatíveis para o 'merge'
            target_pr = int(sampled_data['pr'])
            target_start_commit = int(sampled_data['start_commit'])
        except (ValueError, KeyError) as e:
            print(f"⚠️ Erro ao ler dados da linha em {file_path}: {e}. Pulando.")
            continue

        # 4c. Realizar o lookup no df_parents
        # O nome do projeto deve estar na URL (ex: .../owner/project/pull/123)
        # Usamos f"/{target_project}/" para evitar matches parciais (ex: 'my-proj' e 'my-project')
        # O na=False trata valores NaN na coluna url_pr

        match = df_parents[
            (df_parents['number_pr'] == target_pr) &
            (df_parents['number_commit'] == target_start_commit) &
            (df_parents['url_pr'].str.contains(f"/{target_project}/", case=False, na=False))
            ]

        # 4d. Salvar o resultado
        if not match.empty:
            found_url_pr = match.iloc[0]['url_pr']
            sampled_data['url_pr_encontrada'] = found_url_pr
        else:
            sampled_data['url_pr_encontrada'] = "NAO_ENCONTRADA"

        final_results.append(sampled_data)
        print(
            f"  > Processado: {os.path.basename(file_path)} (PR: {target_pr}, Commit: {target_start_commit}) -> URL: {sampled_data['url_pr_encontrada']}")

    except pd.errors.EmptyDataError:
        print(f"ℹ️ Arquivo {file_path} está vazio. Pulando.")
    except Exception as e:
        print(f"🚨 Erro ao processar o arquivo {file_path}: {e}")

# --- 5. Finalizar e Salvar ---
if not final_results:
    print("\n🚨 Nenhuma linha foi amostrada com sucesso. O script será encerrado.")
else:
    # Converter a lista de dicionários em um DataFrame
    df_final = pd.DataFrame(final_results)

    # Reordenar colunas para melhor visualização
    cols = ['url_pr_encontrada', 'project', 'pr', 'start_commit', 'end_commit',
            'categoria', 'total_commits', 'clone_fingerprint', 'distancia', 'duracao']
    # Filtrar colunas que realmente existem no df_final
    existing_cols = [c for c in cols if c in df_final.columns]
    df_final = df_final[existing_cols]

    # Salvar em CSV
    df_final.to_csv(OUTPUT_CSV, index=False)

    print("\n--- RESULTADO DA AMOSTRAGEM ---")
    print(df_final.to_string())
    print(f"\n✅ Amostra aleatória salva com sucesso em: {OUTPUT_CSV}")