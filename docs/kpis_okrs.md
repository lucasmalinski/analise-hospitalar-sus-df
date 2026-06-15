# KPIs e OKRs

> Catálogo formal dos indicadores e objetivos do projeto. Cada KPI traz fórmula, unidade, baseline calculável da EDA, meta, polaridade (qual direção é desejável) e página do dashboard onde aparece. Cada OKR vincula seus KRs explicitamente aos KPIs.
>
> Referência cruzada: `docs/problema_de_negocio.md` define a pergunta-âncora que orienta todos os indicadores aqui.

---

## 1. Visão geral

O projeto define **11 KPIs** e **2 OKRs**. A decisão é complexa porque a pergunta-âncora *"a saúde pública hospitalar do DF melhorou ou piorou entre 2022 e 2025?"* exige cobertura simultânea de cinco eixos: produção, qualidade assistencial, eficiência financeira, equidade territorial e resolutividade. Cobrir cinco eixos com poucos KPIs deixaria o painel raso; cobri-los com indicadores demais polui os cartões executivos. Onze é o equilíbrio entre as duas tensões.

Sete dos KPIs aparecem na **Visão Executiva (página principal)** com o padrão de cartão YoY descrito no item 3. Os quatro restantes ficam em páginas temáticas (Populações Vulneráveis e Geográfica), mantendo cada visão coerente com sua persona consumidora.

### 1.1 Janela e baseline

Todos os KPIs operam sobre a janela **jan/2022–dez/2025** (4 anos completos). Dados de 2026 são parciais e ficam fora dos cálculos por padrão. O período base para comparações YoY é o **mesmo período do ano calendário anterior** (semântica DAX `SAMEPERIODLASTYEAR`), não o ano calendário inteiro, isso é o que permite comparações coerentes mesmo com filtros parciais de período no painel.

### 1.2 Polaridade dos indicadores

Indicadores não têm todos a mesma direção desejável. A polaridade define a cor do delta nos cartões YoY:

- **DOWN é bom** (verde se diminuir, vermelho se aumentar): K04 Mortalidade, K07 Custo Médio, K13 Tempo Médio Permanência, K15 Mortalidade Infantil, K16 Mortalidade Idosos.
- **UP é bom** (verde se aumentar, vermelho se diminuir): K10 Cobertura RA Mapeada.
- **Ambígua / informativa** (cor neutra sempre): K01 Total Internações, K03 Volume Médio Mensal, K09 Valor Total Investido, K11 Concentração Top-3, K14 Taxa de Uso de UTI.

A polaridade é registrada na coluna correspondente de cada KPI abaixo.

---

## 2. Catálogo de KPIs

### 2.1 Visão Executiva (página principal) — 7 KPIs

| Código       | Nome                           | Fórmula                                                     | Unidade  | Baseline (EDA)       | Meta 2026                                 | Polaridade            |
| ------------- | ------------------------------ | ------------------------------------------------------------ | -------- | -------------------- | ----------------------------------------- | --------------------- |
| **K01** | Total de Internações         | `SUM(fato_atendimento[Quantidade de AIH])`                 | nº      | 929k (2022–25)      | manter ±5% YoY                           | informativa           |
| **K03** | Volume Médio Mensal           | `K01 / DISTINCTCOUNT(dim_data[Ano-Mês])` no contexto      | nº/mês | ~19,3 mil (2022–25) | manter ±5% YoY                           | informativa           |
| **K04** | Taxa de Mortalidade Hospitalar | `DIVIDE([Total Óbitos], [Total Internações])`           | %        | 3,05% (2022–25)     | ≤ 3,00% (gauge)                          | **DOWN é bom** |
| **K07** | Custo Médio por Internação  | `DIVIDE([Total Valor AIH], [Total Internações])`         | R$       | 1.516 (2022–25)     | crescimento YoY ≤ 5%                     | **DOWN é bom** |
| **K09** | Valor Total Investido          | `SUM(fato_atendimento[Valor AIH])`                         | R$       | 1,41 bi (2022–25)   | crescimento real ≤ 5% a.a.               | informativa           |
| **K13** | Tempo Médio de Permanência   | `DIVIDE([Total Diárias Paciente], [Total Internações])` | dias     | calculável da EDA   | reduzir 5% vs 2024                        | **DOWN é bom** |
| **K14** | Taxa de Uso de UTI             | `DIVIDE([Internações com UTI], [Total Internações])`   | %        | calculável da EDA   | monitorar (alerta acima do baseline +2pp) | informativa           |

Justificativa do conjunto: os 7 KPIs respondem em sequência narrativa à pergunta-âncora. K01 e K03 mostram a escala da demanda; K04 mostra se a rede entrega resultado clínico; K07 e K09 mostram se o gasto público é sustentável; K13 mostra eficiência operacional; K14 expõe pressão sobre o leito mais crítico.

### 2.2 Página "Populações Vulneráveis" — 2 KPIs novos + K04 + K14 como referência

