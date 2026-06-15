# Decisões de Modelagem

> Registro técnico das decisões arquiteturais e de modelagem dimensional do projeto. Cada seção explica **o que foi feito**, **por que foi feito** e **quais alternativas foram descartadas** — com foco em auditabilidade futura.
>
> Referências cruzadas: `docs/problema_de_negocio.md` (contexto e perguntas), `docs/kpis_okrs.md` (indicadores e fórmulas), `img/modelagem.png` (diagrama visual), `README.md` (visão geral).

---

## 1. Modelo dimensional — Star Schema

A modelagem segue a **metodologia de Ralph Kimball** com um único star schema centrado em uma tabela fato e sete dimensões diretamente conectadas. Decidir entre as três alternativas clássicas (flat, snowflake, star) foi explícito:

| Alternativa                                                           | Por que foi descartada                                                                                                                                                                                                                                                                      |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Flat** (única tabela com 26 colunas, sem dimensões)         | O dataset bruto já vem nesse formato. Mantê-lo flat duplicaria atributos textuais em milhões de linhas, eliminaria a possibilidade de aplicar Row-Level Security por dimensão e geraria arquivos com muito mais peso após import no Power BI. Rejeitado por compressão e performance. |
| **Snowflake** (hierarquias normalizadas em múltiplos níveis) | Para o domínio do SUS-DF, a normalização adicional não traz ganho — não há atributos repetidos entre dimensões que mereçam ser extraídos. Acrescentaria joins desnecessários ao motor VertiPaq sem benefício de governança. Rejeitado por complexidade sem retorno.            |
| **Star schema** (escolhido)                                     | Equilíbrio entre normalização (cada conceito do negócio é uma dimensão dedicada) e performance (dimensões pequenas e fato magro).                                                                                                                                                    |

