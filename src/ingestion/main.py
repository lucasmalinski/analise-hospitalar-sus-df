"""Pipeline de ingestao SUS-DF.

Baixa as bases anuais de AIH via API publica saude-DF (2022-2026),
salva cada ano em `data/raw/dados_YYYY.csv` e gera o consolidado.
Se configurado com credenciais, envia o resultado para o Azure Blob Storage.

Execucao:
    cd src/ingestion
    uv run main.py
"""

import os
from pathlib import Path

import pandas as pd
import requests

# Configuracao ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CONCAT_DIR = PROJECT_ROOT / "data" / "concat"
CONCAT_FILE = CONCAT_DIR / "dados_concatenados.csv"

YEAR_RANGE = range(2022, 2027)  # inclusive 2022..2026

BASE_URL = (
    "https://api3.saude.df.gov.br/dados_csv/"
    "?ano={ano}&mes=disable&complexidade=disable"
    "&parto=disable&cirurgia=disable&obito=disable"
)

# Configuracao do Azure (lida das variaveis de ambiente do GitHub Actions)
AZURE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
CONTAINER_NAME = "dados-publicos"

# Etapas ---------------------------------------------------------------------

def baixar_ano(ano: int) -> Path | None:
    """Baixa o CSV de um ano para `data/raw/dados_{ano}.csv`."""
    output_file = RAW_DIR / f"dados_{ano}.csv"

    if output_file.exists() and output_file.stat().st_size > 0:
        print(f"  [skip] {ano}: arquivo ja existe")
        return output_file

    print(f"  [get]  {ano}: baixando...")
    tmp_file = output_file.with_name(output_file.name + ".part")

    try:
        response = requests.get(BASE_URL.format(ano=ano))
        response.raise_for_status()
        tmp_file.write_bytes(response.content)
        tmp_file.replace(output_file)
        rel = output_file.relative_to(PROJECT_ROOT)
        print(f"  [ok]   {ano}: salvo em {rel}")
        return output_file
    except requests.RequestException as error:
        print(f"  [err]  {ano}: falha no download ({error})")
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
        return None

def concatenar() -> None:
    """Le todos os CSVs anuais, grava localmente e envia para o Azure."""
    csv_files = sorted(
        str(p)
        for p in RAW_DIR.glob("dados_????.csv")
        if p.is_file() and p.stat().st_size > 0
    )

    if not csv_files:
        print("  [err]  nenhum CSV anual encontrado em data/raw/")
        return

    dfs = []
    for f in csv_files:
        try:
            dfs.append(pd.read_csv(f))
        except Exception as e:
            print(f"  [err]  falha ao ler {f}: {e}")

    if not dfs:
        print("  [err]  nenhum DataFrame valido para concatenar")
        return

    try:
        combined = pd.concat(dfs, ignore_index=True)
        
        # 1. Salva localmente (bom para testar no seu próprio PC)
        combined.to_csv(CONCAT_FILE, index=False)
        rel = CONCAT_FILE.relative_to(PROJECT_ROOT)
        print(f"  [ok]   {len(dfs)} arquivos consolidados em {rel} ({len(combined):,} linhas)")

        # 2. Faz upload para o Azure se as chaves estiverem configuradas
        if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY:
            print("  [upload] Enviando consolidado para o Azure Blob Storage...")
            storage_options = {
                "account_name": AZURE_ACCOUNT_NAME,
                "account_key": AZURE_ACCOUNT_KEY
            }
            azure_path = f"az://{CONTAINER_NAME}/dados_concatenados.csv"
            
            combined.to_csv(azure_path, storage_options=storage_options, index=False)
            
            public_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/dados_concatenados.csv"
            print(f"  [ok]   Upload concluído!")
            print(f"  [url]  Público em: {public_url}")
        else:
            print("  [skip] Upload para o Azure ignorado (credenciais ausentes).")

    except Exception as error:
        print(f"  [err]  falha ao concatenar ou enviar: {error}")

# Entrypoint -----------------------------------------------------------------

def main() -> None:
    """Executa o pipeline completo: cria pastas, baixa por ano, concatena."""
    print("Pipeline ingestao SUS-DF")
    print(f"  raiz   : {PROJECT_ROOT}")
    print(f"  raw    : {RAW_DIR.relative_to(PROJECT_ROOT)}/dados_YYYY.csv")
    print(f"  concat : {CONCAT_FILE.relative_to(PROJECT_ROOT)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CONCAT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/2] Download por ano:")
    for ano in YEAR_RANGE:
        baixar_ano(ano)

    print("\n[2/2] Consolidacao:")
    concatenar()

    print("\nDone.")

if __name__ == "__main__":
    main()