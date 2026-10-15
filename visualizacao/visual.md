# Briefing visual — Casa das Máquinas

Design system e contexto de apresentação do dashboard. Referência inicial registrada em **15/10/2026**, a partir dos layouts, do CSS e das figuras implementadas.

Este documento preserva as decisões visuais para as próximas sessões. Leia junto com o [README.md](README.md), que concentra execução, arquitetura, fontes e fórmulas. Ao evoluir a interface, atualize aqui os padrões que mudarem.

## 1. Objetivo e direção visual

O dashboard oferece uma leitura gerencial do comércio de máquinas e peças: receita, metas, investimento em mídia, retorno, ticket, clientes e lucro. A leitura começa no resumo, passa pelos cruzamentos e termina no resultado financeiro.

A direção atual é **corporativa, clara e orientada aos dados**: fundo cinza muito claro, superfícies brancas, cabeçalho azul escuro, títulos em azul profundo e cores pontuais para distinguir medidas e estados. Espaços e bordas estabelecem a hierarquia; os valores e as curvas recebem o destaque.

Use os componentes de **Dash Bootstrap Components** para a estrutura e o **Plotly** para as visualizações. Preserve o idioma português do Brasil e a identidade presente na implementação. A marca atual é um monograma textual **CM**, seguido de **Casa das Máquinas** e **Indicadores de desempenho**.

## 2. Estrutura e sequência da primeira página

A **Visão Geral Executiva** é a única página do dashboard e abre diretamente, sem navegação por abas. As seções de mídia, mix e clientes fazem parte dessa página, junto dos KPIs, da Curva de Desacoplamento e da seção financeira final.

```text
Cabeçalho azul escuro
  CM · Casa das Máquinas                 Dados disponíveis até

Filtros: Mês atual / Ano atual · Ano · Período · Indicador do gráfico
Contador de dias com registro

Visão Geral Executiva · descrição
  [Faturamento vs. Meta] [ROAS] [Investimento] [Ticket Médio]

Cruzamento estratégico · A Curva de Desacoplamento
  Receita azul × investimento laranja · dois eixos Y · largura total

Performance de Mídia
  Meta × Google × ROAS global · largura total

Mix de Vendas & Produtos
  [Barras por faixa de ticket diário] [Bolhas de ticket por data]

Saúde de Clientes & Retenção
  [Rosca: novos / recorrentes] [Barras: investimento por registro]

Indicador selecionável · série diária
Resultados recentes · últimos 12 dias com registro

Resultado financeiro · Da receita ao lucro
  Resumo · previsto × realizado · cascata · tabela mensal · notas

Rodapé com fórmulas de ROAS e ticket
```

Este esquema representa a hierarquia, sem fixar proporções de tela. A seção financeira é a última seção de conteúdo. O alerta sobre o indicador de recorrentes aparece antes do gráfico selecionável quando aplicável.

## 3. Paleta

### Base da interface

Os quatro primeiros valores são variáveis já definidas em [assets/dashboard.css](assets/dashboard.css). Os demais são valores literais usados no CSS e nos gráficos.

| Papel | Valor | Uso atual |
| --- | --- | --- |
| `--ink` | `#17324d` | Texto principal e títulos |
| `--muted` | `#64758b` | Rótulos, explicações, notas e estados vazios |
| `--line` | `#e4eaf1` | Bordas e divisórias |
| `--surface` | `#fff` | Cards, filtros e painéis |
| Fundo da aplicação | `#f4f7fb` | Área externa aos painéis |
| Cabeçalho | `#102d47` | Faixa superior da marca |
| Texto secundário do cabeçalho | `#b2c4d6` | Subtítulo e legenda de disponibilidade |
| Azul principal | `#326bba` | Marca CM, destaques e séries principais |
| Verde | `#167d57` | Meta atingida, Google na seção de mídia, resultado positivo |
| Laranja | `#d97706` | Investimento na curva, ROAS na mídia, recorrentes |
| Verde-água | `#17a398` | Card e gráfico compacto de investimento |
| Violeta | `#8b78b8` | Card de ticket e faixas de ticket |
| Vermelho | `#c43d4a` | Meta abaixo do limite, deduções e prejuízo |
| Âmbar | `#a86709` | Atingimento próximo da meta |
| Fundo de tag | `#e8f0fb` | Tag “Resultados de e-commerce” |
| Fundo da comparação financeira | `#eef4fc` | Receita prevista e badge de atingimento |
| Fundo de tabela / resumo financeiro | `#f8fafd` | Cabeçalhos de tabela e cards financeiros |
| Grade dos gráficos novos | `#e9eef5` | Linhas horizontais discretas |

