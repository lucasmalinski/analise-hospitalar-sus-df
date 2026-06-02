# Ingestion (uv)

Este diretório usa `uv` para gerenciar dependências Python.

## Pré-requisitos

- `uv` instalado no sistema.

## Sincronizar dependências

No diretório `ingestion/`, execute:

```bash
uv sync
```

Esse comando cria/atualiza o ambiente virtual em `ingestion/.venv` e instala as dependências do `pyproject.toml`.

## Executar o script de ingestão

Após o sync, rode:

```bash
uv run main.py
```

Ou simplesmente main.py se o .venv ingestion estiver ativo (ex.: VsCode)

Os arquivos CSV serão salvos em `ingestion/raw/`.

## Fluxo recomendado

```bash
cd ingestion
uv sync
```

```bash
uv run main.py
```

Ou ```main.py``` com .venv ativo

## Quando rodar `uv sync` novamente

- Quando houver mudança no `pyproject.toml`.
- Quando o lock/dependências forem atualizados.
- Quando recriar o ambiente local.
