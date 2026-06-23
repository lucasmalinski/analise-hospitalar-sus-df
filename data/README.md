# Dados — Análise Hospitalar SUS-DF

> Dicionário, procedência e arquitetura de armazenamento dos dados. Os arquivos físicos da pasta `data/` estão **ignorados pelo Git** (ver `.gitignore`) — o destino canônico é o **Azure Blob Storage**, com o disco local servindo como cache de execução.

---

## 1. Origem

- **Fonte:** API pública da Secretaria de Saúde do Distrito Federal — `https://api3.saude.df.gov.br/dados_csv/`
- **Tipo de dado:** registros de **Autorização de Internação Hospitalar (AIH)** da rede SUS sediada no Distrito Federal.
- **Licença:** dado público, sem restrição de uso. Lei de Acesso à Informação (Lei nº 12.527/2011).
- **Acesso:** público, sem autenticação. Endpoint é parametrizado por ano: `?ano=YYYY&mes=disable&complexidade=disable&parto=disable&cirurgia=disable&obito=disable`.
- **Cobertura temporal:** janeiro/2022 a maio/2026 (dados de 2026 são parciais).

A camada de ingestão (`src/ingestion/main.py`) cuida do download, conversão em Parquet via PyArrow, upload incremental para o Azure Blob e reconstrução do consolidado. Detalhes operacionais (variáveis de ambiente, fluxos completo e incremental, execução via GitHub Actions) em `src/ingestion/README.md`.

---

## 2. Camadas de armazenamento

O pipeline opera em duas camadas: **disco local** (cache de execução) e **Azure Blob Storage** (data lake canônico). O Power BI consome o Parquet do Azure via parâmetro `URL Base`.

### 2.1 Disco local — `data/`

```text
<raiz-do-projeto>/
└── data/
    ├── raw/                          # CSVs efêmeros — apagados ao final da conversão
    │   └── dados_YYYY.csv            # presente apenas durante a execução do pipeline
    └── parquet/                      # Parquets persistentes (cache local)
        ├── dados_2022.parquet
        ├── dados_2023.parquet
        ├── dados_2024.parquet
        ├── dados_2025.parquet
        ├── dados_2026.parquet        # parcial
        └── dados_concatenados.parquet
```

`data/raw/` é volátil — o `main.py` apaga o CSV anual logo após convertê-lo em Parquet, mantendo o disco enxuto.
`data/parquet/` é a cópia local dos arquivos do data lake — usada como fallback quando o Azure não está configurado.

### 2.2 Azure Blob Storage (data lake canônico)

URLs públicas (substituir `${AZURE_STORAGE_ACCOUNT_NAME}` e `${AZURE_STORAGE_CONTAINER_NAME}` pelos valores do `.env`):

```text
https://${AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/${AZURE_STORAGE_CONTAINER_NAME}/dados_YYYY.parquet
https://${AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/${AZURE_STORAGE_CONTAINER_NAME}/dados_concatenados.parquet
```

O Azure é considerado **fonte de verdade**:
- O parâmetro `URL Base` no Power Query aponta para a URL do `dados_concatenados.parquet` no Azure.
- A pipeline em GitHub Actions roda diariamente, atualizando o Azure quando há novas competências.
- O cache local em `data/parquet/` existe apenas para iteração de desenvolvimento offline.

---

## 3. Volumetria

| Arquivo                          | Linhas (sem header) | Período                  |
| -------------------------------- | ------------------- | ------------------------ |
| `dados_2022.parquet`             | 223.453             | jan a dez/2022           |
| `dados_2023.parquet`             | 228.288             | jan a dez/2023           |
| `dados_2024.parquet`             | 238.733             | jan a dez/2024           |
| `dados_2025.parquet`             | 238.675             | jan a dez/2025           |
| `dados_2026.parquet`             | ~56.067             | jan a mai/2026 (parcial) |
| `dados_concatenados.parquet`     | **985.216**         | jan/2022 a mai/2026      |

