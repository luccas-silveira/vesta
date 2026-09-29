# Pesquisa — animações do painel

Spec: `docs/vesta/specs/2026-09-29-animacoes-do-painel-design.md`

Referências visuais (inspo): puladas. O visual não muda, e o inspo guarda capturas estáticas,
sem movimento. O painel já tem sistema visual próprio.

## Achados

### A1 — Interpolar o `d` do arco como texto move a ponta em linha reta, não pela circunferência
- Fonte: https://github.com/w3c/csswg-drafts/issues/10195, https://cagrimmett.com/2016/08/27/d3-transitions/, `skill/scripts/painel.html:397-409`
- Contradiz a spec: parcial. As flags do arco do contexto são sempre `0 1`, então não quebram.
  Mas a ponta, o ponteiro e a etiqueta cortariam a corda do círculo no meio da animação. O
  padrão consagrado interpola o dado (o percentual) e redesenha o arco a cada quadro.
- Pergunta que levanta: o arco ganha um desenho próprio por quadro, para que a ponta corra
  pela curva?

### A2 — A simulação de página dos testes nunca dispara os quadros de animação e não sabe remover elementos
- Fonte: `skill/scripts/test_painel.py:1733-1782`, principalmente `:1760-1766` e `:1737-1758`
- Contradiz a spec: sim. O `requestAnimationFrame` existe na simulação, mas nunca chama de
  volta. Um motor que confiasse nele ficaria parado no valor inicial. A simulação também não
  tem `remove`, `insertBefore` nem `toggleAttribute`, e hoje só roda `rodada()`: nenhum
  gráfico nem o `render()` passam por ela.
- Pergunta que levanta: como provar que o painel reaproveita elementos e termina no valor
  certo? Ampliando a simulação para rodar os gráficos, ou testando só o núcleo de
  reconciliação isolado?

### A3 — No Safari, só um laço de quadros em JS anima o traço de um caminho
- Fonte: BCD `css/properties/d.json`; teste em WebKit 26.6 e Chromium 153 feito na pesquisa
- Contradiz a spec: não. O CSS anima `x`, `r` e `width` nos três navegadores, mas o `d` não
  anima no Safari nem por CSS nem pela Web Animations API. Um laço único de
  `requestAnimationFrame` cobre tudo.

### A4 — Custo medido do laço de quadros: cerca de 1 ms por quadro para 1000 retângulos
- Fonte: teste em WebKit e Chromium sem janela (mediana de 1 ms e 0,7 ms; p95 de 2 ms e 1,3 ms)
- Contradiz a spec: não.

### A5 — Tokens cria 15 pontos por request, e uma request nova move todas as colunas
- Fonte: `skill/scripts/painel.html:411-421`
- Contradiz a spec: parcial. Numa sessão de 400 requests são 6000 círculos. "As colunas
  deslizam para a esquerda" anima todos eles a cada request nova, a cada 3 s.
- Pergunta que levanta: aceitamos o custo, pomos um teto (acima de N elementos o gráfico
  troca direto), ou só a coluna nova anima e as outras se reposicionam sem movimento?

### A6 — Células e listas em HTML ficam fora do mecanismo por chave da spec
- Fonte: `painel.html:525` (`seq-bar`), `:558` (`prov`), `:529`/`:537` (`radar-leg`), `:460` (`features`), `:380-394` (`etapas`), `:580` (`fases`), `:598` (`hist`), `:605` (`ativ`)
- Contradiz a spec: parcial. A spec diz que as células de Sequência e Provas acendem, mas elas
  são `<i>` montados por texto, fora do `pintar`, que é só para SVG.
- Pergunta que levanta: o mesmo ponto de reconciliação serve para HTML? Ou os itens de lista
  são reaproveitados por chave e só trocam o conteúdo quando ele mudou, recebendo um realce
  curto?

### A7 — Os itens de lista reaproveitados herdam atributos de acessibilidade e cliques antigos
- Fonte: `painel.html:587-589` (`aria-current` nunca é removido, `onclick` religado a cada leitura), `:464`; testes `test_painel.py:1775-1778`, `:1869`
- Contradiz a spec: parcial. Os testes clicam em `li.children[0]` e montam cada item com
  `innerHTML`. O teste `:1869` proíbe qualquer `NN:NN` no HTML da fase, e isso inclui
  atributos: a chave não pode carregar hora.
- Pergunta que levanta: resolvida junto com A6. Reescrever o `innerHTML` só quando o texto
  mudou preserva cliques, acessibilidade e testes.

