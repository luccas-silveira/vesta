# Plano — painel da Vesta

- **Objetivo:** um painel local, só biblioteca padrão, que mostra a execução da Vesta, os
  documentos da feature e os instrumentos da sessão, subido pelo `hook-inicio`; o wayfinder e o
  painel antigo saem.
- **Spec:** `docs/vesta/specs/2026-09-25-painel-da-vesta-design.md`
- **Comando de teste:** `python3 -m unittest discover -s test -v && python3 -m unittest discover -s skill/scripts -v`
- **Pastas de tela:** `skill/scripts/painel.html`
- **Mockup:** `docs/vesta/mockups/2026-09-25-painel-da-vesta/index.html`

Fora deste plano, de propósito: "commits no tempo" (o mockup aprovado não tem esse gráfico) e
custo em dinheiro (precisa de tabela de preços; o instrumento mostra só tokens).

Padrões a seguir: testes em `unittest`, repositório git descartável por teste, como
`skill/scripts/test_vesta.py:21-40` (`Base.setUp`). Todo arquivo novo é só biblioteca padrão.
`painel.py` importa de `vesta.py` (`raiz` :34, `ler` :45, `encerrada` :113, `proxima` :122,
`PASTA`, `LIMITE_TENTATIVAS`) com `sys.path` apontando para a própria pasta.

---

## Etapa 1 — Dados da execução e das features

- **Tela:** não.
- **Arquivos:** criar `skill/scripts/painel.py`, `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `momento(estado)` devolve `{"tipo", "texto"}`: `None` → `vazio`, "Nenhuma execução neste
    projeto"; `espera == "plano"` → `plano`, "Esperando aprovação do plano"; `espera ==
    "interrompida"` → `pausada`, "Pausada na etapa N — <motivo>"; alguma etapa `travada` →
    `travada`, "Travada na etapa N depois de 3 tentativas"; todas `feita` → `concluida`,
    "Concluída — K de K etapas com prova"; senão `rodando`, "Rodando na etapa N de K", onde N é
    a posição (1-based) da primeira pendente.
  - `features(raiz)` agrupa `docs/vesta/{specs,research,plans,mockups}` por data + tópico:
    `specs/2026-01-02-abc-design.md`, `research/2026-01-02-abc-research.md`,
    `plans/2026-01-02-abc.md` e a pasta `mockups/2026-01-02-abc/` viram uma feature `abc`,
    data `2026-01-02`, com os caminhos de cada passo; passo sem arquivo é `None`. Grill é
    `True` quando a spec contém a linha `## Decisões do grill`. Ordem: data decrescente, depois
    tópico. Sem `docs/vesta/`: lista vazia. Arquivo fora do padrão de nome é ignorado.
  - `feature_do_plano(features, plano)` acha a feature cujo plano é o caminho do estado;
    `"chat"` ou caminho desconhecido → `None`.
  - `tempo_etapas(raiz, estado)` devolve, por etapa, minutos entre o commit do vermelho e o
    commit da prova verde (`git show -s --format=%ct`); etapa sem os dois → `None`.
  - `doc_seguro(raiz, caminho)` devolve o caminho absoluto só se, depois de `realpath`, ele
    fica dentro de `<raiz>/docs/vesta/` e é arquivo; `..`, caminho absoluto, link simbólico
    para fora e inexistente → `None`.
  - `dados(raiz)` junta tudo: `{"projeto": basename, "momento", "estado" (ou None),
    "erro" (texto quando o estado é ilegível, senão None), "features", "atual" (feature da
    execução ou a mais recente), "tempos"}`. Estado ilegível não levanta: vira `erro` e
    `momento` de tipo `ilegivel`, "Estado ilegível".
- **Como fazer:** estado lido por `vesta.ler(r)`, que devolve `None` ou levanta `ValueError`
  (`vesta.py:45-64`). Regex de nome: `^(\d{4}-\d{2}-\d{2})-(.+?)(-design|-research)?(\.md)?$`.