Em formato Parquet (codificação colunar + compressão Snappy padrão do PyArrow), o consolidado fica **~30 MB**, contra ~300 MB do CSV original. O Power BI lê o Parquet 5–10× mais rápido.

---

## 4. Dicionário de colunas

O CSV bruto traz 26 colunas com prefixo `i_` (padrão da API SUS-DF). Esses mesmos nomes são preservados na conversão para Parquet (PyArrow inferring schema), e renomeados em camada Power Query para nomes em Title Case (mapeamento completo em `relatorio/analise.SemanticModel/definition/tables/fato_atendimento.tmdl`).

| #  | Coluna bruta                | Tipo (PyArrow) | Descrição                                                                                |
| -- | --------------------------- | -------------- | ----------------------------------------------------------------------------------------- |
| 1  | `i_ano_compt`               | int64          | Ano de competência                                                                        |
| 2  | `i_mes_compt`               | int64          | Mês de competência (1–12)                                                                |
| 3  | `i_estab_cnes`              | int64          | Código CNES do estabelecimento                                                            |
| 4  | `i_desc_sigla_estab_cnes`   | string         | Sigla do hospital (`HRS`, `HRG`, `HRSM`, etc.)                                            |
| 5  | `i_desc_regiao_saude`       | string         | Região de Saúde do estabelecimento                                                        |
| 6  | `i_desc_espec_leito`        | string         | Especialidade do leito utilizado                                                          |
| 7  | `i_faixa_etaria`            | string         | Faixa etária em formato técnico (`"00_<_01"`, ...)                                        |
| 8  | `i_desc_sexo`               | string         | Sexo do paciente                                                                          |
| 9  | `i_proc_realizado`          | int64          | Código SIGTAP do procedimento realizado                                                   |
| 10 | `i_desc_proc_realizado`     | string         | Descrição do procedimento SIGTAP                                                          |
| 11 | `i_desc_grupo`              | string         | Grupo de procedimento                                                                     |
| 12 | `i_cid_principal`           | string         | Código CID-10 do diagnóstico principal                                                    |
| 13 | `i_desc_cid_principal`      | string         | Descrição do CID principal                                                                |
| 14 | `i_desc_car_int_atend`      | string         | Caráter da internação (`URGENCIA`, `ELETIVA`, ...)                                        |
| 15 | `i_desc_complex_proc`       | string         | Complexidade do procedimento                                                              |
| 16 | `i_qtd_aih`                 | int64          | **Sempre 1.** Cada linha é uma AIH.                                                       |
| 17 | `i_desc_radf_res`           | string         | RA do DF onde o paciente reside                                                           |
| 18 | `i_desc_tipo_financ`        | string         | Tipo de financiamento da AIH                                                              |
| 19 | `i_partos`                  | string         | `"Sim"` quando o procedimento é de parto, nulo caso contrário                             |
| 20 | `i_cirurgias`               | string         | `"Sim"` quando o procedimento é cirúrgico, nulo caso contrário                            |
| 21 | `i_desc_obito`              | string         | `"Com óbito"` ou `"Sem óbito"`                                                            |
| 22 | `i_desc_munic_res`          | string         | Município de residência do paciente                                                       |
| 23 | `i_desc_uf_res`             | string         | UF de residência do paciente (DF, GO, etc.)                                               |
| 24 | `i_val_total_aih`           | double         | Valor total da AIH em R$                                                                  |
| 25 | `i_qtd_diaria_pac`          | int64          | Quantidade de dias internado                                                              |
| 26 | `i_qtd_diaria_uti`          | int64          | Quantidade de dias em UTI                                                                 |

### 4.1 Mapeamento para o modelo dimensional

O Power Query lê o Parquet do Azure (não o CSV bruto), renomeia colunas em Title Case (ex.: `i_ano_compt` → `Ano Competência`, `i_val_total_aih` → `Valor AIH`) e aplica trim em `RA de Residência`. O mapeamento completo está no `partition` da `fato_atendimento` em `relatorio/analise.SemanticModel/definition/tables/fato_atendimento.tmdl`.

