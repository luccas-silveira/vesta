# Verificação — gráficos laterais do painel

Tela existente mudando (painel da Vesta), tipo Operar, modo direto: uma direção, no estilo atual.
Servida em `http://127.0.0.1:4871/index.html` (servidor parado ao fim). Estados pela barra
"mockup · estado" ou `?estado=<nome>`; a página abre em `execução`. Sem Lighthouse nem trace (Operar).

Oito widgets novos, cinco na coluna direita e três na esquerda: Dias, Sequência, Radar (abaixo de
Tokens); Onda, Odômetro, Provas, Relógio, Pulso (abaixo de Ferramentas). Dados de exemplo em
`BASE.hist`, `BASE.sessao.ritmo` e `BASE.features`; o resto vem do estado que o painel já lê.

## Rodada 1

Achou: rótulos do radar (nome da feature ao lado do ponto) se sobrepunham e estouravam a largura;
`.num small` ("DIAS") em `--tinta-3` a 4.2:1; SVGs de widget vazio não sumiam (`hidden` não age em
SVG), deixando caixa pontilhada alta com o aviso embaixo.
Detector: 61 (375) e 60 (1440), todos em elementos do painel atual, exceto o radar e "DIAS".

## Rodada 2

Correções em lote: radar com pontos numerados e legenda em lista abaixo (nome e idade em dias);
"DIAS" em `--tinta-2` a 11px; `vz()` passou a usar `toggleAttribute('hidden')`.
Detector: 60 e 59; sem alarme novo fora do radar.

## Rodada 3

Rótulos dos anéis do radar (1 d, 7 d, 30 d) saíram do eixo horizontal, onde se atropelavam, para o
vertical, um abaixo do outro. Detector: 60 (375) e 59 (1440). Console sem erro. Sem rolagem
horizontal em 375 (scrollWidth 375). Prints: `r3-375.png`, `r3-1440.png`; estados
`estado-primeiro-dia-1440.png` (vazio de todos os widgets) e
`estado-travada-reduced-motion-1440.png` (acento branco da etapa travada, movimento reduzido).

## Piso conferido

COR-02 passou (tokens do `:root`, nenhum valor cru novo além de `#ff4d00` já existente);
COR-12 passou, com a refutação abaixo; COR-16 passou (cada gráfico tem número no rodapé e
`aria-label`, e a cor só reforça); COR-18 n/a (painel só escuro, decisão existente);
SLOP-46 passou (dados de exemplo rotulados como mockup, vazio mostra marcador, não número);
SLOP-10 e SLOP-11 passaram (nenhum card); TIP-21 passou (tabulares no odômetro e na legenda);
LAY-22 passou (375 a 1440); MOV-02, MOV-05, MOV-23 passaram (odômetro rola por `transform`,
pulso por `opacity`, ambos desligados em `prefers-reduced-motion`; print no estado travada);
UX-01 n/a nos widgets, que não têm interação; vazio coberto (estado `primeiro dia`);
UX-20 n/a, sem controle novo; LAY-26 n/a, sem alvo novo.

## Alarmes do detector

Todos os restantes estão em elementos que já existiam ou são falso positivo:

- `undersized-ui-text` (31), `kicker-above-heading`, `flat-type-hierarchy`, `low-contrast` 4.2:1
  (5), `repeating-stripes-gradient`, `text-overflow` e `all-caps-body` (6): microtexto de 9.5px,
  rótulos "projeto/plano/sincronia", eixos dos gráficos antigos, botões da trilha e a hachura de
  progresso. Conferido no DOM: os cinco `#747474` e os seis `all-caps-body` não estão em `.novo`
  (nenhum elemento de `.novo` tem cor `#747474`; os `all-caps-body` de 35 e 39 caracteres são
  `.micro` de Rodada, Etapas e Trilha). O microtexto dos widgets novos é 11px em `--tinta-2`.
- `low-contrast` 1.2:1 em "1 d", "7 d", "30 d", "1" e "2" (radar): o detector mede o texto do SVG
  contra o fundo pontilhado como se fosse gradiente, o mesmo falso positivo que já marca "171k" e
  "204k" nos gráficos antigos (2.2:1). Cores efetivas lidas no navegador: rótulos dos anéis
  `oklch(0.76 0 0)` sobre `#0d0d0d`, razão 9.1:1; número no ponto `oklch(0.135 0 0)` sobre
  `#ff4d00`, razão 6.0:1. Ambas passam 4.5:1.
