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

- Painel aberto e parado por 1 min: nenhum movimento na página fora o pulso. O favicon
  segue piscando quando há pergunta pendente, porque é um chamado de propósito.
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
  `x`, `y`, `height`, `r`, `opacity` e as linhas retas sem código próprio. O arco de contexto
  é a exceção (ver Por gráfico).
- Elemento novo entra com fade de opacidade. O item pode declarar de onde nasce (`de`):
  barra da base, ponto do próprio centro, feature do centro do radar.
- Elemento que sumiu esmaece e só então é removido.
- Textos numéricos em fonte mono (IBM Plex Mono) contam do valor antigo ao novo pelo mesmo
  interpolador. Os números grandes em Rajdhani (centro do arco, `#pct`, `#seq-n`, centro do
  relógio) não contam: trocam com transição cruzada curta, porque a Rajdhani não tem
  algarismos de largura fixa (o "1" tem 60% da largura do "4") e o número tremeria.
- O motor é um laço de `requestAnimationFrame` com tempo absoluto. Sem
  `requestAnimationFrame` ou com movimento reduzido, o valor final vai direto.
- Leitura nova no meio de uma animação: parte do valor atual interpolado, sem salto.
- Aba em segundo plano: ao voltar, animações atrasadas vão direto ao final, o painel lê
  `/estado` de imediato e desenha essa leitura sem animação.

O mesmo ponto de reconciliação serve SVG e HTML, atributo por atributo e em árvore: um item
pode ter filhos com chave, reconciliados da mesma forma. Isso vale para as células de
Sequência (`seq-bar`) e Provas (`prov`), a legenda do radar (`radar-leg`), a lista de
features e as listas abaixo. Por isso as listas deixam de montar cada item com `innerHTML` e
passam a descrever os filhos como itens: o botão da fase continua sendo `li.children[0]`, com
o clique religado a cada leitura e `aria-current`/`aria-pressed` escritos ou removidos
explicitamente. Classe trocada num elemento reaproveitado anima por transição CSS de cor e
opacidade. Número dentro de `style` (por exemplo, a largura) interpola como atributo. O item
que sai esmaece também no HTML. As regras que dependem de ordem (`.ativ li:first-child`,
`.leg li:first-child`) não são afetadas, porque na atividade o item novo entra no topo e o
antigo sai do fim.

Listas HTML (etapas, fases, histórico, atividade) seguem a mesma regra por chave: `id` da
etapa, `id` da fase, índice do histórico, e na atividade (que vem da mais nova para a mais
antiga) `n_atividade - i`, para que a mesma chamada guarde a mesma chave quando outra entra
no topo.

Abertura: a primeira leitura trata todo elemento como novo. Dentro de cada gráfico, os itens
entram escalonados, e os gráficos entram defasados por posição na tela, somando menos de 1 s.
Linhas se desenham do começo ao fim (`stroke-dashoffset` com `pathLength`). As que já são
tracejadas (grades, anéis do radar, base da onda) também se desenham: recebem uma máscara com
uma cópia contínua da mesma geometria, e essa cópia se desenha, revelando o tracejado por
baixo. A máscara sai ao fim da abertura. Gráfico que sai
do vazio e volta a ter dados remonta pela mesma regra, só ele.

Estado: `--acento` registrado com `@property` como cor, com transição no `body`. A palavra
grande (`#palavra`) faz troca cruzada quando o texto muda.

## Ritmo e realce (questionário do mockup)

- Intensidade de movimento 5 de 10: uma entrada orquestrada na abertura mais transições de
  estado, sem movimento decorativo contínuo. O padrão de tela de operação é 3, que proíbe a
  abertura pedida.
- Mudança de dado em 220 ms. Elemento novo entra em 420 ms e sai em 280 ms. A abertura inteira
  leva até cerca de 900 ms: os gráficos entram defasados por até 250 ms e os itens se escalonam
  por até 200 ms. Curva de entrada `cubic-bezier(0.16,1,0.3,1)`, de saída
  `cubic-bezier(0.7,0,0.84,0)`, e de troca de estado `cubic-bezier(0.65,0,0.35,1)`.