### Estados e cores das séries

As cores de série dependem do contexto do gráfico. Use o mapeamento abaixo ao alterar uma seção; azul e laranja não representam a mesma medida em todos os gráficos.

| Visualização | Mapeamento |
| --- | --- |
| Curva de Desacoplamento | Receita: azul `#326bba`, sólida, círculo, eixo esquerdo. Investimento: laranja `#d97706`, tracejada, losango, eixo direito |
| Performance de Mídia | Meta: azul. Google: verde `#167d57`. ROAS global: laranja tracejada no eixo direito |
| Gráficos compactos dos KPIs | ROAS: azul. Investimento: verde-água. Ticket: violeta |
| Faixas de ticket | Em ordem crescente: `#a6bddb`, `#6493c7`, `#326bba`, `#8b78b8`, `#d97706` |
| Bolhas de ticket | Escala contínua do azul ao laranja conforme o ticket; área proporcional às vendas |
| Clientes | Novos: azul. Recorrentes: laranja, tanto na rosca quanto nas barras |
| Cascata financeira | Aumentos: azul; deduções: vermelho; total de lucro positivo: verde; total negativo: vermelho |

No atingimento da meta, **verde a partir de 100%**, **âmbar de 90% até menos de 100%**, **vermelho abaixo de 90%**. Sem meta ou sem dados, use estado neutro e texto explicativo. Os badges usam os estados Bootstrap `success`, `warning`, `danger` e `secondary`; suas cores vêm do tema Bootstrap, enquanto bordas e figuras usam os valores explícitos acima.

O bullet de atingimento tem fundos `#fbe9ec`, `#fff2d8` e `#e2f3eb` para as faixas, com marco em 100%. Preserve o percentual real quando ele superar 100%.

## 4. Tipografia e números

A interface usa a fonte do sistema **Segoe UI**, com fallback **Arial, sans-serif**. Os gráficos executivos novos seguem essa família. O helper antigo `_figure`, em `charts.py`, ainda usa Arial.

| Elemento | Tamanho / peso implementado |
| --- | --- |
| Nome da marca no cabeçalho | 22 px, 700; 18 px em telas de até 768 px |
| Título de página | 24 px, 700 |
| Título de seção analítica | 21 px, 700; 19 px em telas de até 768 px |
| Título interno de gráfico | 14 px, 600 |
| Descrição de página | 14 px |
| Descrição de seção | 13 px, entrelinha 1,6 |
| Rótulo do KPI executivo | 13 px, 600 |
| Valor do KPI executivo | `clamp(25px, 2vw, 32px)`, 750, números tabulares |
| Valor de card compartilhado | `clamp(19px, 1.5vw, 26px)`, 700 |
| Notas e rótulos de filtros | 12 px |
| Badge executivo | 10 px, 600 |
| Tabela | 13 px |

Títulos de página usam `H2`; seções analíticas, `H3`; títulos internos de pares de gráficos, `H4`. Os rótulos dos KPIs também usam `H3`, com a classe própria que reduz sua escala visual.

Use formatação brasileira e unidades explícitas:

