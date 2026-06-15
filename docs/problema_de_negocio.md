# Problema de Negócio

> Documento de definição. Estabelece o cenário, a pergunta central, os consumidores do dashboard, as hipóteses iniciais e o critério de sucesso do projeto.

## 1. Cenário

O **Conselho de Saúde do Distrito Federal (CSDF)** é o órgão colegiado de caráter permanente e deliberativo previsto na Lei nº 8.142/1990, com a função de **fiscalizar e auditar a aplicação dos recursos do SUS no Distrito Federal**. Sua composição é paritária: representantes de usuários (50%), trabalhadores da saúde (25%) e gestores/prestadores (25%). Para exercer essa função, o Conselho precisa de evidência sistemática sobre o desempenho da rede pública — não na escala operacional do dia a dia, mas na escala plurianual em que melhorias ou deteriorações estruturais ficam visíveis.

Hoje, a leitura do desempenho da rede SUS-DF pelo Conselho depende de relatórios pontuais produzidos pela SES-DF, em formatos não comparáveis entre si e sem séries temporais consolidadas. A análise comparativa entre exercícios fica restrita ao Plano Plurianual de Saúde, com defasagem de meses até virar consulta utilizável.

Este projeto assume o papel da **equipe técnica de BI a serviço do CSDF**, com o mandato de construir um painel analítico que sirva como instrumento permanente de vigilância qualificada sobre a produção hospitalar do SUS no DF.

## 2. Pergunta-âncora

> **A saúde pública hospitalar do Distrito Federal melhorou ou piorou entre 2022 e 2025? E os gastos públicos, evoluem de forma sustentável?**

Toda métrica, visual e narrativa do dashboard responde a alguma decomposição dessa pergunta.

### 2.1 Perguntas derivadas

1. **Produção** — O volume de internações cresce, estabiliza ou cai? A rede está absorvendo mais demanda, igual demanda ou menos demanda do que em 2022?
2. **Qualidade assistencial** — A taxa de mortalidade hospitalar está em queda, estável ou em alta? Há populações cuja mortalidade evolui em descompasso com a média?
3. **Eficiência financeira** — O custo médio por internação cresce acima da produção? O gasto público está mais bem aplicado, ou apenas maior?
4. **Equidade territorial** — Há regiões administrativas que pioraram enquanto outras melhoraram? O entorno metropolitano (Goiás) continua sendo absorvido sem mapeamento?
5. **Resolutividade** — A rede está deslocando o mix de produção para procedimentos de alta complexidade, sinal de capacidade resolutiva mais forte?

## 3. Stakeholders e personas

| Persona                                                                         | Papel no Conselho                                 | O que busca no painel                                                          | Frequência      |
| ------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------- |
| **Presidente do CSDF / Mesa Diretora**                                    | Coordenação executiva do colegiado              | Visão consolidada para abrir reuniões plenárias e responder à imprensa     | Mensal           |
| **Câmaras Técnicas (Regulação, Epidemiologia, Controle e Auditoria)** | Análises temáticas e pareceres                  | Detalhamento por dimensão (CID, RA, financiamento) e séries históricas      | Quinzenal        |
| **Conselheiros Regionais**                                                | Representação territorial                       | Recorte por região de saúde / RAs específicas que monitoram                 | Conforme demanda |
| **Sociedade civil, imprensa, academia**                                   | Controle social externo, divulgação científica | Leitura de transparência: indicadores macro e tendências em formato público | Pontual          |

A **SES-DF figura como entidade auditada**, não como consumidora primária — embora o painel sirva também a ela como ferramenta de prestação de contas.

## 4. Hipóteses iniciais

A análise exploratória (em `src/EDA/analise_exploratoria.ipynb`) levantou quatro hipóteses que o dashboard precisa confirmar ou refutar:

- **H1: Produção em alta de baixa intensidade.** O volume de internações cresce de forma moderada ano sobre ano, possivelmente puxado pelo envelhecimento populacional, não por aumento de incidência aguda.
- **H2: Mortalidade hospitalar estável em torno de 3%.** A taxa-baseline de 3,05% observada na EDA não apresenta tendência clara de queda; concentra-se desproporcionalmente em idosos.
- **H3: Custo unitário em alta.** O valor médio por internação cresce acima da inflação, sinalizando deslocamento para procedimentos mais caros — não necessariamente desperdício, mas necessita auditoria.
- **H4: Carga não-mapeada do entorno persistente.** Aproximadamente 21% das internações registradas no SUS-DF são de pacientes residentes fora do DF (entorno metropolitano), sem que isso esteja refletido no planejamento territorial publicado pela SES-DF.

## 5. Recorte e escopo

- **Janela temporal:** competências de **janeiro/2022 a dezembro/2025** (4 anos completos). Dados de 2026 são parciais (até maio) e ficam **excluídos por padrão** dos cálculos, evitando viés em comparações YoY.
- **Recorte territorial:** rede hospitalar SUS sediada no Distrito Federal. Pacientes do entorno metropolitano (UF ≠ DF) entram como ponto de atenção em página dedicada, não como filtro padrão.
- **Granularidade:** competência mensal × estabelecimento × procedimento × CID × perfil demográfico × território de residência.
- **Fora do escopo:** atenção primária (não há AIH para isso), exames ambulatoriais, indicadores de listas de espera, dados nominais de pacientes.

## 6. Critério de sucesso

O projeto entrega valor para o Conselho se, ao final, o painel cumprir simultaneamente os seis critérios abaixo:

1. **Cobertura da pergunta-âncora.** Todas as cinco perguntas derivadas (§2.1) são respondíveis em até três cliques.
2. **Comparação plurianual obrigatória.** Cada KPI macro exibe valor de referência (2022 ou 2024) e variação até 2025, em magnitude e direção.
3. **Disponibilidade temporal granular.** Variações YoY e MoM estão disponíveis para os indicadores principais ao longo de todos os meses da janela.
4. **Segregação por papel.** Pelo menos dois perfis de Row-Level Security funcionam, demonstrando que o painel pode ser usado por conselheiros regionais sem precisar duplicar relatórios.
5. **Auditabilidade.** Toda métrica exibida tem fórmula documentada e rastreável em `docs/kpis_okrs.md`; todo número da apresentação é reproduzível abrindo o `.pbip`.
6. **Versionamento.** Repositório GitHub público, com `.pbip` versionado em TMDL e commits significativos, permite que qualquer câmara técnica do CSDF audite a construção do indicador antes de citá-lo.
