# Relatório — etapa 1, rodada 1 (painel real em http://127.0.0.1:4749/)

Prints: `r1-375.png`, `r1-1440.png`. Detector: `r1-detector-375.json`, `r1-detector-1440.json` (51 achados cada).

- Igual ao mockup aprovado: faixa da Trilha fora, bloco "Documento" com o leitor, fase Mockup como botão (abre a página do mockup em aba nova, como antes).
- LAY-22 passou: largura 375 em 375 e 1440 em 1440.
- UX-20 passou: fases com documento são botões com `aria-pressed`.
- Console: sem erros.
- Testes da etapa: 13 de 13 (PaginaFaixaUnica, FaixaUnicaNoNavegador).

## Alarmes do detector

- `span.micro overflows its box by 32px` (375): "agora · 13:38" da fase atual, cortado com reticências de propósito, já existia. Refutado.
- `div.cols ... fold falls deep inside the section` (1440): colunas de histórico e atividade, que esta etapa não mudou. Fora do escopo.
- Demais: topo, widgets laterais e gauge, iguais ao mockup e anteriores a esta mudança.