---

## 5. Armadilhas conhecidas dos dados

Cinco pontos que **toda análise sobre esse dataset precisa observar** — descobertos na EDA (`src/EDA/analise_exploratoria.ipynb`) e documentados para evitar erros recorrentes.

### 5.1 Campos de desfecho são texto, não numérico

`i_partos`, `i_cirurgias` e `i_desc_obito` chegam como string (`"Sim"` / nulo / `"Com óbito"` / `"Sem óbito"`). Tentativas de operar aritmeticamente sobre eles geram `TypeError`. Para uso em Python, converter explicitamente:

```python
df["c_obito"]   = (df["i_desc_obito"] == "Com óbito").astype(int)
df["c_parto"]   = (df["i_partos"] == "Sim").astype(int)
df["c_cirurg"]  = (df["i_cirurgias"] == "Sim").astype(int)
```

Em DAX, comparar com o literal textual original — ver `docs/kpis_okrs.md` §2 e `docs/decisoes_de_modelagem.md` §2.3.

### 5.2 `i_qtd_aih` é constante igual a 1

Não somar `mean` direto para obter "média de internações" — vai retornar 1. Para qualquer cálculo de média mensal de internações, agregar primeiro por `(ano, mês)` com `sum` e depois aplicar `mean`. A EDA seção 3.3 documenta a correção.

### 5.3 RAs com trailing spaces

A coluna `i_desc_radf_res` contém duplicatas por espaço em branco final: `"Jardim Botânico"` e `"Jardim Botânico "` aparecem como linhas distintas. Sem trim, contagens de RAs distintas ultrapassam as 35 oficiais do DF.

Tratamento no Power Query — ver `docs/decisoes_de_modelagem.md` §6.3.

### 5.4 Faixa etária em formato técnico

`i_faixa_etaria` vem como `"00_<_01"`, `"01_<_05"`, ..., `"80_<_+_"`. A `dim_detalhes` normaliza para forma legível (`"0 a 1 ano"`, `"1 a 5 anos"`, ..., `"80+ anos"`) via cascata de substituições. Filtros DAX (incluindo KPIs K15 e K16) usam **o valor normalizado**, não o bruto.

### 5.5 21% de pacientes sem RA mapeada

Aproximadamente 21% das internações têm `i_desc_radf_res` nulo ou vazio. Predominantemente são pacientes do entorno metropolitano de Goiás atendidos na rede DF. Não tentar imputar — a invisibilidade é um achado de relevância para o controle social e está modelado como KPI dedicado (K10 Cobertura RA Mapeada em `docs/kpis_okrs.md` §2.3).

---

## 6. Como regenerar os arquivos

O pipeline é idempotente e usa árvore de decisão para evitar redownloads desnecessários:

```bash
cd src/ingestion
uv sync                              # uma vez, instala dependências
uv run --env-file .env main.py       # com upload para Azure
uv run main.py                       # somente local
```

Detalhes em `src/ingestion/README.md`: pré-requisitos, configuração do `.env`, fluxo completo vs incremental, saída esperada.

A pipeline também roda automaticamente via GitHub Actions a cada novo push e diariamente, garantindo que o Azure tenha o `dados_concatenados.parquet` sempre atualizado.

---

## 7. Versão dos dados

A API SUS-DF publica dados acumulativos por competência, com defasagem de 30–60 dias da competência real. Re-executar a ingestão em data posterior traz:

- Linhas adicionais de meses já incluídos (ajustes retroativos de AIH).
- Linhas de meses ainda não cobertos (avanço do mês de fechamento).

O fluxo incremental do `main.py` detecta automaticamente novas linhas comparando metadata do Parquet no Azure com a contagem da API antes de decidir se reescreve o arquivo do ano corrente.

Para reproducibilidade analítica de uma data específica, baixar o snapshot do Azure e versionar localmente o arquivo.
