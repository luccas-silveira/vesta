# Plano — animações do painel

- **Objetivo:** o painel se monta uma vez na abertura e depois anima só o que mudou nos dados, reaproveitando os elementos por chave em vez de redesenhar tudo a cada 3 s.
- **Spec:** `docs/vesta/specs/2026-09-29-animacoes-do-painel-design.md`
- **Comando de teste:** `python3 -m unittest discover -s test -v && python3 -m unittest discover -s skill/scripts -v`
- **Pastas de tela:** `skill/scripts/painel.html`
- **Mockup:** `docs/vesta/mockups/2026-09-29-animacoes-do-painel/index.html` (tela existente, uma direção)

Contexto que vale para as três etapas:

- `skill/scripts/painel.html` é uma página única, sem build e sem dependência. O `<script>` principal consulta `/estado` a cada 3 s (`puxar`, `painel.html:638`) e chama `render()` (`:486`).
- Hoje cada gráfico apaga e recria tudo a cada leitura (`g.innerHTML=''`).
- O mockup aprovado é uma cópia do `painel.html` com a mudança pronta e funcionando. O motor fica em `docs/vesta/mockups/2026-09-29-animacoes-do-painel/index.html:529-624`, entre `// Movimento:` e a linha do `visibilitychange`. As funções dos gráficos e das listas estão reescritas no mesmo arquivo. A implementação copia de lá.
- Nada do mockup a partir de `/* dados de exemplo */` (`:751`) em diante vai para o painel. O CSS `.demo` (`:227-231`) também fica fora.
- Os testes da página rodam o script num navegador simulado em Node: `HARNESS` em `skill/scripts/test_painel.py:1733-1782`, chamado por `FaixaUnicaNoNavegador.rodar` (`:1808-1817`). Eles pulam quando não há `node`.

## Etapa 1 — Simulação de página que roda o painel inteiro

- **Tela:** não.
- **Arquivos:** muda `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - A simulação roda o `render()` completo com um estado de painel em execução, sem erro. O estado tem `momento.tipo` `rodando`, 4 etapas (1 feita, 1 atual, 2 pendentes), `sessao` com `entrada`, `ritmo`, `ferramentas`, `contexto`, `janela`, `saida`, `duracao_s` e `requests`, `hist` com 140 `dias` e 24 `horas`, 3 `features`, `tempos` e `rodada` com fases, histórico e atividade. É o mesmo formato que `painel.py` devolve em `/estado`.
  - Depois do `render()`, cada gráfico (`#arco`, `#pontos`, `#colunas`, `#ferr`, `#dias`, `#radar`, `#onda`, `#rel`) tem pelo menos um elemento filho. As listas `#etapas`, `#fases`, `#hist` e `#ativ` têm um item por entrada do estado.
  - A simulação não define `requestAnimationFrame` (`typeof requestAnimationFrame === 'undefined'` dentro da página), para que o painel vá direto ao valor final.
  - Os testes existentes de `FaixaUnicaNoNavegador` continuam passando sem mudança nas asserções.
- **Como fazer:**
  - Ampliar a classe `El` do `HARNESS` (`test_painel.py:1737-1758`) com:
    - `parentNode`, gravado por `append`/`appendChild`/`insertBefore`. Um nó que muda de pai sai da lista `children` do pai antigo.
    - `remove()`, `insertBefore(novo, ref)` (com `ref` nulo, anexa no fim), `nextSibling` (o próximo em `children` do pai, ou `null`) e `firstChild` coerente com `children`. O `_first` só vale quando `children` está vazio, como hoje.
    - `attributes` (lista de `{name, value}` a partir de `attrs`), `hasAttribute`, `toggleAttribute(nome, forcar)`, `cloneNode()` (cópia rasa de tag e `attrs`), `style.setProperty` (no-op), `insertAdjacentHTML` (anexa ao `_html`), `tagName` (maiúsculo para HTML, como no navegador; nos SVG criados por `createElementNS`, a tag como veio) e `outerHTML` igual a `outer`.
  - Tirar `requestAnimationFrame` e `cancelAnimationFrame` do contexto (`:1760-1766`). Os outros temporizadores seguem no-op.
  - Acrescentar à simulação um segundo modo, escolhido pelo cenário: define `D` e chama `render()` em vez de `rodada()`. Devolve, para cada id pedido, a contagem de filhos e o `outer` deles. O modo atual (`rodada`) fica como está.
  - Criar a classe de teste nova ao lado de `FaixaUnicaNoNavegador`, com o estado de exemplo acima escrito no próprio teste.