| Código       | Nome                            | Fórmula                                                                                                           | Unidade | Baseline (EDA) | Meta 2026           | Polaridade            |
| ------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------- | -------------- | ------------------- | --------------------- |
| **K15** | Mortalidade Infantil (0–1 ano) | `CALCULATE([Taxa Mortalidade %], dim_detalhes[Faixa Etária] = "0 a 1 ano")`                                     | %       | calculável    | reduzir 10% vs 2024 | **DOWN é bom** |
| **K16** | Mortalidade em Idosos (60+)     | `CALCULATE([Taxa Mortalidade %], dim_detalhes[Faixa Etária] IN { "60 a 69 anos", "70 a 79 anos", "80+ anos" })` | %       | calculável    | reduzir 5% vs 2024  | **DOWN é bom** |

Justificativa da página: a EDA evidencia concentração de óbitos e uso de UTI nos extremos etários (seção 8 do notebook). Sem essa página, o painel pode suavizar o achado e perder força narrativa para o controle social. K04 (Mortalidade Geral) aparece como **linha de referência visual** nos visuais.

### 2.3 Página "Geográfica" — 2 KPIs específicos + K04, K07, K09 como referência

| Código       | Nome                           | Fórmula                                                                                                                | Unidade | Baseline (EDA)  | Meta 2026 | Polaridade          |
| ------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------- | ------- | --------------- | --------- | ------------------- |
| **K10** | Cobertura RA Mapeada           | `DIVIDE(CALCULATE([Total Internações], NOT(ISBLANK(dim_ra_residencia[RA de Residência]))), [Total Internações])` | %       | ~79% (2022–25) | ≥ 85%    | **UP é bom** |
| **K11** | Concentração Top-3 Hospitais | `DIVIDE([Internações Top-3 Hospitais], [Total Internações])`                                                      | %       | calculável     | monitorar | informativa         |

Justificativa: K10 quantifica explicitamente o problema das 21% de internações sem RA mapeada — falha de governança territorial visível na EDA. K11 mede dependência sistêmica: concentração alta significa que falha em um único hospital tem impacto desproporcional sobre a rede.

### 2.4 Tabela-resumo de páginas

| Página do dashboard           | KPIs principais no topo           | KPIs auxiliares na página |
| ------------------------------ | --------------------------------- | -------------------------- |
| 1 — Visão Executiva          | K01, K03, K04, K07, K09, K13, K14 | —                         |
| 2 — Temporal & Sazonalidade   | K01, K04, K07                     | —                         |
| 3 — Populações Vulneráveis | K04, K14                          | K15, K16                   |
| 4 — Geográfica               | K04, K07, K09                     | K10, K11                   |
| 5 — Financeira & Complexidade | K07, K09, K13                     | —                         |

---

## 3. Padrão de cartão KPI com comparação temporal

Todos os cartões da Visão Executiva (e dos topos das páginas temáticas) seguem o mesmo padrão visual, implementado via **medidas de texto** (título, subtítulo) e **medidas de cor** (formatação condicional sobre a fonte do subtítulo). Não usa custom visual — usa o Card visual nativo do Power BI.

**Estrutura de cada cartão:**

```
Título: <nome do KPI>           (medida de texto fixo)
Valor:  R$ 3,11 Mi              (medida principal, formatada)
Delta:  ▲ +9,1% | R$ 2,85 Mi    (medida de texto concatenado)
        vs Ano Anterior
```

**Medida do subtítulo (exemplo, K01 Total Internações):**

```dax
KPI Internações Subtitle =
VAR _atual    = [Total Internações]
VAR _anterior = CALCULATE([Total Internações], SAMEPERIODLASTYEAR(dim_data[Data]))
VAR _delta    = _atual - _anterior
VAR _pct      = DIVIDE(_delta, _anterior)
VAR _seta     = IF(_delta >= 0, "▲", "▼")
VAR _sinal    = IF(_delta >= 0, "+", "")
RETURN
    _seta & " " & _sinal & FORMAT(_pct, "0,0%") & " | " &
    FORMAT(_anterior, "#.##0") & " vs Mesmo Período Ano Anterior"
```

**Medida de cor (exemplo, K04 Mortalidade — DOWN é bom):**

```dax
KPI Mortalidade Color =
VAR _atual    = [Taxa de Mortalidade %]
VAR _anterior = CALCULATE([Taxa de Mortalidade %], SAMEPERIODLASTYEAR(dim_data[Data]))
VAR _delta    = _atual - _anterior
RETURN
    SWITCH(
        TRUE(),
        _delta < 0, "#0E7C7B",    -- verde teal (melhorou)
        _delta > 0, "#C7185A",    -- magenta (piorou)
        "#666666"                 -- cinza (sem mudança)
    )
```

Para KPIs de **polaridade inversa** (UP é bom — K10), trocar os hexes de verde e vermelho. Para KPIs **informativos** (sem polaridade), retornar sempre `#0E7C7B` (teal neutro).

Cada um dos 11 KPIs terá um par dessas duas medidas na tabela `_Medidas`, em `displayFolder = "06 Cartões KPI"`.

---

## 4. OKRs

### 4.1 OKR 1 — Manter a mortalidade hospitalar do SUS-DF sob controle