| Tipo | Exemplo |
| --- | --- |
| Moeda | `R$ 130.337,97` |
| Percentual | `57,00%` |
| ROAS | `4,14x` |
| Contagem | `1.142` |
| Data completa | `31/07/2026` |
| Competência da tabela financeira | `07/2026` |
| Mês no eixo temporal | `Jul/2026` |
| Valor ausente | `—` |

Os valores principais atuais são exibidos por extenso, com duas casas para moedas, percentuais e ROAS. Use `format_value` em [charts.py](charts.py) para manter consistência.

## 5. Espaçamento, superfícies e responsividade

O container principal tem largura máxima de **1600 px**, padding **30 px vertical / 32 px horizontal**. Em telas de até **768 px**, passa a **22 px / 14 px**. O cabeçalho acompanha a mesma largura máxima.

Painéis usam borda de **1 px**, raio de **12 px** e fundo branco. Cards executivos têm borda superior de **3 px** na cor do indicador/estado e sombra discreta `0 4px 16px rgba(23, 50, 77, 0.035)`.

| Componente | Distribuição e medidas atuais |
| --- | --- |
| KPIs executivos | 1 coluna abaixo de 768 px; 2 a partir de 768 px; 4 a partir de 1200 px. `xs=12, md=6, xl=3`, gutter `g-3` |
| Card executivo | Altura mínima 300 px; corpo com padding 20 px; gráfico compacto com 58 px |
| Cards compartilhados / financeiros | `xs=12, sm=6, lg=4`; em `xl`, a largura depende da quantidade. Com quatro cards: 1 / 2 / 3 / 4 colunas conforme o breakpoint |
| Filtros | Padding 20 px, flex com quebra de linha, gap 18 px; Ano, Período e Indicador têm larguras flexíveis |
| Seção analítica | Cabeçalho com padding `24px 24px 0`; corpo `8px 12px 18px` |
| Seção analítica até 768 px | Cabeçalho `20px 16px 0`; corpo `8px 0 16px` |
| Curva e mídia | Gráfico em largura total |
| Mix | Abaixo de 992 px: empilhado. A partir de 992 px: barras em 7/12 e bolhas em 5/12 |
| Clientes | Abaixo de 992 px: empilhado. A partir de 992 px: duas colunas de 6/12 |
| Separação das seções | `mb-4`; pares de gráficos usam `g-3` |
| Células de tabela | Padding `12px 18px`, conteúdo sem quebra; container responsivo com rolagem horizontal |

A responsividade deve preservar a leitura dos valores, os rótulos dos eixos e a explicação de cada indicador. Use rolagem dentro das tabelas extensas e permita que filtros, badges e detalhamentos quebrem de linha.

## 6. Componentes e hierarquia

**Cabeçalho:** marca à esquerda, disponibilidade dos indicadores à direita. O monograma CM usa fundo azul e raio de 12 px. A data mostra a disponibilidade dos dados carregados.

**Filtros:** ano e período controlam as seções da Visão Geral Executiva. Os atalhos “Mês atual” e “Ano atual” usam o fuso `America/Sao_Paulo`. O seletor “Indicador do gráfico” permanece sempre visível e controla a série diária.

**Card executivo:** rótulo e badge no topo, valor principal, detalhe da fórmula/meta, visual compacto e rodapé. Faturamento usa um bullet quando há meta; os outros três usam gráficos de evolução diária. A ausência de meta tem um placeholder textual. A implementação está em `executive_kpi_cards`, em [components.py](components.py).

**Seção analítica:** reutilize `.strategy-card`, `.strategy-heading`, `.strategy-body` e `.strategy-note`. O cabeçalho contém título e descrição; o corpo contém o gráfico ou o par de gráficos; a nota explica unidades, abrangência e limites relevantes dos dados. Alguns cabeçalhos usam `.strategy-eyebrow`, como “Cruzamento estratégico” e “Resultado financeiro”.

**Tabela:** use `dbc.Table` responsiva, com hover, classe `.results-table`, cabeçalho claro e rótulos das medidas. A tabela recente tem 12 dias; a financeira tem as competências mensais com receitas observadas e a cobertura de dias.