## Etapa 2 — Motor de movimento e gráficos reaproveitados por chave

- **Tela:** sim. Implementa a abertura e as mudanças dos gráficos do mockup: Contexto, Tokens, Tempo, Ferramentas, Dias, Radar, Onda e Relógio; a transição do acento entre estados; a hachura de progresso que cresce; o lampejo nos rótulos dos gráficos.
- **Arquivos:** muda `skill/scripts/painel.html` e `skill/scripts/test_painel.py`.
- **O que prova a etapa** (na simulação da etapa 1, salvo quando dito):
  - Duas leituras com os mesmos dados deixam cada filho de `#arco`, `#pontos`, `#colunas`, `#ferr`, `#dias`, `#radar`, `#onda` e `#rel` como o mesmo objeto. O teste marca os objetos depois do primeiro `render()` e confere que todos seguem marcados depois do segundo, e que a contagem não mudou.
  - Uma request nova (um valor a mais em `sessao.entrada`) acrescenta exatamente 15 círculos a `#pontos`, e os círculos antigos seguem sendo os mesmos objetos. O `cy` do círculo de cabeça da coluna nova termina no valor final (`H - v/max*H`), não no de partida.
  - Mudar `tempos['2']` faz a barra da etapa 2 em `#colunas` terminar com a `height` final e o texto do valor igual ao novo número. Uma etapa que some de `tempos` tem a coluna removida.
  - Uma feature que sai de `features` tem o círculo, a linha e o número dela removidos de `#radar`. Uma que entra acrescenta os três.
  - Mudar `sessao.contexto` faz o arco de uso terminar no percentual novo: o `d` do traço de uso é igual ao desenhado direto para esse percentual, e o texto central mostra o percentual novo com uma casa decimal.
  - Mudar a ordem de `sessao.ferramentas` mantém o rótulo de cada ferramenta como o mesmo objeto, com `y` na posição da linha nova.
  - Depois de cada `render()`, não sobra nenhuma interpolação pendente (sem `requestAnimationFrame`, tudo vai direto ao final).
  - A interpolação de valores (`mistura`, exposta no escopo global da página):
    - Com o mesmo esqueleto, interpola cada número: `M0 0L10 10` para `M10 0L20 20` em 0.5 dá `M5 0L15 15`.
    - Esqueletos diferentes (`M0 0L10 10` e `M0 0Z`) devolvem `null`.
    - Número igual nos dois lados fica exatamente como está, o que protege as flags `0 1` de um arco.
    - Em texto, a quantidade de casas decimais do destino é preservada (`12.3k` para `13.1k`).
    - Em texto, o zero à esquerda do destino também é preservado (`req 009` para `req 012` continua com três dígitos).
  - O código-fonte da página:
    - Registra `--acento` com `@property` e `syntax:'<color>'`, com transição no `body`.
    - Tem a transição de largura em `.hachura .cheio`.
    - Tem as duas desligadas sob `prefers-reduced-motion: reduce`.
    - Consulta `matchMedia('(prefers-reduced-motion: reduce)')` no script.
    - Não contém nada do mockup (`mockup · simular`, `ACOES`, `dados de exemplo`).
    - O primeiro bloco `:root{...}` fica igual (`test_cores_novas_no_root`, `test_painel.py:1520`).
  - Na verificação da tela real (passo 5 da vesta-interface, servida pelo `vesta.py painel`), medido no navegador:
    - Com o painel parado por mais de 3 s, nenhum elemento é recriado e nenhuma animação roda fora o pulso.
    - A abertura termina em menos de 1 s.
    - Com `prefers-reduced-motion: reduce`, nenhuma animação roda.
    - O console fica sem erro, e não há rolagem lateral em 375.