**Objective:** Em 2026, o Conselho de Saúde do DF audita a estabilização e gradual redução da mortalidade hospitalar atendida pelo SUS-DF, com atenção especial às populações etárias vulneráveis (extremos da pirâmide).

| KR               | Descrição                                               | Meta quantitativa                                           | KPI vinculado |
| ---------------- | --------------------------------------------------------- | ----------------------------------------------------------- | ------------- |
| **KR 1.1** | Manter Taxa de Mortalidade Hospitalar global sob controle | ≤**3,00%** até Dez/2026 (baseline 3,05% em 2022-25) | **K04** |
| **KR 1.2** | Reduzir Taxa de Mortalidade em Idosos (60+)               | **−5%** em termos relativos vs baseline 2024         | **K16** |
| **KR 1.3** | Reduzir Taxa de Mortalidade Infantil (0–1 ano)           | **−10%** em termos relativos vs baseline 2024        | **K15** |

Por que escolhido: K04 é o indicador-mãe de qualidade assistencial em qualquer sistema hospitalar; KR 1.2 e 1.3 endereçam diretamente o achado da EDA de concentração de óbitos nos extremos etários. Esse OKR justifica a existência da página Populações Vulneráveis.

### 4.2 OKR 2 — Garantir sustentabilidade fiscal da rede hospitalar

**Objective:** Em 2026, o Conselho de Saúde do DF audita que o crescimento dos gastos hospitalares no SUS-DF acompanha a inflação observada e que ganhos de eficiência operacional são gerados de forma contínua.

| KR               | Descrição                                                                  | Meta quantitativa                                            | KPI vinculado |
| ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------- |
| **KR 2.1** | Manter crescimento YoY do Custo Médio por Internação dentro da inflação | ≤**5%** em 2026 (proxy de IPCA acumulado)             | **K07** |
| **KR 2.2** | Reduzir Tempo Médio de Permanência                                         | **−5%** em termos relativos vs baseline 2024          | **K13** |
| **KR 2.3** | Manter Valor Total Investido com crescimento real moderado                   | crescimento real (descontada inflação) ≤**5%** a.a. | **K09** |

Por que escolhido: K07 e K09 cobrem a dimensão financeira em duas escalas (unitária e total). KR 2.2 (Tempo de Permanência) é um proxy clássico de eficiência operacional: permanência mais curta com mesmo desfecho clínico significa que a rede está rodando melhor.

### 4.3 Tabela de vinculação KR ↔ KPI

| KR     | KPI principal | KPI auxiliar de leitura           |
| ------ | ------------- | --------------------------------- |
| KR 1.1 | K04           | K15, K16 (decomposição etária) |
| KR 1.2 | K16           | K04 (referência de média)       |
| KR 1.3 | K15           | K04 (referência de média)       |
| KR 2.1 | K07           | K09 (escala total)                |
| KR 2.2 | K13           | K01 (escala da demanda)           |
| KR 2.3 | K09           | K07 (custo unitário)             |

Cobertura: dos 11 KPIs, 6 entram em algum KR (K04, K07, K09, K13, K15, K16). Os 5 restantes (K01, K03, K10, K11, K14) ficam como **KPIs informativos sem amarração OKR** — situação comum e legítima quando o indicador é descritivo, não de mudança ativa.

---

## 5. Velocímetro principal — especificação

O dashboard exibe, na **página Visão Executiva**, um velocímetro renderizando o **KR 1.1** (Taxa de Mortalidade Hospitalar) — escolha alinhada com o foco de auditoria do CSDF.

| Parâmetro        | Valor                       | Observação                                                              |
| ----------------- | --------------------------- | ------------------------------------------------------------------------- |
| Métrica          | `[Taxa de Mortalidade %]` | medida principal já existente                                            |
| Mínimo (eixo)    | 0%                          | piso natural do indicador                                                 |
| Máximo (eixo)    | 5%                          | piso de "fora de controle" em sistemas hospitalares públicos brasileiros |
| Target (marcador) | 3,00%                       | meta KR 1.1                                                               |
| Valor atual       | dinâmico                   | calculado conforme filtro de período ativo                               |

**Faixas de cor (conditional formatting do arco):**

| Faixa    | Intervalo      | Cor (hex)   | Significado para o CSDF                                                     |
| -------- | -------------- | ----------- | --------------------------------------------------------------------------- |
| Verde    | ≤ 3,00%       | `#0E7C7B` | Indicador dentro da meta — qualidade clínica preservada                   |
| Amarela  | 3,01% – 4,00% | `#E89A3C` | Zona de atenção — gatilho de pedido de detalhamento por câmara técnica |
| Vermelha | > 4,00%        | `#C7185A` | Zona crítica — gatilho de manifestação formal do colegiado              |

Medida de cor para o arco:

```dax
Gauge Mortalidade Color =
VAR _val = [Taxa de Mortalidade %]
RETURN SWITCH(
    TRUE(),
    _val <= 0.03,  "#0E7C7B",
    _val <= 0.04,  "#E89A3C",
    "#C7185A"
)
```
