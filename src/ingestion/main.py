"""Pipeline de ingestao SUS-DF (PyArrow Nativo).

Baixa as bases anuais de AIH via API publica saude-DF (2022-2026).
Garante a existencia dos parquets anuais e recria o consolidado
(dados_concatenados) de forma idempotente apenas se houver linhas novas.

Execucao:
    cd src/ingestion
    uv run main.py
"""

import os
from datetime import datetime
from pathlib import Path
import requests

# Imports exclusivos do PyArrow
import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.parquet as pq
from pyarrow import fs

# Configuracao ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARQUET_DIR = PROJECT_ROOT / "data" / "parquet"

ANO_ATUAL = datetime.now().year
YEAR_RANGE = range(2022, ANO_ATUAL+1)  # inclusive 2022..ANO_ATUAL


BASE_URL = (
    "https://api3.saude.df.gov.br/dados_csv/"
    "?ano={ano}&mes=disable&complexidade=disable"
    "&parto=disable&cirurgia=disable&obito=disable"
)

# Configuracao do Azure das variaveis de ambiente
_az_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
_az_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
_az_container = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

# Garantia contra \r do Windows em .env
AZURE_ACCOUNT_NAME = _az_name.strip() if _az_name else None
AZURE_ACCOUNT_KEY = _az_key.strip() if _az_key else None
CONTAINER_NAME = _az_container.strip() if _az_container else None

# Inicializacao do FileSystem Nativo do PyArrow
azure_fs = None
if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY:
    azure_fs = fs.AzureFileSystem(account_name=AZURE_ACCOUNT_NAME, account_key=AZURE_ACCOUNT_KEY) # type: ignore

# Etapas Auxiliares ----------------------------------------------------------

def arquivo_existe_no_azure(caminho_relativo: str) -> bool:
    """Verifica se um arquivo existe no Azure Blob Storage usando PyArrow."""
    if not azure_fs:
        return False
    caminho_completo = f"{CONTAINER_NAME}/{caminho_relativo}"
    info = azure_fs.get_file_info(caminho_completo)
    return info.type != fs.FileType.NotFound # type: ignore

def baixar_csv(ano: int) -> Path | None:
    """Baixa o CSV de um ano temporariamente usando um arquivo .part de seguranca."""
    local_csv = RAW_DIR / f"dados_{ano}.csv"
    tmp_file = local_csv.with_name(local_csv.name + ".part")
    
    print(f"  [get]  {ano}: baixando CSV da API...")
    try:
        response = requests.get(BASE_URL.format(ano=ano))
        response.raise_for_status()
        tmp_file.write_bytes(response.content)
        tmp_file.replace(local_csv)
        return local_csv
    except requests.RequestException as error:
        print(f"  [err]  {ano}: falha no download ({error})")
        if tmp_file.exists():
            tmp_file.unlink()
        return None

def csv_para_parquet(csv_path: Path, ano: int) -> pa.Table | None:
    """Le o CSV local usando PyArrow, salva Parquet local e envia ao Azure."""
    print(f"  [convert] Lendo CSV de {ano} com PyArrow...")
    try:
        tabela = pv.read_csv(csv_path) # type: ignore
        
        local_parquet = PARQUET_DIR / f"dados_{ano}.parquet"
        pq.write_table(tabela, local_parquet)
        
        if azure_fs:
            az_path = f"{CONTAINER_NAME}/dados_{ano}.parquet"
            with azure_fs.open_output_stream(az_path) as out_stream:
                pq.write_table(tabela, out_stream)
            print(f"  [upload] dados_{ano}.parquet salvo no Azure!")
            
        return tabela
    except Exception as e:
        print(f"  [err] Erro ao converter arquivo de {ano}: {e}")
        return None
    finally:
        if csv_path.exists():
            csv_path.unlink()

