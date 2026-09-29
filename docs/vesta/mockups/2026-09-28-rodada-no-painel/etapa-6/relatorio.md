# Verificação — etapa 6, tela da rodada

Página real servida por `painel.py servir` em `http://127.0.0.1:4871/`, sobre este repositório:
execução em andamento (Rodada abaixo das Etapas), rodada costurada de 2 sessões com 42 itens de
histórico e 165+ de atividade, e uma pergunta pendente postada em `/pergunta`.

## Rodada 1

Achou: na atividade, nomes longos de ferramenta (`browser_navigate`, `ToolSearch`) passavam da
coluna de 64px e cobriam o alvo (medido: `scrollWidth` 162 contra 64). O mockup não pegava porque
os dados de exemplo só tinham nomes curtos.

Conferido: envio pela página grava `respondida` com o rótulo marcado (`GET /pergunta/menu-demo`);
sem nada marcado e sem texto aparece "Marque uma opção ou escreva uma resposta." e nada é
enviado; texto e marcação sobrevivem à atualização de 3 s; título `● pergunta · vesta · Vesta`.

## Rodada 2

Correção: coluna da ferramenta a 104px, com reticências e o nome inteiro no `title`.

Achou: a 1280px, "Concluída" na faixa de fases passava 5px da célula.

## Rodada 3

Correção: fases com `letter-spacing` .08em, padding lateral 6px e reticências de segurança;
nenhum nome de fase cortado a 1280 e 1440.

Prints `r3-375.png` e `r3-1440.png`; detector em `r3-detector-375.json` (97) e
`r3-detector-1440.json` (96). Console sem erro nem aviso nas duas larguras. Sem rolagem lateral
(`scrollWidth` 375 e 1440).

Alarmes, todos refutados: as mesmas categorias refutadas no `relatorio.md` do mockup, em
elementos do painel atual (`.micro` a 9.5px, `#747474` nos rótulos, `span.micro` da trilha,
gráficos com gradiente, `#obs` em caixa alta, hachura da fase pulada). Os contadores de
`tiny-text` e `low-contrast` sobem com o volume de dados reais (mais linhas de etapa e gráfico).
Prova de que nenhum é do bloco novo, lida no CSS computado da página: dentro de `#rodada` e
`#pergunta` nenhum texto abaixo de 11px, nenhum na cor `rgb(116,116,116)`, nenhuma entrelinha
abaixo de 1.3 em texto de mais de uma linha, e nenhum elemento com texto transbordando sem
reticências.

Fica: nomes de ferramenta com mais de ~13 caracteres aparecem cortados na atividade (nome inteiro
ao passar o mouse). O formulário responde só a primeira questão de um menu com várias, como no
mockup.