## Etapa 2 — Instrumentos da sessão

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/painel.py`, `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `pasta_sessoes(raiz)` devolve `~/.claude/projects/<raiz com / e . trocados por ->`, com
    `HOME` vindo do ambiente (o teste aponta `HOME` para uma pasta temporária).
  - `sessao(raiz)` lê o `.jsonl` modificado por último nessa pasta e devolve
    `{"inicio", "fim", "duracao_s", "requests", "entrada" (lista, uma por request, soma de
    input + cache_read + cache_creation), "saida" (total), "ferramentas" (lista de [nome,
    contagem] decrescente, nome sem prefixo `mcp__x__`), "contexto" (entrada da última
    request), "janela"}`.
  - Linhas `assistant` com o mesmo `requestId` contam uma request só (usa o último `usage`);
    `tool_use` conta todas.
  - `janela` é 200000, ou 1000000 quando alguma request passou de 200000.
  - Linha que não é JSON é pulada. Pasta ausente, nenhum `.jsonl`, ou nenhum `usage` → `None`.
  - `dados(raiz)` ganha a chave `"sessao"`.
- **Como fazer:** formato visto em `~/.claude/projects/*/*.jsonl`: `type`, `requestId`,
  `timestamp`, `message.usage.{input_tokens, cache_read_input_tokens,
  cache_creation_input_tokens, output_tokens}`, `message.content[].type == "tool_use"` com
  `name`. Comentário `ponytail:` na `janela`: heurística, o modelo não fica no registro.

## Etapa 3 — Servidor local

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/painel.py`, `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `python3 painel.py servir <raiz> <porta>` escuta em `127.0.0.1`.
  - `GET /estado` → 200, JSON de `dados(raiz)`.
  - `GET /doc?caminho=docs/vesta/specs/x.md` → 200, texto do arquivo; caminho recusado por
    `doc_seguro` → 404.
  - `GET /` → 200, `text/html`, conteúdo de `painel.html`; `GET /marked.js` → 200.
  - Qualquer outra rota → 404.
  - `GET /quem` → 200 com o texto `vesta-painel <raiz>`, usado pelo hook para saber se a porta
    é deste projeto.
  - Porta já ocupada → sai com código 0, sem erro.
  - O teste sobe o servidor em porta livre num subprocesso, faz as requisições com
    `urllib.request` e mata o processo no `tearDown`.
- **Como fazer:** `http.server.ThreadingHTTPServer` com `daemon_threads = True`, handler próprio
  herdando `BaseHTTPRequestHandler` (não `SimpleHTTPRequestHandler`, que segue link
  simbólico), `log_message` silencioso. `painel.html` e `marked.js` lidos da pasta do script.
  Esta etapa cria `skill/scripts/painel.html` com `<!doctype html><title>Vesta</title>` e baixa
  `skill/scripts/marked.js` de `https://cdn.jsdelivr.net/npm/marked@12/marked.min.js`.

## Etapa 4 — A página

- **Tela:** sim — o mockup inteiro, no estado terminal sóbrio com a faixa de instrumentos.
- **Arquivos:** mudar `skill/scripts/painel.html`, `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - A página servida contém os pontos de montagem: `id="momento"`, `id="etapas"`,
    `id="lista"`, `id="leitor"`, `id="inst"`, `id="gauge"`, `id="spark"`, `id="etapas-g"`,
    `id="ferr"`, `id="aviso-sessao"`, e carrega `/marked.js` e `/estado`.
  - A página não carrega nada de fora de `127.0.0.1` além do Google Fonts.
  - Verificação visual (não automatizada): abrir o painel deste repositório no Safari com um
    estado de exemplo rodando, travado, pausado, sem execução, ilegível e sem sessão, e
    comparar com o mockup.
- **Como fazer:** partir de `docs/vesta/mockups/2026-09-25-painel-da-vesta/index.html`. Tirar a
  barra de estados do rodapé e os dados fixos; `fetch('/estado')` a cada 3 s preenche tudo.
  Trilha: botão por passo, desabilitado quando o caminho é `None`; clicar faz
  `fetch('/doc?caminho=')` e renderiza com `marked.parse` no leitor; o mockup abre em aba nova
  (`/doc` serve o HTML como `text/html` quando o caminho termina em `.html`). Sem sessão:
  esconde `.inst.sessao` e mostra `#aviso-sessao`. Lista de features aparece quando o momento é
  `vazio` ou `ilegivel`; clicar numa feature a torna a da trilha. Cabeçalho mostra o nome do
  projeto e "atualizado há N s".

