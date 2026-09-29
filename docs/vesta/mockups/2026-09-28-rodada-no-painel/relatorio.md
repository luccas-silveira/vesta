# Verificação — rodada no painel

Tela existente mudando (painel da Vesta), tipo Operar, modo direto: uma direção, no estilo atual
do painel. Servida em `http://127.0.0.1:4861/index.html`. Estados pela barra "mockup · estado"
ou por `?estado=<nome>`.

Respostas deduzidas (modo direto): a pergunta pendente fica acima de tudo no centro e, no
celular, sobe acima dos instrumentos; com pergunta pendente o acento da página vira ciano; antes
da execução a palavra grande mostra a fase atual; o bloco Rodada fica acima das Etapas.

## Rodada 1

Achou: microtexto de 9.5 a 10px no bloco novo; texto em cinza `#747474` a 4.2:1 nas fases
pendentes; origem da pergunta em caixa alta longa; fase feita marcada com faixa inferior (lida
como side-tab); entrelinha 1.25 no enunciado; barra de estados do mockup fixa, cobrindo as fases
no print de página inteira.

## Rodada 2

Correções em lote: microtexto do bloco novo a 11px e em `--tinta-2`; fases pendentes em
`--tinta-2`, sem peso; origem em caixa normal; fase feita com ✓ no lugar da faixa; enunciado
a 1.3; barra do mockup no fluxo, no topo. Alarmes do detector de 91 para 53 (1440) e 54 (375).

Restantes, refutados:

- `undersized-ui-text` (22), `low-contrast` 4.2:1 (4), `kicker-above-heading`, `tiny-text` 8.5px,
  `text-overflow` na trilha, `wide-tracking`, `flat-type-hierarchy`, contraste dos gráficos de
  contexto, tokens e ferramentas: todos em elementos do painel atual (`.micro` a 9.5px, rótulos
  "projeto", "plano", "sincronia", eixos dos gráficos, botões da trilha desabilitados), fora do
  escopo da spec. Nenhum está em `#rodada`, `#pergunta` ou `.demo` (conferido no CSS computado).
- `tiny-text` 11px: é o microtexto de hora e meta do bloco novo, no piso de 11px.
- `all-caps-body`: o `#obs` do painel atual ("Fase 5 de 8 · pergunta esperando resposta") e os
  rodapés dos instrumentos, estilo existente.
- `ai-color-palette` "Cyan gradient": a hachura de progresso (`.cheio`) herdando o acento ciano;
  ela fica oculta antes da execução.
- `repeating-stripes-gradient`: hachura da fase pulada; é o sinal de "pulada", com o texto riscado
  junto (COR-16).

## Rodada 3

Pedido do usuário: verde e ciano trocados por `#FF4D00` em todo o painel (tokens `--verde` e
`--ciano`, e as cores fixas do favicon). Texto `#FF4D00` sobre o fundo e texto escuro sobre
`#FF4D00` passam de 4.5:1; o alarme `ai-color-palette` sumiu. Alarmes: 52 (1440) e 53 (375),
os mesmos refutados da rodada 2. O coral de "travada" (`--coral`) ficou próximo do novo acento.

## Piso

| id | resultado |
|---|---|
| SLOP-02 | passou: sem gradiente em texto nem roxo |
| SLOP-37 | passou: sem ícone novo; ✓ e ↳ tipográficos |
| SLOP-10 | passou |
| SLOP-11 | passou: pergunta é um bloco, não card dentro de card |
| SLOP-22 | passou no bloco novo; "projeto" acima do nome é do painel atual |
| SLOP-21 | passou |
| SLOP-46 | passou: dados de exemplo tirados desta rodada real |
| SLOP-44 | passou: sem vidro |
| SLOP-49 | passou |
| TIP-01 | passou: Rajdhani, IBM Plex Sans e Mono do painel |
| TIP-12 | passou: enunciado 22px, opções 16px, histórico 15px |
| TIP-20 | passou: h3 Rodada, h4 Histórico e Atividade |
| TIP-21 | passou: horas com `tabular-nums` |
| TIP-22 | passou: `display=swap` do painel |
| COR-02 | passou: só tokens do `:root` |
| COR-12 | passou no bloco novo após a rodada 2 |
| COR-13 | passou: foco de 2px em opção, campo, botão e barra do mockup |
| COR-15 | passou |
| COR-16 | passou: fase atual com fundo e `aria-current`; pulada com risco e hachura; feita com ✓ |
| COR-18 | passou: o painel é escuro por desenho |
| LAY-03 | passou |
| LAY-22 | passou: `scrollWidth` 375 em 375 |
| LAY-26 | passou: opções ≥ 89px de altura, Responder 44px |
| LAY-31 | passou: z-index do painel |
| MOV-02 | passou: só o favicon pisca, avisando a pergunta |
| MOV-03 | passou |
| MOV-05 | passou |
| MOV-09 | não se aplica |
| MOV-10 | não se aplica |
| MOV-23 | passou: pulso do painel já respeita `reduced-motion`; o piscar do favicon não é animação CSS |
| UX-01 | passou: Responder com padrão, hover, foco, pressionado, desabilitado, enviando, erro e sucesso ("respondida no Knobler") |
| UX-08 | passou: erro de envio diz o que falhou e como sair (tentar de novo ou o terminal) |
| UX-14 | passou: "Outra resposta" acima do campo |
| UX-15 | passou: ajuda e erro embaixo, no mesmo lugar |
| UX-16 | passou: validação só ao enviar |
| UX-26 | passou: uma ação primária, Responder |
| UX-11 | não se aplica |
| UX-12 | não se aplica |
| UX-20 | passou: opções são `input` nativos, envio por Enter |

Console sem erro nas duas larguras.