- **Como fazer:**
  - Copiar do mockup para `skill/scripts/painel.html`:
    - (a) O motor inteiro, `index.html:529-624`, de `// Movimento:` até a linha do `visibilitychange`, no lugar do `const pintar=...` atual (`painel.html:508`). O `pintar` novo substitui o antigo com a mesma assinatura `pintar(g, xs)`.
    - (b) As funções `arco`, `pontos`, `colunas`, `ferr`, `dias`, `radar`, `onda` e `relogio` do mockup (`:408`, `:429`, `:440`, `:456`, `:625`, `:644`, `:658`, `:679`), no lugar das atuais.
    - (c) O CSS de `index.html:222-226`, logo depois da regra `@media (prefers-reduced-motion:reduce){.vivo{animation:none}}` (`painel.html:221`).
  - Em `render()`, pôr `abrindo=false;` logo depois de `novos();` (mockup `:523`), e trocar os três `textContent` de `n-req`, `n-ferr` e `n-saida` por `escreve(...)`, como no mockup.
  - Não mudar nesta etapa `etapas`, `rodada`, `features`, `seq` e `provas`: são da etapa 3. O `radar` do mockup pinta também a legenda `#radar-leg` com `pintar`, e isso entra já aqui.
  - Expor `mistura` já é automático: é uma função de topo no script.
  - O motor depende de `h`, `com`, `escreve` e `toca`, que estão no bloco copiado.
  - Não usar o nome global `k` para nada novo: `k` é a formatação de números (`painel.html:367`).

## Etapa 3 — Listas, células e rótulos reaproveitados

- **Tela:** sim. Implementa do mockup: a etapa que fica verde acende a linha e troca o selo; a fase que muda de estado acende; o item novo de histórico e de atividade entra deslizando de cima; as células de Sequência e Provas trocam com fade; a palavra de estado e o percentual trocam com fade; os rótulos contam e acendem.
- **Arquivos:** muda `skill/scripts/painel.html` e `skill/scripts/test_painel.py`.
- **O que prova a etapa** (na simulação da etapa 1):
  - Duas leituras com os mesmos dados deixam como os mesmos objetos cada `li` de `#etapas`, `#fases`, `#hist`, `#ativ` e `#features` e cada célula de `#seq-bar` e `#prov`.
  - Uma atividade nova no topo (`rodada.atividade` ganha um item na frente e `n_atividade` sobe 1) deixa os `li` antigos de `#ativ` como os mesmos objetos. O `li` novo é o primeiro, e a contagem sobe 1.
  - Quando a fase atual passa a feita e a seguinte vira atual, o `li` de cada fase segue o mesmo objeto. O que deixou de ser atual perde `aria-current`, e o novo atual tem `aria-current="step"`.
  - Depois de uma segunda leitura, clicar no botão de uma fase com documento (`li.children[0].onclick`) abre esse documento: o cabeçalho do leitor muda para a fase clicada. O clique continua valendo num elemento reaproveitado.
  - Quando uma etapa pendente vira feita, o `li` dela segue o mesmo objeto, a classe inclui `feita` e o selo diz `verde`.
  - Uma pergunta do histórico que era pendente (`resposta` nula) e passa a respondida segue o mesmo `li`, perde a classe `pend` e mostra a resposta.
  - Depois de uma mudança de estado, `#palavra` mostra a palavra nova, `#pct` o percentual novo e `#n-req` o número novo de requests.
  - Os testes existentes de `FaixaUnicaNoNavegador` continuam passando sem mudança nas asserções. Isso inclui `test_painel.py:1869`: nenhum `NN:NN` no HTML de uma fase feita. As chaves nunca viram atributo.
  - Na verificação da tela real (passo 5 da vesta-interface, servida pelo `vesta.py painel`):
    - Com o painel parado por mais de 3 s, nenhum `li` nem célula é recriado.
    - O console fica sem erro, e não há rolagem lateral em 375.
- **Como fazer:**
  - Copiar do mockup para `skill/scripts/painel.html` as funções `etapas` (`index.html:389`), `features` (`:480`), `seq` (`:638`), `provas` (`:671`) e `rodada` (`:693`), no lugar das atuais.
  - Em `render()` e `odo()`, trocar os `textContent` de `#palavra`, `#desc`, `#obs`, `#odo-e` e `#odo-s` por `escreve(...)`, exatamente como no mockup (`:510` e `:669`).
  - As listas deixam de usar `innerHTML` por item: cada item é montado com `h(tag, atributos, ...filhos)`, e o texto que divide o elemento com outro filho vai num `<span>` próprio. Exemplos: o título da etapa, e a resposta livre do histórico ao lado do `<em>livre</em>`.
  - O botão da fase continua sendo `li.children[0]`, com `onclick` religado a cada leitura. O `aria-current` e o `aria-pressed` saem como atributos do nó novo, e o reconciliador remove os que faltam.
  - Chaves: `'e'+id` nas etapas, `id` da fase, `'h'+índice` no histórico, `n_atividade - índice` na atividade e `topico` nas features.
