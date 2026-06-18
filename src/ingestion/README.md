# Ingestão automatizada (uv)

Camada inicial do pipeline: baixa as bases anuais de AIH SUS-DF via API pública saúde-DF e consolida em um único CSV para carga em Azure Blob a ser utilizado pelo Power BI. Suporta também execução local, sem credenciais Azure configuradas.

## Estrutura de saída

A partir da raiz do projeto, os arquivos gerados são salvos em:

```text
<raiz-do-projeto>/
└── data/
    ├── raw/                          # uma linha por ano (2022–2026)
    │   ├── dados_2022.csv
    │   ├── dados_2023.csv
    │   ├── dados_2024.csv
    │   ├── dados_2025.csv
    │   └── dados_2026.csv
    └── concat/
        └── dados_concatenados.csv    # arquivo carregado no Azure Blob
```

> A pasta `data/` está ignorada pelo Git — os CSVs ficam só no disco local de cada colaborador.
> Quando `ingestion/main.py` é executada pelo runner do Github Actions, os dados de todos os anos serão baixados, já que o ambiente não possui persistência.
> Na nuvem, o arquivo final consolidado fica disponível publicamente em:
`https://${AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/${AZURE_CONTAINER}/dados_concatenados.csv`

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

Para executar apenas a fase de download e concatenação local, nenhuma configuração extra é necessária.

Se deseja testar a fase de upload para o Azure na sua máquina, crie um arquivo `.env` duplicando `.env.example` dentro da pasta src/ingestion/:

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

Quando executado localmente, o script é **idempotente**: arquivos anuais que já existem (e não estão vazios) em `data/raw/` são pulados. Para forçar re-download de um ano específico, apague `data/raw/dados_YYYY.csv` antes de rodar.

### Com upload para o Azure Blob

```bash
uv run --env-file .env main.py
```

## Saída esperada (Com credenciais Azure)

```text
Pipeline ingestao SUS-DF
  raiz   : <...>/analise-hospitalar-sus-df
  raw    : data/raw/dados_YYYY.csv
  concat : data/concat/dados_concatenados.csv

[1/2] Download por ano:
  [get]  2022: baixando...
  [ok]   2022: salvo em data/raw/dados_2022.csv
  [skip] 2023: arquivo ja existe
  ...

[2/2] Consolidacao:
  [ok]   5 arquivos consolidados em data/concat/dados_concatenados.csv (985,220 linhas)
  [upload] Enviando consolidado para o Azure Blob Storage...
  [ok]   Upload concluído!
  [url]  Público em: https://${AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/${AZURE_CONTAINER}/dados_concatenados.csv

Done.
```

## Quando rodar `uv sync` novamente

- Quando houver mudança no `pyproject.toml`.
- Quando o lock/dependências forem atualizados.
- Quando recriar o ambiente local.