### A8 — Regras de CSS que dependem de ordem mudam de alvo quando um item sai esmaecendo
- Fonte: `painel.html:189` (`.ativ li:first-child`), `:205` (`.leg li:first-child`)
- Contradiz a spec: parcial. Um item que sai esmaecendo continua no DOM e segue contando como
  filho.
- Pergunta que levanta: resolvida junto com A6. Nas listas, o item que sai sai direto, e só o
  SVG esmaece.

### A9 — O truque de desenhar a linha conflita com as linhas que já são tracejadas
- Fonte: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/pathLength; `painel.html:415`, `:427`, `:532`, `:541`
- Contradiz a spec: parcial. "Linhas se desenham do começo ao fim" usa o tracejado da própria
  linha. Grades, anéis do radar e a base da onda já são tracejados.
- Pergunta que levanta: só as linhas contínuas se desenham, e as tracejadas entram com fade?

### A10 — Até agora, toda animação aprovada no painel usou só deslocamento e opacidade
- Fonte: `docs/vesta/mockups/2026-09-29-graficos-laterais/relatorio.md:39-40`
- Contradiz a spec: parcial. Animar `x`, `height` e `d` é o primeiro movimento fora disso. O
  detector da vesta-interface pode acusar. Isso é uma inferência: o texto das regras MOV não
  está no repositório.
- Pergunta que levanta: aceitamos essa animação e refutamos o alarme com a medição de A4, ou
  restringimos o movimento a deslocamento e opacidade?

### A11 — Número contando numa fonte de largura variável faz o texto tremer
- Fonte: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-variant-numeric; `painel.html:407` (Rajdhani no centro do arco), `:499`, `:524`
- Contradiz a spec: parcial. Os números grandes usam Rajdhani, centralizada. Se a fonte não
  tiver algarismos de largura fixa, o número treme enquanto conta.
- Pergunta que levanta: só contam os números em fonte monoespaçada? Ou todos, trocando para
  algarismos fixos?

### A12 — O favicon pisca enquanto há pergunta pendente
- Fonte: `painel.html:636`; `docs/vesta/specs/2026-09-28-rodada-no-painel-design.md:89`
- Contradiz a spec: parcial. O critério "nada se move além do pulso" vale para a página, não
  para a aba.
- Pergunta que levanta: o critério passa a dizer "na página"?

### A13 — `@property` com herança recalcula a página inteira a cada quadro da transição
- Fonte: https://web.dev/blog/at-property-performance, https://developer.mozilla.org/en-US/docs/Web/CSS/@property
- Contradiz a spec: não. A troca de estado é rara e dura 0,3 s. O `initial-value` precisa ser
  uma cor literal, e o primeiro bloco `:root` fica intacto por causa de
  `test_cores_novas_no_root` (`test_painel.py:1520`).

### A14 — Aba em segundo plano congela os quadros e atrasa a leitura
- Fonte: https://developer.chrome.com/blog/timer-throttling-in-chrome-88, https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame
- Contradiz a spec: não. Com o tempo medido em absoluto, a animação termina sozinha na volta.
  Na volta vale também ler de imediato e desenhar sem animação.

### A15 — Durações e curvas recomendadas batem com a spec
- Fonte: https://www.nngroup.com/articles/animation-duration/, Material 3 motion tokens, Heer & Robertson 2007
- Contradiz a spec: não. Faixa de 100–400 ms, desaceleração no fim e entrada um pouco mais
  longa que a saída. Escalonamento de 20–40 ms por item, com teto. Animar só o que mudou. A
  curva que o odômetro já usa (`cubic-bezier(0.16,1,0.3,1)`, `painel.html:213`) serve.

### A16 — O `<defs>` com a hachura das barras precisa sobreviver à reconciliação
- Fonte: `painel.html:425`, `:430`
- Contradiz a spec: não. Entra como item com chave própria.

## Fila do grill

1. A2 — como provar o comportamento nos testes (trava o plano)
2. A6 — mecanismo para HTML: reconciliação genérica ou troca de conteúdo quando muda (resolve A7 e A8)
3. A1 — arco com desenho próprio por quadro
4. A5 — custo dos Tokens: teto ou só a coluna nova anima
5. A9 — linhas tracejadas: fade em vez de desenho
6. A10 — aceitar animação de geometria, fora do deslocamento e da opacidade
7. A11 — números contando em fonte de largura variável
8. A12 — critério "nada se move" limitado à página
