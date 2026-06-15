# Dados — Análise Hospitalar SUS-DF

> Dicionário e procedência dos dados utilizados pelo projeto. Os arquivos físicos desta pasta estão **ignorados pelo Git** (ver `.gitignore`) — cada colaborador gera localmente rodando o pipeline de ingestão.

---

## 1. Origem

- **Fonte:** API pública da Secretaria de Saúde do Distrito Federal — `https://api3.saude.df.gov.br/dados_csv/`
- **Tipo de dado:** registros de **Autorização de Internação Hospitalar (AIH)** da rede SUS sediada no Distrito Federal.
- **Licença:** dado público, sem restrição de uso. Lei de Acesso à Informação (Lei nº 12.527/2011).
- **Acesso:** público, sem autenticação. Endpoint é parametrizado por ano: `?ano=YYYY&mes=disable&complexidade=disable&parto=disable&cirurgia=disable&obito=disable`.
- **Cobertura temporal:** janeiro/2022 a maio/2026 (dados de 2026 são parciais).

A camada de ingestão (`src/ingestion/main.py`) cuida do download, deduplicação anual e consolidação. Detalhes operacionais em `src/ingestion/README.md`.

---

## 2. Estrutura de pastas

```
data/
├── raw/                          uma linha por ano de competência
│   ├── dados_2022.csv
│   ├── dados_2023.csv
│   ├── dados_2024.csv
│   ├── dados_2025.csv
│   └── dados_2026.csv            (parcial)
└── concat/
    └── dados_concatenados.csv    arquivo único consumido pelo Power BI
```

Granularidade dos arquivos: cada linha do CSV equivale a **uma AIH** registrada na competência mensal correspondente.

---

## 3. Volumetria

| Arquivo                    | Linhas (sem header) | Período                 |
| -------------------------- | ------------------- | ------------------------ |
| `dados_2022.csv`         | 223.453             | jan a dez/2022           |
| `dados_2023.csv`         | 228.288             | jan a dez/2023           |
| `dados_2024.csv`         | 238.733             | jan a dez/2024           |
| `dados_2025.csv`         | 238.675             | jan a dez/2025           |
| `dados_2026.csv`         | ~56.067             | jan a mai/2026 (parcial) |
| `dados_concatenados.csv` | **985.216**   | jan/2022 a mai/2026      |

O arquivo consolidado totaliza ~300 MB descomprimido. **Não vai para o repositório Git** — ver `.gitignore`.

---

## 4. Dicionário de colunas

O CSV bruto traz 26 colunas com prefixo `i_` (padrão da API SUS-DF). Os tipos abaixo refletem o que o `pandas.read_csv` infere; os tipos finais usados no modelo dimensional (Power Query / TMDL) são mapeados em `relatorio/analise.SemanticModel/definition/tables/fato_atendimento.tmdl`.

