# Análise Hospitalar SUS-DF Hospitalar

Este repositório contém o pipeline de Engenharia de Dados e Business Intelligence para extração, higienização, transformação e modelagem dimensional dos dados de internações e atendimentos hospitalares do Sistema Único de Saúde (SUS) no Distrito Federal e Entorno assim como o relatório correspondente de Business Intelligence.

O objetivo do projeto é transformar registros públicos transacionais em um ecossistema analítico de alta performance para monitoramento de indicadores de saúde pública.

## Arquitetura do Modelo (Star Schema)

A modelagem de dados segue rigorosamente a metodologia de Ralph Kimball, estruturada em um modelo estrela focado em performance de compressão e velocidade em consultas analíticas no motor do Power BI.

---
[Modelagem de Dados - DrawDB](https://www.drawdb.app/editor?shareId=6fe92f7fac81a8f17a74b9028610b5f5)

> ![Star Schema](img\modelagem.png)

### Otimização Estrutural: Junk Dimension (`dim_detalhes`)

Para evitar a redundância de dados e manter a tabela fato puramente numérica e performática, implementou-se uma **Junk Dimension** chamada `dim_detalhes`.

* Atributos textuais e perfis socio-clínicos de baixa cardinalidade foram extraídos da tabela fato e consolidados através de uma mesclagem multi-coluna no Power Query.
* **Campos Agrupados:** `Sexo`, `Faixa Etária`, `Especialidade de Leito`, `Caráter de Internação ou Atendimento`, `Complexidade do Procedimento` e `Descrição Tipo Financiamento`.
* **Impacto:** Milhares de linhas repetidas de texto bruto foram colapsadas em **~1200 combinações únicas de perfis**, reduzindo drasticamente o tamanho do arquivo final e otimizando os joins.

### Governança de Chaves Substitutas (Surrogate Keys)

Com o objetivo de blindar o modelo contra falhas, chaves vazias ou alterações nas chaves naturais dos sistemas transacionais do SUS, foram criadas chaves substitutas artificiais organizadas por faixas numéricas estritas no pipeline de ETL:

* **`ID Município`** (`dim_municipio_residencia`): Iniciando em **100**
* **`ID RA`** (`dim_ra_residencia`): Iniciando em **200**
* **`ID Detalhes`** (`dim_detalhes`): Iniciando em **300**
* **`ID Atendimento`** (`fato_atendimento`): Chave primária da Fato iniciando em **1000** com o prefixo alfanumérico **`AT`** (ex: `AT1000`, `AT1001`...), garantindo uma identificação exclusiva para auditorias de registros.

---

## Dicionário de Tabelas do Modelo

### Tabela Fato

* **`fato_atendimento`**: Centraliza os IDs das dimensões e armazena as métricas quantitativas e financeiras da produção hospitalar (`Quantidade de AIH`, `Valor AIH`, `Quantidade de Diárias do Paciente` e `Quantidade de Diárias UTI`), além de flags lógicas de desfecho (`Parto`, `Cirurgia`, `Óbito`).

### Tabelas Dimensão

* **`dim_detalhes`**: Junk Dimension contendo o perfil demográfico, administrativo e o nível de complexidade do atendimento. Inclui tratamento de strings para correta exibição e ordenação de faixas etárias.
* **`dim_estabelecimento`**: Cadastro das unidades hospitalares do DF (mapeando o código CNES, a sigla oficial da unidade como HRS, HRG, HRSM, e a sua respectiva Região de Saúde).
* **`dim_procedimento`**: Tabela de procedimentos realizados com base na tabela unificada do SUS - SIGTAP (ID, Descrição e Grupo de Procedimento).
* **`dim_diagnostico`**: Mapeamento de patologias codificadas internacionalmente via CID Principal.
* **`dim_data`**: Dimensão calendário analítica. Como a granularidade original do SUS opera por Competência (Ano/Mês), as datas foram normalizadas inserindo o dia padrão (`01/MM/AAAA`) para habilitar nativamente as funções de inteligência de tempo (*Time Intelligence*) do DAX.
* **`dim_municipio_residencia`**: Origem geográfica externa do paciente atendido (Município e UF).
* **`dim_ra_residencia`**: Regiões Administrativas do Distrito Federal, permitindo o rastreamento interno de demandas territoriais de saúde.

---

## Pipeline de Dados & Estrutura do Repositório

O projeto está dividido em duas camadas principais organizadas no repositório:

### 1. Camada de Ingestão (`/ingestion`)

Responsável pela extração programática dos dados públicos diretamente da API da Saúde-DF e pela consolidação multiano (2022 a 2026) num arquivo unificado via Pandas.

* Para detalhes de configuração do ambiente virtual, dependências e instruções de execução da extração, consulte o [README exclusivo da Camada de Ingestão](/ingestion/README.md).

### 2. Camada de Modelagem (`/analise_pbip`)

Contém os arquivos de metadados do Power BI no formato **PBIP**.

* Toda a estrutura de tabelas, relacionamentos (`1:*` unidirecionais) e o M code de transformação do Power Query encontram-se expostos na pasta `analise.SemanticModel/definition/` em formato declarativo **TMDL**, facilitando o versionamento por Git, code reviews e o desenvolvimento colaborativo.