## Etapa 5 — O hook sobe o painel

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/vesta.py` (`hook_inicio`, :442), `skill/scripts/painel.py`,
  `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `porta(raiz)` é estável para o mesmo caminho e fica entre 4700 e 4799.
  - `subir(raiz)` em projeto sem `docs/vesta/` e sem `.claude/vesta/` → `None`, nada sobe.
  - Com Vesta e porta livre → sobe o servidor em segundo plano e devolve a URL; uma requisição
    a `/quem` responde este projeto.
  - Chamado de novo com o painel já de pé → devolve a mesma URL sem subir outro processo.
  - Porta ocupada por outro processo → tenta a próxima, até 100.
  - `hook-inicio` em projeto com Vesta e sem aviso pendente devolve `additionalContext` com
    "Painel deste projeto: http://localhost:N"; com aviso, a linha do painel vai junto do aviso.
  - Os testes existentes de `hook-inicio` em `test_vesta.py` continuam passando.
- **Como fazer:** porta base `4700 + int(sha1(raiz)[:4], 16) % 100`, varredura como
  `~/.claude/hooks/painel.sh:36-43`. Teste de porta com `socket.create_connection` e
  `urllib` em `/quem`. `subprocess.Popen([sys.executable, painel.py, 'servir', raiz, porta],
  start_new_session=True, stdin/stdout/stderr=DEVNULL)`, e espera até 2 s a porta abrir.
  `hook_inicio` importa `painel` dentro de `try`: qualquer falha do painel não pode derrubar o
  aviso da Vesta. O teste usa porta derivada de uma raiz temporária e mata o processo no fim.

## Etapa 6 — Sai o wayfinder e o painel antigo

- **Tela:** não.
- **Arquivos:**
  - `~/Code/vesta`: criar `test/test_sem_wayfinder.py`; mudar `README.md` e
    `docs/como-funciona.md` (o painel); apagar `panel/` e `docs/wayfinder/` (não rastreados).
  - `~/Code/claude-tooling`: apagar `panel/`, `config/claude/hooks/painel.sh`,
    `config/claude/skills/wayfinder/`; mover `docs/wayfinder/` para `docs/historico/wayfinder/`;
    tirar o registro do `painel.sh` de `config/claude/settings.json`; mudar `CLAUDE.md`,
    `README.md`, `docs/README.md`; criar `docs/decisions/00NN-painel-da-vesta.md` (próximo
    número) dizendo que 0011, 0012 e 0013 foram superados; `git config --unset core.hooksPath`.
  - `~/.claude`: apagar `skills/wayfinder/`, `hooks/painel.sh`, o registro dele em
    `settings.json` (:215) e `~/.claude/painel/`; matar os servidores antigos listados lá.
  - Outros projetos: apagar `panel/` com `panel/.versao` e `docs/wayfinder/` que tenha só
    `TRACKER.md` e `como-construir-um-mapa.md`, **depois de mostrar a lista ao usuário e ele
    confirmar**. `docs/wayfinder/` com mapas reais fica.
- **O que prova a etapa:**
  - `test_sem_wayfinder.py`: nenhum arquivo em `skill/`, `commands/` e `README.md` cita
    "wayfinder"; `README.md` cita `skill/scripts/painel.py`.
  - Os testes de `test_docs.py` passam com o README novo (todo caminho citado existe).
- **Como fazer:** no claude-tooling, um commit só com a remoção e o espelho juntos
  (`backup/sync.sh:20` espelha `~/.claude`). O ADR segue o formato dos que existem em
  `docs/decisions/`. A remoção em `~/.claude` e nos outros projetos não tem commit na Vesta;
  a prova desta etapa é o teste da Vesta, e o restante é conferido por `ls` no fechamento.