def reconstruir_concatenado() -> None:
    """Le todos os Parquets (2022-2026), concatena e sobrescreve o resultado final."""
    print("\n[++] Iniciando a reconstrucao de dados_concatenados.parquet...")
    tabelas = []
    
    for ano in YEAR_RANGE:
        az_path = f"{CONTAINER_NAME}/dados_{ano}.parquet"
        local_path = PARQUET_DIR / f"dados_{ano}.parquet"
        
        try:
            if azure_fs and arquivo_existe_no_azure(f"dados_{ano}.parquet"):
                with azure_fs.open_input_file(az_path) as in_stream:
                    tabelas.append(pq.read_table(in_stream))
            elif local_path.exists():
                tabelas.append(pq.read_table(local_path))
            else:
                print(f"  [warn] Parquet de {ano} ausente para a concatenacao.")
        except Exception as e:
            print(f"  [err] Erro ao ler tabela de {ano}: {e}")

    if not tabelas:
        print("  [err] Nenhuma tabela encontrada para concatenar.")
        return

    # Concatena ponteiros em memoria via Zero-Copy (instantaneo)
    tabela_final = pa.concat_tables(tabelas)
    
    local_concat = PARQUET_DIR / "dados_concatenados.parquet"
    pq.write_table(tabela_final, local_concat)
    print(f"  [ok] Concatenado local salvo. ({tabela_final.num_rows:,} linhas)")
    
    if azure_fs:
        print("  [upload] Enviando concatenado atualizado para o Azure...")
        az_concat_path = f"{CONTAINER_NAME}/dados_concatenados.parquet"
        with azure_fs.open_output_stream(az_concat_path) as out_stream:
            pq.write_table(tabela_final, out_stream)
        print("  [ok] Upload do concatenado finalizado!")

# Etapas Principais (Árvore de Decisao) ------------------------------------

def fluxo_inicial_ou_recuperacao(concatenado_existe: bool, historico_completo: bool) -> None:
    """Roda quando o concatenado ou alguma peca essencial do historico esta faltando."""
    if not concatenado_existe:
        print("-> Status: dados_concatenados.parquet AUSENTE. Iniciando fluxo completo.")
    elif not historico_completo:
        print("-> Status: Arquivos anuais ausentes no Azure. Iniciando recuperacao do historico...")
        
    for ano in YEAR_RANGE:
        if arquivo_existe_no_azure(f"dados_{ano}.parquet"):
            print(f"  [skip] {ano}: Parquet ja existe no Azure.")
        else:
            csv_path = baixar_csv(ano)
            if csv_path:
                csv_para_parquet(csv_path, ano)
                
    reconstruir_concatenado()

def fluxo_incremental_ano_atual() -> None:
    """Roda quando a infraestrutura esta integra. Foca estritamente em buscar novos registros."""
    print(f"-> Status: dados_concatenados.parquet ENCONTRADO. Verificando ano {ANO_ATUAL}.")
    
    az_path_atual = f"{CONTAINER_NAME}/dados_{ANO_ATUAL}.parquet"
    linhas_no_azure = 0
    
    if azure_fs and arquivo_existe_no_azure(f"dados_{ANO_ATUAL}.parquet"):
        with azure_fs.open_input_file(az_path_atual) as in_stream:
            meta = pq.read_metadata(in_stream)
            linhas_no_azure = meta.num_rows

    csv_novo = baixar_csv(ANO_ATUAL)
    if not csv_novo:
        return
        
    tabela_nova = pv.read_csv(csv_novo) # type: ignore
    linhas_na_api = tabela_nova.num_rows
    
    print(f"  [check] {ANO_ATUAL}: Azure tem {linhas_no_azure} linhas. API tem {linhas_na_api} linhas.")
    
    if linhas_na_api > linhas_no_azure:
        print(f"  [update] Novas linhas detectadas! Atualizando arquivo de {ANO_ATUAL}...")
        
        local_parquet = PARQUET_DIR / f"dados_{ANO_ATUAL}.parquet"
        pq.write_table(tabela_nova, local_parquet)
        
        if azure_fs:
            with azure_fs.open_output_stream(az_path_atual) as out_stream:
                pq.write_table(tabela_nova, out_stream)
                
        csv_novo.unlink()
        reconstruir_concatenado()
    else:
        print("  [skip] Nenhuma linha nova. O concatenado atual ja esta atualizado.")
        csv_novo.unlink()

# Entrypoint -----------------------------------------------------------------

def main() -> None:
    print("Pipeline de ingestao SUS-DF")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    
    if azure_fs:
        print("  azure   : Conectado via PyArrow Native FileSystem")
    else:
        print("  azure   : NÃO conectado. O pipeline ira rodar estritamente local.")

    print("-" * 50)
    
    # Validacao dupla de integridade antes de definir a estratégia de carga
    concatenado_existe = arquivo_existe_no_azure("dados_concatenados.parquet")
    historico_completo = all(
        arquivo_existe_no_azure(f"dados_{ano}.parquet") for ano in YEAR_RANGE
    )

    if concatenado_existe and historico_completo:
        fluxo_incremental_ano_atual()
    else:
        fluxo_inicial_ou_recuperacao(concatenado_existe, historico_completo)
        
    print("\n✅ Pipeline finalizado.")

if __name__ == "__main__":
    main()