**Alertas:** `info` para a abrangência mensal da DRE; `warning` para origem CPA, dados financeiros incompletos ou diferenças de conciliação. Exiba o alerta junto da análise afetada, com uma explicação concreta.

**Interação:** carregamentos usam `dcc.Loading(type="circle")`. Gráficos completos oferecem hover e controles Plotly; gráficos compactos dos KPIs ocultam a barra de ferramentas. Preserve os IDs de componentes e filtros usados nos callbacks.

## 7. Padrões de gráficos

Use `plotly_white`, fundo branco, grade discreta e linhas em torno de 2 a 3 px. As séries executivas temporais usam marcadores, legendas horizontais e tooltip que compara a data. Evite suavizar curvas de forma que altere a leitura dos registros.

| Visual | Altura atual | Característica de leitura |
| --- | --- | --- |
| Bullet e gráficos compactos dos KPIs | 58 px | Sem eixos visíveis; bullet com marco em 100% |
| Curva de Desacoplamento | 430 px | Dois eixos Y, cores correspondentes às séries, legenda abaixo e hover unificado |
| Mídia e ROAS | 420 px | Investimento em R$ no eixo esquerdo; ROAS em `x` no direito |
| Faixas, bolhas, rosca e custo de referência | 380 px | Comparação de composição ou distribuição |
| Indicador selecionável | 350 px | Evolução diária, título dentro da figura |
| Cascata financeira | 420 px | Valores positivos/negativos e lucro como total, com valores externos às barras |

As alturas são as configuradas no código, com largura responsiva. Ajustes de margem devem acomodar legendas e títulos nos dois eixos.

### Tempo, composição e resultado

Na curva e na mídia, seleções dentro de um mês usam dias; seleções que cruzam meses usam somas por competência. O ROAS mensal é recalculado pelas somas. Os meses incluem o ano para evitar misturar competências de anos distintos.

Datas ausentes permanecem como lacunas (`connectgaps=False`). Pontos isolados têm marcadores. A nota dos gráficos de dois eixos explica que as escalas são independentes.

As barras de ticket são horizontais, em faixas crescentes. Cada barra soma as vendas dos dias daquela faixa de ticket médio. As bolhas usam data no eixo X, ticket diário no Y e área proporcional às vendas.

A rosca de clientes tem furo de **0,68**, novos em azul e recorrentes em laranja. O centro informa os dias comparáveis. O texto central usa coordenadas `paper`; eixos cartesianos ficam ocultos.

A cascata apresenta **Receita bruta → Impostos sobre vendas → Devoluções → CPV → Lucro bruto**. Preserve a dedução de devoluções e o total calculado pelo Plotly. Margens bruta e líquida aparecem com seus denominadores nos rótulos do resumo.

## 8. Estados de interface e fidelidade dos dados

| Situação | Apresentação |
| --- | --- |
| Período sem dados | Mensagem no gráfico, valores `—` e tabela com texto de ausência |
| Zero registrado | Mostrar zero com a unidade da medida |
| Divisão por zero ou sem denominador | Mostrar `—` e explicar a cobertura quando relevante |
| Meta ausente | “Meta não cadastrada”, badge neutro e placeholder no lugar do bullet |
| CPA na origem de recorrentes | Alerta de origem e exclusão desses valores das novas proporções/custos |
| Um tipo de cliente sem cobertura | Barra ausente e indicação “Sem dados” |
| DRE com filtro de dias parcial | Alerta de que a seção inclui as competências mensais abrangidas |
| DRE com custo ausente | Alerta e cascata sem resultado agregado incompleto |

Preserve estas distinções nas próximas alterações:

