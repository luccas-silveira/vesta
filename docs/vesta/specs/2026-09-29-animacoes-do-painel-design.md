# Animações do painel

## Resultado

O painel parece responder aos próprios dados. Ao abrir, cada gráfico se monta uma vez. Depois
disso, só se move o que mudou, do valor antigo ao novo, e parado nada se mexe além do pulso.
Hoje o `render()` apaga e recria todo SVG e lista a cada leitura de 3 s, então não há como
distinguir o que mudou do que foi só redesenhado.

## O que o usuário disse

- Animações clean na abertura e nas mudanças de estado de todos os gráficos e pontos.
- Nada forçado: o sistema deve parecer responder diretamente às alterações nas informações.
- Biblioteca nova só se for vantajosa. Abordagem escolhida: nativa, sem dependência.

## O que foi suposto (confirmado)

- Abertura curta: montagem total abaixo de 1 s.
- Parado não se move nada além do pulso, que segue piscando a cada leitura.
- Mudança: 150–400 ms, curva que desacelera no fim, sem quique.
- `prefers-reduced-motion: reduce` torna tudo instantâneo.
- Os testes atuais de `test_painel.py` seguem passando.

## Critério de sucesso

- Painel aberto e parado por 1 min: nenhum movimento fora o pulso.
- Um dado muda (request nova, etapa verde, feature nova): só os elementos daquele dado
  animam, e o olho vai direto a eles.
- Abrir a página: cada gráfico se monta uma vez, em sequência de cima para baixo, em menos
  de 1 s.

## Mecanismo

Um único ponto de reconciliação para todos os SVGs: `pintar(g, itens)`, que hoje já serve
`dias`, `radar`, `onda` e `relogio`. `arco`, `pontos`, `colunas` e `ferr` passam a usá-lo
também.

- Cada item carrega uma chave estável (`data-k`), por exemplo `etapa-3`, `dia-14`, `hora-09`.
  Item sem chave usa a posição na lista.
- Elemento com a mesma chave é reaproveitado. Cada atributo que mudou interpola do valor
  atual ao novo em ~300 ms. A interpolação é genérica: se o valor antigo e o novo têm o mesmo
  esqueleto e diferem só nos números, cada número interpola; senão, troca direto. Isso cobre
  `x`, `y`, `height`, `r`, `opacity` e o `d` do arco sem código próprio.
- Elemento novo entra com fade de opacidade. O item pode declarar de onde nasce (`de`):
  barra da base, ponto do próprio centro, feature do centro do radar.
- Elemento que sumiu esmaece e só então é removido.
- Textos numéricos marcados contam do valor antigo ao novo pelo mesmo interpolador.
- O motor é um laço de `requestAnimationFrame` com tempo absoluto. Sem
  `requestAnimationFrame` ou com movimento reduzido, o valor final vai direto.
- Leitura nova no meio de uma animação: parte do valor atual interpolado, sem salto.
- Aba em segundo plano: ao voltar, animações atrasadas vão direto ao final.

Listas HTML (etapas, fases, histórico, atividade) seguem a mesma regra por chave: `id` da
etapa, `id` da fase, índice do histórico, e na atividade (que vem da mais nova para a mais
antiga) `n_atividade - i`, para que a mesma chamada guarde a mesma chave quando outra entra
no topo.

Abertura: a primeira leitura trata todo elemento como novo. Dentro de cada gráfico, os itens
entram escalonados, e os gráficos entram defasados por posição na tela, somando menos de 1 s.
Linhas se desenham do começo ao fim (`stroke-dashoffset` com `pathLength`). Gráfico que sai
do vazio e volta a ter dados remonta pela mesma regra, só ele.

Estado: `--acento` registrado com `@property` como cor, com transição no `body`. A palavra
grande (`#palavra`) faz troca cruzada quando o texto muda.

## Por gráfico

- Contexto (`arco`): traço e ponteiro deslizam até o novo percentual; o número central conta.
- Tokens (`pontos`): request nova faz as colunas deslizarem para a esquerda; a nova nasce na
  borda direita com os pontos subindo da base.
- Dias, Sequência, Provas: célula ou quadrado que mudou de nível acende até a intensidade nova;
  o recorde conta.
- Radar: feature nova cresce do centro até a posição; as outras escorregam quando a idade muda
  de faixa.
- Tempo (`colunas`), Ferramentas (`ferr`): barra cresce ou encolhe da base, números contam;
  ferramenta que troca de posição no ranking desliza até a linha nova.
- Onda, Relógio: cada traço estica até o novo tamanho; a cor de destaque passa ao trecho que
  virou pico.
- Odômetro: sem mudança, já rola os dígitos.
- Sessão (`dur`): sem animação.
- Barra de progresso (`#cheio`, `#pct`): hachura cresce até o novo percentual, número conta.
- Etapas: etapa que ficou verde troca o selo com fade curto e acende a linha uma vez.
- Rodada: fase que virou atual acende; item novo no histórico e na atividade entra deslizando
  curto de cima, os de baixo descem.
- Pulso: sem mudança.
- Fora do escopo: o formulário de pergunta pendente e o leitor de documento.

## Erros

- Dado ausente ou gráfico vazio: segue o `vz()` atual, sem animação de saída.
- Chave duplicada num gráfico: o segundo item recebe sufixo de posição, sem quebrar o desenho.
- Qualquer exceção no motor de animação cai no valor final, nunca num gráfico pela metade.

## Testes

Na simulação de página que `test_painel.py` já roda em Node:

- Duas leituras com os mesmos dados reaproveitam os mesmos objetos de elemento, sem recriar
  nenhum.
- Um dado que muda termina com o atributo no valor novo (sem `requestAnimationFrame`, direto).
- Um item que some é removido do SVG.

No navegador real, antes de entregar: gravação de quadros da abertura e de uma mudança de
dado, conferindo duração, sequência e ausência de movimento com o painel parado.