O diagrama visual do modelo está em `img/modelagem.png` e na versão interativa em [DrawDB](https://www.drawdb.app/editor?shareId=6fe92f7fac81a8f17a74b9028610b5f5).

---

## 2. Tabela fato — `fato_atendimento`

### 2.1 Granularidade

Cada linha da fato representa **uma autorização de internação hospitalar (AIH) agregada na competência mensal**, com chave artificial `ID Atendimento`. A granularidade da fato é portanto:

> **competência (mês/ano) × estabelecimento × procedimento × CID principal × perfil clínico-demográfico × território de residência**

A granularidade é mensal porque é a granularidade nativa do dado público SUS — a API `saude.df.gov.br` não expõe data exata da internação, apenas mês e ano de competência. Tentar inferir data diária introduziria ruído sem base factual.

### 2.2 Métricas armazenadas

Quatro métricas numéricas aditivas: `Quantidade de AIH`, `Valor AIH`, `Quantidade de Diárias do Paciente` e `Quantidade de Diárias UTI`. A primeira é constante igual a 1 por linha (cada linha representa uma internação) — `SUM` e `COUNTROWS` são equivalentes para contagem. Decidimos manter explicitamente em vez de implícita para legibilidade das medidas DAX.

### 2.3 Flags textuais — `Parto`, `Cirurgia`, `Óbito`

Os três campos vêm como string no dataset bruto:

- `Parto`: `"Sim"` ou nulo
- `Cirurgia`: `"Sim"` ou nulo
- `Óbito`: `"Com óbito"` ou `"Sem óbito"`

A tentação inicial é converter para inteiro (1/0). **Não fizemos**, por três motivos:

1. As medidas DAX que filtram esses campos (em `docs/kpis_okrs.md` §2.1) ficam mais legíveis com a comparação textual original: `CALCULATE([Total Internações], fato_atendimento[Óbito] = "Com óbito")` é autodocumentado.
2. Conversão para 1/0 induz a usar `SUM` direto, que é matematicamente equivalente mas perde o significado semântico ao ler a fórmula.
3. Custo de armazenamento desprezível — VertiPaq comprime esses três campos com dicionário binário sem impacto perceptível.

### 2.4 Chave primária artificial — `ID Atendimento`

Cada linha recebe um identificador único sintético no formato `AT` + índice sequencial iniciando em 1000 (ex.: `AT1000`, `AT1001`, ...). Criada no Power Query via `Table.AddIndexColumn`.

**Por que não usar chaves naturais?** Os campos do SUS (`CNES`, `CID`, `competência`) não formam chave única em conjunto — pacientes diferentes podem gerar AIHs com a mesma combinação. Tentar inventar uma chave composta seria frágil; a sintética é blindada contra mudanças nas chaves naturais dos sistemas transacionais do SUS.

---

## 3. Tabelas dimensão

O modelo tem **7 dimensões** conectadas à fato por relacionamentos `1:N` unidirecionais (filtro fluindo de dimensão para fato):

| Dimensão                    | PK                            | Cardinalidade aproximada         | Origem            |
| ---------------------------- | ----------------------------- | -------------------------------- | ----------------- |
| `dim_data`                 | `Data`                      | ~60 (5 anos × 12 meses)         | Power Query + DAX |
| `dim_detalhes` (Junk)      | `ID Detalhes`               | ~1.200 combinações             | Power Query       |
| `dim_estabelecimento`      | `CNES Estabelecimento`      | ~30 hospitais                    | Power Query       |
| `dim_diagnostico`          | `CID Principal`             | ~5.000 CIDs distintos            | Power Query       |
| `dim_procedimento`         | `ID Procedimento Realizado` | ~3.000 procedimentos             | Power Query       |
| `dim_ra_residencia`        | `ID RA`                     | 56 RAs (após trim — ver §6.3) | Power Query       |
| `dim_municipio_residencia` | `ID Município`             | ~300 municípios                 | Power Query       |

### 3.1 Junk Dimension — `dim_detalhes`

A decisão mais relevante de modelagem do projeto. Seis atributos textuais de **baixa cardinalidade individual** foram extraídos da fato e consolidados em uma dimensão "lixeira" (Junk):

- `Sexo`
- `Faixa Etária`
- `Especialidade de Leito`
- `Caráter de Internação ou Atendimento`
- `Complexidade do Procedimento`
- `Descrição Tipo Financiamento`

**Racional.** Se cada um virasse uma dimensão dedicada, teríamos 6 dimensões adicionais com poucas linhas cada — sobrecarregando o painel de campos do Power BI sem ganho analítico (raramente alguém quer filtrar por "Sexo" e só por "Sexo" em isolamento). Se ficassem na fato, a tabela teria 985k linhas com 6 colunas de texto redundante.

A solução Junk colapsa as **combinações únicas observadas** (cerca de 1.200 combinações reais em 985k linhas) em uma dimensão compacta. A fato armazena apenas o `ID Detalhes` correspondente.

**Por que não criar 6 dimensões separadas?** Foi considerado. Descartado porque (1) atributos como `Sexo` e `Faixa Etária` são quase sempre filtrados juntos no fluxo de análise epidemiológica, e (2) a explosão de tabelas pequenas no painel de campos do Power BI atrapalha a UX de quem usa o modelo.

### 3.2 Outras dimensões

`dim_estabelecimento` mantém o **CNES (Cadastro Nacional de Estabelecimentos de Saúde)** como chave natural — é um identificador estável, padronizado nacionalmente, e usá-lo como surrogate seria reinventar a roda.

`dim_diagnostico` usa o **CID Principal** (Classificação Internacional de Doenças) também como chave natural, pelo mesmo motivo.

`dim_procedimento` usa o **código SIGTAP** (Sistema de Gerenciamento da Tabela de Procedimentos do SUS) — mesmo argumento.

`dim_ra_residencia` e `dim_municipio_residencia` recebem **surrogate keys** porque os nomes textuais das RAs e municípios são instáveis (mudanças de grafia, acentuação, espaços em branco) — ver §4 e §6.3.

---

## 4. Política de Surrogate Keys

As três tabelas que recebem chave artificial seguem **faixas numéricas estritas** documentadas no Power Query:

| Tabela                              | Início da faixa | Padrão                             |
| ----------------------------------- | ---------------- | ----------------------------------- |
| `dim_municipio_residencia`        | 100              | inteiro sequencial                  |
| `dim_ra_residencia`               | 200              | inteiro sequencial                  |
| `dim_detalhes`                    | 300              | inteiro sequencial                  |
| `fato_atendimento.ID Atendimento` | 1000             | prefixo `AT` + inteiro sequencial |

**Por que faixas estritas em vez de iniciar em 1?** Para que, em uma futura inspeção de dados, qualquer ID isolado torne explícita a tabela de origem. Ver `300` significa imediatamente `dim_detalhes`; ver `AT1547` significa fato. É uma convenção de governança que custa zero e ajuda em qualquer debug futuro do modelo.

---

## 5. `dim_data` — calendário híbrido (Power Query + DAX)

A `dim_data` é construída em **duas camadas**:

1. **Power Query (existente):** seleciona distintos de `Mês Competência` e `Ano Competência`, monta o campo `Data` no formato `01/MM/AAAA` (todo dia 1º do mês — convenção neutra para inteligência de tempo DAX).
2. **DAX (a ser adicionada na Fase 1):** colunas calculadas que enriquecem o calendário com Ano, Mês Num, Nome Mês (com `sortByColumn`), Mês Curto, Ano-Mês, Trimestre, Trimestre Label e Ano-Trimestre — necessárias para os visuais temporais (heatmap, ribbon chart, small multiples).

**Por que híbrido em vez de calendário 100% DAX?** Uma `dim_data` totalmente em DAX (via `CALENDAR`) traria granularidade diária — desnecessária quando o dado nativo é mensal. Calcular dia-a-dia geraria ~1.825 linhas em vez de ~60 e habilitaria filtros sem sentido no domínio (filtrar "10 de março" não significa nada quando a competência é mensal).

**Por que não 100% Power Query?** Adicionar funções como `FORMAT([Data], "mmmm")` no Power Query exigiria reescrever a query a cada ajuste; em DAX, são colunas calculadas independentes que podem ser ajustadas sem refresh.

**Marcação obrigatória.** No Power BI Desktop, `dim_data` precisa ser marcada como **Tabela de Datas** (Modeling → Mark as date table → coluna `Data`). Sem isso, as funções de time intelligence (`TOTALYTD`, `SAMEPERIODLASTYEAR`) não operam corretamente em alguns contextos.

---

## 6. Power Query — decisões

### 6.1 Parâmetro `CaminhoBase`

Para portabilidade entre máquinas, o caminho do CSV é injetado via parâmetro `CaminhoBase`. Cada colaborador configura o seu uma vez (instruções em `docs/tmdl_setup/COMO_INSTALAR.md`).

**Por que parâmetro e não OneDrive/SharePoint compartilhado?** Soluções de cloud sync (OneDrive, Google Drive) introduzem conflito com o git em pastas versionadas — comprovado pelos travamentos de `.git/index.lock` observados em sessões anteriores do projeto. O parâmetro local é a única solução que separa de fato versionamento (git) e dado local (disco do colaborador).

### 6.2 Query base referenciada — `_Base` (Fase 1)

Hoje, cada uma das 8 tabelas refaz o pipeline completo: `Csv.Document → PromoteHeaders → ChangedType → RenameColumns`. Em um refresh, o CSV de 985k linhas é lido **oito vezes**.

A Fase 1 introduz uma query staging `_Base` (com `Enable Load = false`) que executa essas etapas comuns uma única vez; as dimensões e a fato passam a referenciá-la. Ganho esperado: refresh ~8× mais rápido em qualquer alteração de tipagem ou renome.

### 6.3 Trim obrigatório em `dim_ra_residencia` (Fase 1)

O dataset bruto contém duplicatas de RA por **trailing spaces** — exemplo: `Jardim Botânico` e `Jardim Botânico ` (com espaço final) são linhas distintas no CSV. A EDA (cell #14 do notebook) já registrou: o número de RAs distintas ultrapassa as 35 oficiais do DF justamente por isso.

Sem tratamento, qualquer filtro DAX (incluindo o do Row-Level Security em §8) falharia ao comparar literais: `[RA de Residência] = "Plano Piloto"` não pegaria `"Plano Piloto "`.

**Solução implementada na Fase 1:** adicionar uma etapa `Table.TransformColumns` com `Text.Trim` na coluna `RA de Residência` da `dim_ra_residencia` (e replicar em `fato_atendimento` antes do merge para preservar consistência).

### 6.4 Tratamento de `Faixa Etária`

A `Faixa Etária` chega do CSV em formato técnico (`"00_<_01"`, `"01_<_05"`...) e é normalizada via cascata de `Table.ReplaceValue` em `dim_detalhes` para a forma legível (`"0 a 1 ano"`, `"1 a 5 anos"`, ..., `"80+ anos"`). Decisão importante para os KPIs K15 e K16 (`docs/kpis_okrs.md` §2.2): os literais usados no filtro DAX (`"0 a 1 ano"`, `"60 a 69 anos"`, etc.) **precisam bater exatamente** com os valores normalizados.

---

## 7. Tabela `_Medidas` separada

Todas as ~30 medidas DAX do projeto ficam em uma **tabela dedicada `_Medidas`** (sem partição de dados, apenas com coluna placeholder oculta). Vantagens:

- Painel de campos visualmente organizado — medidas longe de colunas de dados.
- Organização por pasta de display (`01 Básicas`, `02 Time Intelligence`, `03 Variações`, `04 Filtros`, `05 Taxas`, `06 Cartões KPI`).
- Próximo desenvolvedor encontra tudo em um único lugar.

Em formato TMDL, a tabela é declarada manualmente — o Power BI Desktop não tem UI nativa para criá-la, mas detecta e respeita uma vez declarada.

---

## 8. Row-Level Security (RLS)

### 8.1 Decisão de papéis

Implementamos **9 papéis** distintos que simulam o organograma do CSDF (consumidor primário do painel — ver `docs/problema_de_negocio.md` §3).

| # | Papel                                          | Tipo de filtro            | Filtro DAX                                                        |
| - | ---------------------------------------------- | ------------------------- | ----------------------------------------------------------------- |
| 1 | **Presidente / Mesa Diretora CSDF**      | sem filtro (visão total) | —                                                                |
| 2 | Câmara Técnica Regional — Central           | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Central"`    |
| 3 | Câmara Técnica Regional — Centro-Sul        | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Centro-Sul"` |
| 4 | Câmara Técnica Regional — Leste             | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Leste"`      |
| 5 | Câmara Técnica Regional — Norte             | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Norte"`      |
| 6 | Câmara Técnica Regional — Oeste             | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Oeste"`      |
| 7 | Câmara Técnica Regional — Sudoeste          | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Sudoeste"`   |
| 8 | Câmara Técnica Regional — Sul               | por Região de Saúde     | `dim_estabelecimento[Região de Saúde] = "Região Sul"`        |
| 9 | **Conselheiro Regional — Plano Piloto** | por RA de Residência     | `dim_ra_residencia[RA de Residência] = "Plano Piloto"`         |

### 8.2 Racional

Três modelos distintos de visibilidade, cobertos por um único modelo:

- **Visão total** (papel 1) — para auditoria executiva e prestação de contas externa.
- **Visão por hospital** (papéis 2–8) — para câmaras que fiscalizam capacidade instalada por região de saúde, independente de onde o paciente residia.
- **Visão por residência** (papel 9) — para conselheiro que representa um território específico e quer ver onde os pacientes da sua RA foram atendidos, independente do hospital.

Os filtros por Região de Saúde (papéis 2–8) **não restringem** as 3 categorias administrativas que aparecem em `dim_estabelecimento[Região de Saúde]` (`Privado`, `Contratado/Credenciado`, `URD`). Pacientes atendidos nessas categorias são vistos apenas pelo Presidente — comportamento desejado, já que as câmaras regionais auditam a rede pública direta.

### 8.3 Pré-requisito técnico

O papel 9 depende criticamente do **trim em `dim_ra_residencia`** descrito em §6.3. Sem o trim, o filtro literal não captura registros com espaço residual. A Fase 1 do plano técnico executa o trim antes da primeira validação de RLS.

### 8.4 Como demonstrar

Validação obrigatória via **Modeling → View as → escolher papel**. 

- `docs/rls_presidente.png` — visão total (baseline de comparação)
- `docs/rls_camara_centro_sul.png` — exemplo de corte por Região de Saúde
- `docs/rls_conselheiro_plano_piloto.png` — exemplo de corte por RA de residência

Cada print mostra a página Visão Executiva com os totais aplicáveis, evidenciando que o filtro DAX está operando.

---

## 9. Relacionamentos

Todos os 7 relacionamentos da fato com as dimensões são **`1:N` unidirecionais**, com filtro fluindo da dimensão para a fato (configuração padrão Kimball). Não há relacionamentos `many-to-many` e não há filtros bidirecionais.

A versão inicial do modelo tinha relacionamentos com nomes `AutoDetected_*` (gerados automaticamente). A Fase 1 renomeia para nomes legíveis (`Rel_Fato_DimData`, `Rel_Fato_DimDetalhes`, etc.) para facilitar manutenção e diagnóstico.
