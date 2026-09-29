# Relatório — etapa 2, verificação da tela real (rodada 1)

Tela servida pelo `painel.py servir` sobre este repositório, com dados reais: 141 requests,
141 colunas em Tokens e 2705 elementos nos oito gráficos. Chromium, 1440×900.

Prints: `r1-1440.png`, `r1-375.png`. Detector: `r1-detector-375.json`, `r1-detector-1440.json`.

## Medições

- Abertura: do primeiro ao último quadro animado vão 288–1139 ms, ou seja, 851 ms. Houve um
  quadro lento, de 49 ms. O pico foi de 833 animações e interpolações ao mesmo tempo.
- Antes da correção, a mesma medição dava 1158 ms e quadros de 200–300 ms. Tokens animava
  1890 pontos um a um. Agora anima por coluna, 141 grupos (plano, etapa 2).
- Parado: em 3,6 s, com uma leitura no meio, os 2705 elementos continuaram sendo os mesmos
  objetos. Nenhum mudou, e nenhuma amostra teve animação ou interpolação ativa.
- Movimento reduzido: `anima()` é falso, 0 animações e 0 interpolações.
- Largura: `scrollWidth` 375 em 375.
- Console: 0 erros.

## Piso e movimento

MOV-02, MOV-03, MOV-08, MOV-09, MOV-10, MOV-23, MOV-24 e LAY-22 passaram, com as medições
acima. Os demais itens do piso não mudam nesta etapa: ela não mexe em layout, cor, texto nem
controle.

## Alarmes do detector

- `layout-transition` (2×): é a hachura de progresso. Refutado como no relatório do mockup:
  ela é absoluta, não reflui vizinhos e muda uma vez por etapa.
- `tiny-text` (10), `tight-leading` (2), `line-length` (1), `undersized-ui-text` (28): são da
  tipografia que já existia, em 11 px nas listas e 1.2 no título das etapas. Aparecem mais
  vezes porque os dados reais têm mais itens de lista e documento no leitor. Esta etapa não
  mudou CSS de texto.
- Demais: iguais aos do mockup e dos mockups anteriores.
