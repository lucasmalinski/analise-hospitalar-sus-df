# Ingestão automatizada (uv)

Camada inicial do pipeline: baixa as bases anuais de AIH SUS-DF via API pública saúde-DF e consolida em um único Parquet para carga no Azure Blob a ser utilizado pelo Power BI. Suporta também execução local, sem credenciais Azure configuradas.

## Estrutura de saída

A partir da raiz do projeto, os arquivos gerados são salvos em:

```text
<raiz-do-projeto>/
└── data/
    ├── raw/                          # CSVs temporários (baixados e apagados após conversão)
    │   └── dados_YYYY.csv            # removido automaticamente após gerar o Parquet
    └── parquet/                      # Parquets persistentes (anuais + consolidado)
        ├── dados_2022.parquet
        ├── dados_2023.parquet
        ├── dados_2024.parquet
        ├── dados_2025.parquet
        ├── dados_2026.parquet
        └── dados_concatenados.parquet
```

> A pasta `data/` está ignorada pelo Git — os arquivos ficam só no disco local de cada colaborador.
> Quando `ingestion/main.py` é executada pelo runner do Github Actions, os dados de todos os anos serão baixados, já que o ambiente não possui persistência.
> Na nuvem, os arquivos ficam disponíveis publicamente em:
> `https://${AZURE_STORAGE_ACCOUNT}.dfs.core.windows.net/${AZURE_CONTAINER}/dados_YYYY.parquet`
> `https://${AZURE_STORAGE_ACCOUNT}.dfs.core.windows.net/${AZURE_CONTAINER}/dados_concatenados.parquet`

## Pré-requisitos para execução local

- [`uv`](https://docs.astral.sh/uv/) instalado no sistema.
- Conectividade com `api3.saude.df.gov.br`.
- (Opcional) Credenciais do Azure para testar o upload localmente.

## Sincronizar dependências

A partir da raiz do projeto:

```bash
cd src/ingestion
uv sync
```

Esse comando cria/atualiza o ambiente virtual em `src/ingestion/.venv` e instala as dependências do `pyproject.toml`.

## Configuração Local (.env)

Para executar apenas a fase de download e consolidação local, nenhuma configuração extra é necessária.

Se deseja testar a fase de upload para o Azure na sua máquina, crie um arquivo `.env` duplicando `.env.example` dentro da pasta `src/ingestion/`:

```env
AZURE_STORAGE_ACCOUNT_NAME=nome_storage_account
AZURE_STORAGE_ACCOUNT_KEY=SuaChaveDoAzureAquiTerminadaEm==
AZURE_STORAGE_CONTAINER_NAME=nome_storage_container
```

## Executar a ingestão

### Sem upload para o Azure Blob

```bash
uv run main.py
```

Ou simplesmente `python main.py` se o `.venv` da ingestion já estiver ativo (ex.: VS Code com o interpretador `.venv` selecionado).

### Com upload para o Azure Blob

```bash
uv run --env-file .env main.py
```

## Lógica de execução (árvore de decisão)

O pipeline verifica a integridade do Azure antes de decidir o que fazer:

```text
Existe dados_concatenados.parquet no Azure?
E todos os Parquets anuais estão presentes?
        │
        ├── NÃO → Fluxo completo / recuperação
        │         Para cada ano (2022..atual):
        │           - Pula se o Parquet já existe no Azure
        │           - Caso contrário: baixa CSV → converte para Parquet → upload
        │         Reconstrói e envia dados_concatenados.parquet
        │
        └── SIM → Fluxo incremental (apenas ano atual)
                  Compara linhas entre Azure e API
                    - Sem linhas novas → nenhuma ação
                    - Com linhas novas → atualiza Parquet do ano e reconstrói o concatenado
```

> **Execução local (sem Azure):** O pipeline roda inteiramente em `data/parquet/`, sem verificações de integridade remota. O fluxo completo é sempre executado, pulando apenas os Parquets anuais que já existirem localmente.

## Saída esperada

### Fluxo completo (primeira execução ou recuperação)

```text
Pipeline de ingestao SUS-DF
  azure   : Conectado via PyArrow Native FileSystem
--------------------------------------------------
-> Status: dados_concatenados.parquet AUSENTE. Iniciando fluxo completo.
  [skip] 2022: Parquet ja existe no Azure.
  [get]  2023: baixando CSV da API...
  [convert] Lendo CSV de 2023 com PyArrow...
  [upload] dados_2023.parquet salvo no Azure!
  ...

[++] Iniciando a reconstrucao de dados_concatenados.parquet...
  [ok] Concatenado local salvo. (985,220 linhas)
  [upload] Enviando concatenado atualizado para o Azure...
  [ok] Upload do concatenado finalizado!

✅ Pipeline finalizado.
```

### Fluxo incremental (execuções subsequentes)

```text
Pipeline de ingestao SUS-DF
  azure   : Conectado via PyArrow Native FileSystem
--------------------------------------------------
-> Status: dados_concatenados.parquet ENCONTRADO. Verificando ano 2026.
  [get]  2026: baixando CSV da API...
  [check] 2026: Azure tem 120,000 linhas. API tem 135,400 linhas.
  [update] Novas linhas detectadas! Atualizando arquivo de 2026...

[++] Iniciando a reconstrucao de dados_concatenados.parquet...
  [ok] Concatenado local salvo. (985,220 linhas)
  [upload] Enviando concatenado atualizado para o Azure...
  [ok] Upload do concatenado finalizado!

✅ Pipeline finalizado.
```

### Sem novidades

```text
-> Status: dados_concatenados.parquet ENCONTRADO. Verificando ano 2026.
  [get]  2026: baixando CSV da API...
  [check] 2026: Azure tem 135,400 linhas. API tem 135,400 linhas.
  [skip] Nenhuma linha nova. O concatenado atual ja esta atualizado.

✅ Pipeline finalizado.
```

## Quando rodar `uv sync` novamente

- Quando houver mudança no `pyproject.toml`.
- Quando o lock/dependências forem atualizados.
- Quando recriar o ambiente local
