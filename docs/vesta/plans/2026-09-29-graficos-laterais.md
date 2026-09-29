# Plano — gráficos laterais do painel

- **Objetivo:** oito widgets novos nas laterais do painel (Dias, Sequência, Radar, Onda, Odômetro, Provas, Relógio, Pulso), com dados reais das sessões do projeto.
- **Spec:** nenhuma. Caminho pequeno: o design aprovado no chat e o mockup valem como spec.
- **Comando de teste:** `python3 -m unittest discover -s test -v && python3 -m unittest discover -s skill/scripts -v`
- **Pastas de tela:** `skill/scripts/painel.html`
- **Mockup:** `docs/vesta/mockups/2026-09-29-graficos-laterais/index.html` (tela existente, uma direção)

Contexto que vale para as duas etapas: o painel (`skill/scripts/painel.py`) serve `/estado`, que o navegador consulta a cada 3 s (`painel.html`, `puxar`). `dados(r)` (`painel.py:306`) monta o JSON. `sessao(r)` (`painel.py:121`) lê o `.jsonl` mais recente em `pasta_sessoes(r)`, ignorando sessões do SDK (`_do_sdk`). Requisição = `requestId` único de linha `assistant` com `message.usage`.

## Etapa 1 — Dados de histórico e ritmo no servidor

- **Tela:** não.
- **Arquivos:** muda `skill/scripts/painel.py` e `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `painel.historico(r)` devolve `{'dias': [140 ints], 'horas': [24 ints]}`. `dias` termina em hoje (hora local), o mais antigo primeiro; cada valor é o número de requisições únicas naquele dia, somando todas as sessões não-SDK da pasta do projeto, não só a mais recente. `horas[h]` é o total de requisições na hora local `h`, sobre todas as sessões e todos os dias.
  - Requisição repetida entre dois arquivos (mesmo `requestId`) conta uma vez. Sessão do SDK não conta. Linha sem `timestamp`, linha que não é JSON e requisição mais velha que 140 dias entram em `horas` mas não em `dias`.
  - Sem sessões: `dias` são 140 zeros e `horas` são 24 zeros, sem erro.
  - `painel.sessao(r)['ritmo']` é uma lista de 48 ints: o intervalo do primeiro ao último timestamp da sessão dividido em 48 trechos iguais, cada um com a contagem de requisições únicas cujo primeiro timestamp cai nele. A soma é `requests`. Sessão de um instante só (início igual ao fim): as requisições caem todas no trecho 0.
  - `dados(r)` inclui a chave `hist` com o resultado de `historico`.
  - Ler de novo sem o arquivo mudar não relê o arquivo (`open` não é chamado para arquivo com mesmo tamanho e mtime): o painel consulta a cada 3 s e as pastas de sessão passam de MB.
  - O teste existente de `sessao` que compara o dict inteiro (`test_painel.py:334`) passa a incluir `ritmo`.
- **Como fazer:** extrair o laço de leitura de `sessao` (`painel.py:130-152`) para `_ler(caminho)` que devolve `(usos, saidas, marcas, ferr, tempos)`, em que `tempos` é `{requestId: primeiro timestamp}` (`tempos.setdefault(rid, l['timestamp'])` onde hoje se grava `usos[rid]`). Cachear `_ler` por `(caminho, mtime, tamanho)` num dict de módulo (`# ponytail: cache sem limite, um item por arquivo de sessão`). `historico(r)` percorre `glob` de `*.jsonl` da `pasta_sessoes(r)` sem os `_do_sdk`, converte cada timestamp com `_instante(ts).astimezone()` e acumula. `ritmo` sai de `tempos` da sessão atual com `_instante`. Manter o restante do dict de `sessao` como está.

## Etapa 2 — Os oito widgets na tela

- **Tela:** sim. Implementa o mockup inteiro nas duas laterais: Dias, Sequência e Radar na esquerda abaixo de Tokens; Onda, Odômetro, Provas, Relógio e Pulso na direita abaixo de Ferramentas.
- **Arquivos:** muda `skill/scripts/painel.html` e `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `GET /` serve uma página que contém os ids `dias`, `seq-bar`, `radar`, `onda`, `odo`, `prov`, `rel` e `bat`, e a função `novos`.
  - A página servida não contém a data fixa `2026-09-29T12:00:00` do mockup (o dia de hoje vem de `new Date()`).
  - A página não contém dados de exemplo do mockup (`BASE.`, `DOCS=`).
  - Na ordem do HTML, `id="pontos"` vem antes de `id="dias"`, `id="seq-bar"` e `id="radar"` (coluna esquerda), e `id="ferr"` vem antes de `id="onda"`, `id="odo"`, `id="prov"`, `id="rel"` e `id="bat"` (coluna direita).
  - Cada widget com estado vazio tem o elemento `-v` (`dias-v`, `seq-w-v`, `radar-v`, `rel-v`, `prov-w-v`).
  - Na verificação da tela real (`vesta-interface`, passo 5, servida pelo `vesta.py painel`), os oito widgets aparecem com dados reais deste projeto, sem erro no console e sem rolagem lateral em 375.
- **Como fazer:** copiar do mockup `docs/vesta/mockups/2026-09-29-graficos-laterais/index.html` para `skill/scripts/painel.html`: (a) os blocos `<div class="inst novo">` (linhas 260-276 na esquerda e 357-380 na direita), (b) as regras CSS de `.novo` até `@media (prefers-reduced-motion…)` (linhas 202-220 e `@keyframes pulso`, linha 230), (c) as funções `vz`, `pintar`, `dias`, `seq`, `radar`, `onda`, `odo`, `provas`, `relogio`, `pulso`, `novos` (linhas 541-609), trocando `const HOJE=new Date('2026-09-29T12:00:00')` por `const HOJE=new Date()`. Chamar `novos()` no fim de `render()` do painel (o mockup já faz isso; `painel.html:456`). Não copiar barra de estados do mockup, `BASE`, `DOCS` nem os dados de exemplo. Usar os helpers que o painel já tem (`el`, `esc`, `pad`, `k`); se algum não existir em `painel.html`, copiar a definição do mockup. Os dados vêm de `D.hist` (etapa 1), `D.sessao.ritmo`, `D.features` e `D.estado`, exatamente como o mockup lê.