- Os números de clientes são somas de registros diários. A rosca usa apenas dias com ambos os tipos informados. A identificação de pessoas únicas exige identificadores.
- A barra de custo usa o título **“Investimento por registro · referência”**. O CAC atribuído por tipo depende de custos separados para aquisição e recorrência. Os tooltips informam investimento, contagem e dias usados.
- As faixas representam o **ticket médio diário**. A separação de máquinas e peças depende de pedidos, SKUs e categorias; os picos visuais indicam dias para investigação.
- Na página executiva, investimento é Meta Ads + Google Ads + Outros. Os gráficos e a tabela acompanham a mesma definição dos cards.
- A meta do card de faturamento vem de [planning.py](planning.py). O previsto da seção financeira vem de PLANO 2026 no BigQuery; essa seção tem sua própria indicação de atingimento e abrangência mensal.
- A DRE mostra margens **bruta** e **líquida** separadamente. A linha “Margem de lucro” da fonte corresponde à margem líquida.

## 9. Acessibilidade e textos

Associe cores a rótulos, percentuais, tracejados ou marcadores. Use títulos semânticos e os atributos `aria-label` / `aria-labelledby` já presentes nas seções. Explique unidades nos eixos e valores nos tooltips. Mantenha os controles operáveis por teclado e o foco visível ao evoluir os componentes.

As notas devem explicar uma decisão que afeta a leitura: fórmula, cobertura, escala, fonte ou limitação observada. Use frases curtas e termos de negócio. SQL, credenciais e detalhes de infraestrutura ficam na documentação técnica.

## 10. Mapa de implementação

| Alteração | Arquivo de referência |
| --- | --- |
| Paleta da interface, tipografia, espaçamentos e ajustes de tela | [assets/dashboard.css](assets/dashboard.css) |
| Cabeçalho, filtros e página executiva | [layout.py](layout.py) |
| Ordem das seções da primeira página | [pages/visao_geral_executiva.py](pages/visao_geral_executiva.py) |
| Cards, tabelas e painéis compartilhados | [components.py](components.py) |
| Curva, gráficos compactos e indicador selecionável | [charts.py](charts.py) |
| Cores dos KPIs e cálculo de atingimento | [executive.py](executive.py) |
| Estrutura das três seções complementares | [insight_sections.py](insight_sections.py) |
| Figuras de mídia, mix e clientes | [insight_charts.py](insight_charts.py) |
| Faixas de ticket e cobertura de clientes | [insights.py](insights.py) |
| Resumo, cascata e tabela financeira | [financial_section.py](financial_section.py) |
| DRE, margens e filtro mensal | [financial.py](financial.py) |
| Conexão do Bootstrap e aplicação Dash | [app.py](app.py) |

O CSS contém quatro variáveis de base; parte das cores e medidas permanece literal nos módulos Python. O gráfico de indicador selecionável usa Arial, enquanto as demais seções executivas usam Segoe UI. Ao fazer uma alteração, confira o componente usado e mantenha este briefing fiel ao resultado implementado.

## 11. Continuidade e conferência visual

Para retomar o trabalho: leia o [README.md](README.md), este briefing, o CSS e o módulo da seção a alterar. Reutilize os componentes existentes e mantenha a identidade e a sequência da primeira página ao implementar o pedido da sessão.

Depois de uma mudança de interface, confira desktop (por exemplo, 1440 e 1280 px), tablet (768 px) e celular (390 px). Observe rótulos, valores, legendas, foco e rolagem das tabelas. Esses tamanhos são referências de conferência, não capturas já homologadas.

Use janeiro de 2025 para clientes com cobertura válida, julho de 2026 para mídia/ticket/DRE, o ano de 2025 para agregação mensal e um período vazio para os estados de ausência. Para verificar o bullet, configure uma meta de teste explicitamente identificada e retire-a após a conferência; o planejamento de produção deve usar os valores aprovados.

Em 15/10/2026, a limpeza para página única foi validada com 56 testes usando dados sintéticos. Uma validação anterior conferiu cálculos e callbacks com dados reais do BigQuery. A inspeção visual automatizada no navegador não foi concluída neste ambiente; este briefing descreve a implementação e as decisões registradas, com base no código.
