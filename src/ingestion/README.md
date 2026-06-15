# Ingestão (uv)

Camada inicial do pipeline: baixa as bases anuais de AIH SUS-DF via API pública saúde-DF e consolida em um único CSV para consumo pelo Power BI.

## Estrutura de saída

A partir da raiz do projeto, os arquivos gerados são salvos em:

```
<raiz-do-projeto>/
└── data/
    ├── raw/                          # uma linha por ano (2022–2026)
    │   ├── dados_2022.csv
    │   ├── dados_2023.csv
    │   ├── dados_2024.csv
    │   ├── dados_2025.csv
    │   └── dados_2026.csv
    └── concat/
        └── dados_concatenados.csv    # arquivo lido pelo Power BI
```

> A pasta `data/` está ignorada pelo Git — os CSVs ficam só no disco local de cada colaborador.

## Pré-requisitos

- [`uv`](https://docs.astral.sh/uv/) instalado no sistema.
- Conectividade com `api3.saude.df.gov.br`.

## Sincronizar dependências

A partir da raiz do projeto:

```bash
cd src/ingestion
uv sync
```

Esse comando cria/atualiza o ambiente virtual em `src/ingestion/.venv` e instala as dependências do `pyproject.toml`.

## Executar a ingestão

```bash
uv run main.py
```

Ou simplesmente `python main.py` se o `.venv` da ingestion já estiver ativo (ex.: VS Code com o interpretador `.venv` selecionado).

O script é **idempotente**: arquivos anuais que já existem (e não estão vazios) em `data/raw/` são pulados. Para forçar re-download de um ano específico, apague `data/raw/dados_YYYY.csv` antes de rodar.

## Saída esperada

```
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

Done.
```

## Quando rodar `uv sync` novamente

- Quando houver mudança no `pyproject.toml`.
- Quando o lock/dependências forem atualizados.
- Quando recriar o ambiente local.