| #  | Coluna bruta                | Tipo    | Descrição                                                                                |
| -- | --------------------------- | ------- | ------------------------------------------------------------------------------------------ |
| 1  | `i_ano_compt`             | int64   | Ano de competência                                                                        |
| 2  | `i_mes_compt`             | int64   | Mês de competência (1–12)                                                               |
| 3  | `i_estab_cnes`            | int64   | Código CNES do estabelecimento (chave nacional padronizada)                               |
| 4  | `i_desc_sigla_estab_cnes` | text    | Sigla do hospital (`HRS`, `HRG`, `HRSM`, etc.)                                       |
| 5  | `i_desc_regiao_saude`     | text    | Região de Saúde do estabelecimento (1 das 7 regiões do DF + categorias administrativas) |
| 6  | `i_desc_espec_leito`      | text    | Especialidade do leito utilizado                                                           |
| 7  | `i_faixa_etaria`          | text    | Faixa etária do paciente em formato técnico (`"00_<_01"`, `"01_<_05"`, ...)          |
| 8  | `i_desc_sexo`             | text    | Sexo do paciente                                                                           |
| 9  | `i_proc_realizado`        | int64   | Código SIGTAP do procedimento realizado                                                   |
| 10 | `i_desc_proc_realizado`   | text    | Descrição do procedimento SIGTAP                                                         |
| 11 | `i_desc_grupo`            | text    | Grupo de procedimento (agregado de alto nível)                                            |
| 12 | `i_cid_principal`         | text    | Código CID-10 do diagnóstico principal                                                   |
| 13 | `i_desc_cid_principal`    | text    | Descrição do CID principal                                                               |
| 14 | `i_desc_car_int_atend`    | text    | Caráter da internação (`URGENCIA`, `ELETIVA`, ...)                                  |
| 15 | `i_desc_complex_proc`     | text    | Complexidade do procedimento (`Alta Complexidade`, `Média Complexidade`, ...)         |
| 16 | `i_qtd_aih`               | int64   | **Sempre 1.** Cada linha é uma AIH.                                                 |
| 17 | `i_desc_radf_res`         | text    | Região Administrativa do DF onde o paciente reside                                        |
| 18 | `i_desc_tipo_financ`      | text    | Tipo de financiamento da AIH (Federal, Próprio, Complementar)                             |
| 19 | `i_partos`                | text    | `"Sim"` quando o procedimento é de parto, nulo caso contrário                          |
| 20 | `i_cirurgias`             | text    | `"Sim"` quando o procedimento é cirúrgico, nulo caso contrário                        |
| 21 | `i_desc_obito`            | text    | `"Com óbito"` ou `"Sem óbito"`                                                       |
| 22 | `i_desc_munic_res`        | text    | Município de residência do paciente                                                      |
| 23 | `i_desc_uf_res`           | text    | UF de residência do paciente (DF, GO, etc.)                                               |
| 24 | `i_val_total_aih`         | decimal | Valor total da AIH em R$                                                                   |
| 25 | `i_qtd_diaria_pac`        | int64   | Quantidade de dias internado                                                               |
| 26 | `i_qtd_diaria_uti`        | int64   | Quantidade de dias em UTI                                                                  |

### 4.1 Mapeamento para o modelo dimensional

O Power Query renomeia todas as 26 colunas para nomes em Title Case (ex.: `i_ano_compt` → `Ano Competência`, `i_val_total_aih` → `Valor AIH`). O mapeamento completo está no `partition` da `fato_atendimento` em `relatorio/analise.SemanticModel/definition/tables/fato_atendimento.tmdl`.

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

Tratamento no Power Query (Fase 1) — ver `docs/decisoes_de_modelagem.md` §6.3.

### 5.4 Faixa etária em formato técnico

`i_faixa_etaria` vem como `"00_<_01"`, `"01_<_05"`, ..., `"80_<_+_"`. A `dim_detalhes` normaliza para forma legível (`"0 a 1 ano"`, `"1 a 5 anos"`, ..., `"80+ anos"`) via cascata de substituições em Power Query. Filtros DAX (incluindo KPIs K15 e K16) usam **o valor normalizado**, não o bruto.

### 5.5 21% de pacientes sem RA mapeada

Aproximadamente 21% das internações têm `i_desc_radf_res` nulo ou vazio. Predominantemente são pacientes do entorno metropolitano de Goiás atendidos na rede DF. Não tentar imputar — a invisibilidade é um achado de relevância para o controle social e está modelado como KPI dedicado (K10 Cobertura RA Mapeada em `docs/kpis_okrs.md` §2.3).

---

## 6. Como regenerar os arquivos

A camada de ingestão é idempotente. Para reconstruir todos os CSVs do zero:

```bash
cd src/ingestion
uv sync
uv run main.py
```

Detalhes em `src/ingestion/README.md`. Arquivos anuais já presentes em `data/raw/` são pulados — para forçar redownload de um ano específico, apagar o `dados_YYYY.csv` correspondente antes de rodar.

---

## 7. Versão dos dados

Este projeto usa o **snapshot baixado em 2026-06-09** da API SUS-DF. A API publica dados acumulativos por competência, com defasagem de 30–60 dias da competência real. Re-rodar a ingestão em data posterior pode trazer:

- Linhas adicionais de meses já incluídos (ajustes retroativos de AIH).
- Linhas de meses ainda não cobertos (avanço do mês de fechamento).

Para reproducibilidade analítica, recomenda-se preservar o `dados_concatenados.csv` usado em cada apresentação ou relatório.
