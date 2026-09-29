# Relatório — etapa 3, verificação da tela real (rodada 1)

Tela servida pelo `painel.py servir` sobre este repositório, com dados reais (152 itens na
atividade). Chromium, 1440×900.

Prints: `r1-1440.png`, `r1-375.png`. Detector: `r1-detector-375.json`, `r1-detector-1440.json`.

## Medições

- Parado: em 3,6 s, com uma leitura no meio, 3847 elementos continuaram sendo os mesmos
  objetos. São os gráficos mais `#etapas`, `#fases`, `#hist`, `#ativ`, `#features`,
  `#radar-leg`, `#seq-bar` e `#prov`. Nenhum mudou, e nenhuma amostra teve animação ativa fora
  o pulso.
- Clique depois da reconciliação: o botão Pesquisa, que já era um objeto reaproveitado, abriu o
  documento. O cabeçalho ficou `Pesquisa // animacoes do painel` e o botão ficou com
  `aria-pressed="true"`.
- Abertura: 241–1113 ms, ou seja, 872 ms, com três quadros de 36 a 44 ms.
- Largura: `scrollWidth` 375 em 375.
- Console: 0 erros.

## Piso e movimento

MOV-02, MOV-08, MOV-09, MOV-10, MOV-23 (caminho de `anima()` já medido na etapa 2), MOV-24,
UX-20 (a fase continua sendo `<button>`, e o clique funciona depois da reconciliação) e
LAY-22 passaram. As listas não mudaram de CSS nem de estrutura visível.

## Alarmes do detector

Os mesmos da etapa 2, com um `tiny-text` e um `undersized-ui-text` a mais. Vêm da atividade,
que ganhou itens entre as duas medições, em 11 px como antes. A tipografia não mudou.
`layout-transition` segue refutado: é a hachura de progresso.
