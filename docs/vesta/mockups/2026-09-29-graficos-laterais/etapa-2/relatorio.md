# Verificação — gráficos laterais, etapa 2 (tela real)

Tela existente mudando (painel da Vesta), tipo Operar, modo direto. Servida por
`vesta.py painel` em `http://localhost:4749`, com o `painel.py` da etapa 1 (o processo antigo foi
reiniciado: o `/estado` agora traz `hist` com 140 dias e 24 horas, e `sessao.ritmo` com 48 trechos).

## Rodada 1

Prints: `r1-375.png`, `r1-1440.png`. Detector: `r1-detector-375.json`, `r1-detector-1440.json`
(reserva não usada; binário `detectar` rodou).

Conferido nos prints e no DOM, dados reais deste projeto:

- Dias: 140 células, 322 requisições no total, hoje 151 (passou: 20 semanas, hoje destacado).
- Sequência: 2 dias, recorde 2, últimos 14 dias marcados.
- Radar: 4 features com legenda numerada (`0 d`, `1 d`, `4 d`, `4 d`).
- Onda: 48 trechos, pico de 6 requisições, último trecho em acento.
- Odômetro: 7 dígitos, entrada 5632K e saída 28.3K.
- Provas: etapa 1 verde, etapa 2 em prova (barra segmentada).
- Relógio: 24 marcas, pico às 00h.
- Pulso: linha de batimento.
- Nenhum estado vazio visível; nenhum widget sem dado.
- Console: 0 erros, 0 avisos da página. Sem rolagem lateral em 375 (`scrollWidth` 375 = `clientWidth` 375).
- Bate com o mockup aprovado: mesma ordem nas duas laterais, mesmos rótulos, mesmo acento.

Nenhuma correção de código foi necessária.

## Alarmes do detector (60 em 375, 60 em 1440), refutados

- `undersized-ui-text` (29), `low-contrast` 4.2:1 (17 no total), `kicker-above-heading`,
  `all-caps-body`, `tight-leading`, `wide-tracking`, `flat-type-hierarchy`, `text-overflow`,
  `repeating-stripes-gradient` e `first-viewport-column-overflow`: todos em elementos do painel
  anterior a esta feature (rótulos de 9.5px, cabeçalhos, Contexto, Tokens, Etapas, Rodada,
  Trilha, Sessão, Tempo, Ferramentas), fora do escopo. Nenhum snippet cita um widget novo; os
  widgets novos usam 11px em `--tinta-2`.
- `low-contrast` 1.2:1 em "1 d", "7 d", "30 d" e nos números 1 e 2 do Radar (o detector lê o
  gradiente do pontilhado como fundo). Cores efetivas lidas no navegador: os rótulos de anel têm
  `fill` `oklch(0.76 0 0)` sobre `#0d0d0d`, 9.1:1; os números dentro dos pontos têm
  `oklch(0.135 0 0)` sobre pontos claros ou laranja. É o mesmo falso positivo refutado no mockup.
- `low-contrast` 2.2:1 em "144k", "72.1", "% USADO", "0", "52.9k", "106k", "159k": gráficos de
  Contexto e Tokens, elementos antigos.

Não rodaram Lighthouse nem trace (tipo Operar).
