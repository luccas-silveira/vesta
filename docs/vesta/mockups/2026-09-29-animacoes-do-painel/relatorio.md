# Relatório — animações do painel (rodada 1)

A tela já existe e está mudando, então há uma direção só, no estilo atual do painel. Tipo de
tela Operar, com MOVIMENTO 5 decidido no questionário.

O mockup é o próprio `painel.html` com o motor de movimento. A barra "mockup · simular" altera
os dados, e o painel lê esses dados pelo mesmo `/estado` a cada 3 s.

Prints: `r1-375.png`, `r1-1440.png`, `quadro-abertura-1.png` (120 ms), `quadro-abertura-2.png`
(320 ms), `quadro-etapa-verde.png` (90 ms depois do clique) e
`estado-pausada-reduced-motion-1440.png`.

Detector: `r1-detector-375.json`, `r1-detector-1440.json`.

## Medições (Chromium, 1440×900)

- Parado: em 3,6 s, com uma leitura no meio, 1218 elementos continuaram sendo os mesmos
  objetos. Nenhum mudou, e nenhuma animação nem interpolação ficou ativa.
- Abertura: do primeiro ao último quadro animado vão 38–949 ms. O pico foi de 1076 animações de
  opacidade e 682 elementos interpolando juntos.
- Nova request: 60 ms depois do clique, 613 elementos interpolando e 32 animações, todos nos
  gráficos e rótulos que mudaram (Tokens, Contexto, Ferramentas, Atividade, contadores). Aos
  760 ms não havia nenhum. Entraram exatamente 15 pontos e 1 item de atividade.
- Troca de estado: 90 ms depois de pausar, `--acento` estava no meio do caminho entre âmbar e
  laranja (`oklab(0.787 0.048 0.138)`), e aos 490 ms estava no valor final.
- Movimento reduzido: `anima()` é falso, 0 animações e 0 interpolações, mesmo depois de uma
  request e de uma troca de estado.
- Largura: `scrollWidth` 375 em 375.
- Console: 0 erros.

## O que a rodada tocou

- MOV-02 passou: só anima o que mudou; o painel parado não se move.
- MOV-03 passou: o momento autoral é a abertura. São três primitivas: fade, interpolação de
  geometria e traço que se desenha. Troca e lampejo são variações de fade e cor.
- MOV-05: refutado com prova (ver alarmes). A animação de geometria foi aceita no grill (A10).
  Fade, troca e lampejo usam só `opacity` e cor.
- MOV-08, MOV-09, MOV-10 passaram: 220/420/280 ms, com saída a 67% da entrada, e curvas nos
  valores do guia.
- MOV-23 passou: com movimento reduzido tudo vai direto ao final, e as transições de CSS do
  acento e da hachura ficam desligadas.
- MOV-24 passou: uma leitura no meio de uma animação parte do valor atual; os cliques não
  esperam animação.
- LAY-22 passou: sem rolagem lateral em 375 e 1440.

## Piso

SLOP-02, SLOP-10, SLOP-11, SLOP-21, SLOP-37, SLOP-44, SLOP-46, SLOP-49, TIP-01, TIP-20,
COR-02, COR-15, COR-16, COR-18, LAY-03, LAY-26, LAY-31, UX-08, UX-11, UX-12, UX-14, UX-15,
UX-16, UX-20, UX-26 passaram ou não se aplicam. A mudança não mexe em layout, cor, texto nem
controle.

TIP-21 passou: os rótulos que contam estão em IBM Plex Mono, que tem algarismos de largura
fixa. Os números em Rajdhani trocam com fade, sem contar (A11).

SLOP-22, TIP-12, TIP-22, COR-12 e COR-13: os alarmes do detector sobre isso já existiam no
painel, em áreas que esta mudança não toca, e ficam fora do escopo.

## Alarmes do detector

- `layout-transition` (`transition: width`, 2×): é a hachura de progresso das etapas
  (`.hachura .cheio`). Refutado. O elemento tem `position:absolute`, então mudar a largura não
  reflui nenhum vizinho, e isso acontece uma vez por etapa concluída. Trocar por
  `transform: scaleX` achataria a hachura e o marcador da ponta.
- `undersized-ui-text` (25, eram 19 no mockup anterior): a diferença vem dos rótulos `.micro`
  das etapas e da barra do mockup, visíveis neste estado e não no outro. A tipografia não
  mudou.
- Demais alarmes: iguais aos do mockup anterior, em elementos que esta mudança não toca.