- Lampejo: o rótulo cujo valor mudou acende na cor de destaque e volta em 500 ms. A linha da
  etapa ou da fase que mudou de estado acende o fundo pelo mesmo tempo.
- Entrada, saída, troca e lampejo usam a Web Animations API e não tocam atributo nenhum. Só a
  geometria passa pelo laço de quadros.

## Por gráfico

- Contexto (`arco`): anima o percentual, não o texto do caminho. A cada quadro o arco,
  o ponteiro e a etiqueta são recalculados a partir do percentual interpolado, e a ponta corre
  pela curva. O número central troca com transição cruzada. A interpolação genérica faria a ponta cortar a corda.
- Tokens (`pontos`): request nova faz as colunas deslizarem para a esquerda; a nova nasce na
  borda direita com os pontos subindo da base. Sem teto: todas as colunas animam sempre,
  mesmo em sessão longa (15 pontos por request; o custo medido é de 1 a 3 ms por quadro).
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
- Barra de progresso (`#cheio`, `#pct`): hachura cresce até o novo percentual, número troca com transição cruzada.
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

Na simulação de página que `test_painel.py` já roda em Node (`HARNESS`, `:1733`), ampliada
para rodar o `render()` inteiro: ganha `remove`, `insertBefore`, `toggleAttribute` e o que mais
os gráficos usarem, e passa a não definir `requestAnimationFrame`, para o motor ir direto ao
valor final. Hoje a simulação define o `requestAnimationFrame`, mas ele nunca chama de volta.

- Duas leituras com os mesmos dados reaproveitam os mesmos objetos de elemento, em todos os
  gráficos e listas, sem recriar nenhum.
- Um dado que muda termina com o atributo no valor novo.
- Um item que some é removido.
- Os testes atuais de `FaixaUnicaNoNavegador` seguem passando sem mudança nas asserções.

No navegador real, antes de entregar: gravação de quadros da abertura e de uma mudança de
dado, conferindo duração, sequência e ausência de movimento com o painel parado.

## Decisões do grill

- **A2** — a simulação de página dos testes é ampliada para rodar o `render()` inteiro, sem
  `requestAnimationFrame`. Motivo: hoje ela só roda `rodada()` e nunca dispara quadros, e o
  teste isolado do núcleo não pegaria um gráfico sem chave.
- **A6** — HTML reconciliado atributo por atributo, em árvore, como o SVG. Escolha do usuário
  no lugar da recomendação de reescrever só o item cujo texto mudou.
- **A7** — coberto por A6: as listas deixam de montar os itens com `innerHTML`, e os cliques e
  `aria-*` são reescritos a cada leitura. A chave nunca carrega hora, por causa de
  `test_painel.py:1869`.
- **A8** — mantido sem mudança: na atividade o item novo entra no topo e o antigo sai do fim,
  então `:first-child` não muda de alvo durante o esmaecimento.
- **A1** — o arco de contexto anima o percentual e se redesenha por quadro. Motivo: o texto do
  caminho interpolado faz a ponta cortar a corda.
- **A5** — Tokens anima todas as colunas sempre, sem teto. Escolha do usuário. O custo medido é
  de 1 a 3 ms por quadro.
- **A9** — linhas tracejadas também se desenham, com máscara. Escolha do usuário no lugar do
  fade.
- **A10** — aceita a animação de geometria. O alarme do verificador é refutado no relatório com
  a medição de A4.
- **A11** — números em Rajdhani trocam com transição cruzada, e os mono contam. Motivo: a
  Rajdhani não tem algarismos de largura fixa (medido nos glifos: de 312 a 515 unidades).
- **A12** — o critério "nada se move" vale para a página. O favicon segue piscando.
- **A3, A4, A13, A14, A15, A16** — confirmam a spec. Registro: laço de quadros único em JS
  (o Safari não anima `d` por CSS); `@property` com `initial-value` literal e o primeiro
  `:root` intacto; na volta da aba, ler de imediato e desenhar sem animação; curva do
  odômetro `cubic-bezier(0.16,1,0.3,1)` reaproveitada; o `<defs>` da hachura entra como item
  com chave.
