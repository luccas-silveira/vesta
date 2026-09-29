# Pesquisa — rodada no painel

Spec: `docs/vesta/specs/2026-09-28-rodada-no-painel-design.md`

Frente externa: a doc oficial não cobre a resposta de AskUserQuestion por hook; os fatos
abaixo vêm de teste nesta máquina e do Knobler. Inspo pulado: o painel já tem linguagem
visual própria.

## Achados

### A1 — O Knobler já responde AskUserQuestion por fora do terminal
- Fonte: `~/.claude/hooks/knobler-ask.sh` (PreToolUse `AskUserQuestion`, timeout 600 em
  `~/.claude/settings.json`); teste nesta sessão: a pergunta apareceu no Knobler e a
  resposta dada lá voltou como resposta normal do menu.
- Contradiz a spec: sim
- Pergunta que levanta: com dois ganchos disputando a mesma pergunta, ela aparece no notch e
  no painel e quem responder primeiro não é garantido. O painel deve responder por conta
  própria, entregar a pergunta ao Knobler, ou o Knobler passa a ser só um dos lados de uma
  mesma fila?

### A2 — Preencher `answers` pelo `updatedInput` funciona e é o caminho limpo
- Fonte: `knobler-ask.sh` (allow + `updatedInput` com `questions` e `answers`; texto livre
  vence rótulos; múltiplos rótulos juntados por ", "); teste 1 desta sessão.
- Contradiz a spec: parcial (a spec deixou dois caminhos em aberto)
- Pergunta que levanta: nenhuma; fixa o caminho e descarta o "negar com recado".

### A3 — Negar com recado volta como erro
- Fonte: teste 2 desta sessão: `PreToolUse:AskUserQuestion hook error: Resposta dada pelo painel: {...}`.
- Contradiz a spec: parcial
- Pergunta que levanta: nenhuma; descartado por A2.

### A4 — Gancho espera 10 minutos por padrão
- Fonte: https://code.claude.com/docs/en/hooks-guide.md (timeout padrão 600 s, ajustável no
  campo `timeout`); o Knobler usa 570 s e devolve ao terminal no fim.
- Contradiz a spec: parcial ("sem prazo")
- Pergunta que levanta: passado o prazo, a pergunta volta ao terminal. Aceita um prazo longo
  fixo (por exemplo 1 hora), sabendo que a sessão fica parada esperando esse tempo?

### A5 — O painel local aceitar escrita abre porta para outra página responder por você
- Fonte: `skill/scripts/painel.py:172-212` (servidor em 127.0.0.1, sem `do_POST` hoje).
  Qualquer site aberto no navegador consegue mandar POST para `localhost`.
- Contradiz a spec: parcial
- Pergunta que levanta: sem uma senha gerada pelo servidor e conferida em cada resposta, um
  site qualquer poderia responder aos menus de uma sessão rodando com permissões liberadas.
  Pôr essa senha e conferir a origem do pedido?

### A6 — Decisões do painel de 25/09 que esta spec derruba
- Fonte: `docs/vesta/specs/2026-09-25-painel-da-vesta-design.md:19-21` (sobe só com
  `docs/vesta`; linha do tempo fora), `:77` e `:107-109` (sem hook novo; só o endereço, sem
  abrir o navegador, "aba nova por projeto vira ruído"); `docs/como-funciona.md:63-64`.
- Contradiz a spec: sim
- Pergunta que levanta: abrir o navegador na ativação traz de volta a aba por projeto que
  foi recusada em 25/09. Abrir só quando nenhuma página do projeto está aberta resolve?

### A7 — Testes travam o número de hooks
- Fonte: `test/test_plugin.py:29-36` (exatamente PostToolUse, SessionStart e Stop; PostToolUse
  só com `Bash`); `test/test_instalacao_real.py:27-31`.
- Contradiz a spec: parcial
- Pergunta que levanta: nenhuma; os testes mudam junto.

### A8 — O registro da sessão não é contrato, e a rodada passa a depender muito dele
- Fonte: `docs/vesta/specs/2026-09-25-painel-da-vesta-design.md:65-66`; formato visto nesta
  sessão: `Skill` com `input.skill`, AskUserQuestion com `toolUseResult.answers`.
- Contradiz a spec: parcial
- Pergunta que levanta: se uma versão do Claude Code mudar o formato, fase, histórico e
  atividade somem juntos. Aceita que o bloco mostre "registro em formato desconhecido" nesse
  caso, sem tentar adivinhar?

### A9 — As fases são lidas por Bash e por dois caminhos
- Fonte: esta sessão leu `spec.md` e `research.md` com `cat ~/.claude/skills/vesta/...`;
  `~/.claude/skills/vesta` aponta para `~/Code/vesta/skill`.
- Contradiz a spec: não
- Pergunta que levanta: o leitor reconhece os dois caminhos.

### A10 — Costura precisa de leitor novo
- Fonte: `skill/scripts/painel.py:113-122` (`sessao()` lê só o arquivo mais recente de uma
  pasta); `:96-98` (`pasta_sessoes` é por projeto).
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; reuso do laço de leitura e do filtro do SDK.

### A11 — São 22 pontos de texto livre nas instruções da Vesta
- Fonte: `skill/spec.md:12,15,29-32,39,43-45,62-66,72`; `skill/grill.md:3,9-12,33-37,61`;
  `skill/mockup.md:28,33,39-40,76-82`; `skill/plano.md:66-74`; `skill/execucao.md:92-101,115`;
  `skill/SKILL.md:13-15,67-87`. `test/test_mockup.py:67-90` confere frases de `mockup.md`.
- Contradiz a spec: não
- Pergunta que levanta: a escolha entre as duas direções do mockup mora na vesta-interface
  (outro repositório), que precisa de teste de contrato aqui.

### A12 — Servidor com várias threads, fila precisa de trava
- Fonte: `skill/scripts/painel.py:208` (`ThreadingHTTPServer`).
- Contradiz a spec: não

## Fila do grill

1. A1 — painel e Knobler: quem recebe a pergunta (trava A4, A5)
2. A5 — senha e origem nas respostas
3. A4 — prazo do gancho
4. A6 — abrir o navegador na ativação
5. A8 — formato desconhecido do registro
