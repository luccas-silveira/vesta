# Relatório — faixa única (rodada 1)

Tela existente mudando: uma direção, estilo atual do painel. Tipo Operar (sem Lighthouse nem rotação).

Prints: `r1-375.png`, `r1-1440.png`, `estado-grill-aberto-1440.png`, `estado-feature-antiga-1440.png`.
Detector: `r1-detector-375.json`, `r1-detector-1440.json`.

## O que a rodada tocou

- LAY-22 passou: largura da página 375 em 375 e 1440 em 1440, sem rolagem lateral.
- LAY-26 passou: fases clicáveis medem 77×46 a 77×58 px em 375.
- UX-20 passou: as fases com documento são `<button>`, alcançadas por Tab, com `aria-pressed` no documento aberto.
- COR-13 passou: foco com contorno de 1px em `--tinta` sobre o chão escuro.
- COR-16 passou: a fase aberta tem barra de 3px embaixo, além do contorno; a atual segue com fundo de acento e `aria-current`.
- UX-01: padrão, hover (fundo `--placa`), foco, pressionado (barra). Desabilitado = fase sem documento, que vira célula comum sem botão. Carregando/erro: o leitor mostra "Documento não encontrado." como antes.
- Console: 0 erros.

## Piso

SLOP-02, SLOP-10, SLOP-11, SLOP-21, SLOP-37, SLOP-44, SLOP-46, SLOP-49, TIP-01, TIP-20, TIP-21, COR-02, COR-15, COR-18, LAY-03, LAY-31, MOV-02, MOV-05, MOV-23, UX-08, UX-11, UX-12, UX-14, UX-15, UX-16, UX-26: passaram ou não se aplicam; a mudança só remove a faixa de botões e reaproveita a faixa de fases com os tokens existentes.

SLOP-22, TIP-12, COR-12, TIP-22: os alarmes do detector sobre isso são de áreas que esta mudança não toca (topo, widgets laterais, gauge de contexto) e já existiam no painel; ficam fora do escopo.

## Alarmes do detector

- `span.micro overflows its box by 32px` (375): é o "agora · 23:40" da fase atual, cortado com reticências de propósito (`text-overflow: ellipsis` já existia em `.fases .micro`). Refutado.
- Demais alarmes: todos em elementos fora da faixa de fases e do leitor; nenhum aponta para `#fases` ou `#leitor`.
