# Plano — rodada no painel

- **Objetivo:** o painel acompanha a rodada inteira da Vesta (fase, histórico, atividade) desde
  a ativação da skill e responde às perguntas de menu, junto com o Knobler, valendo a primeira
  resposta.
- **Spec:** `docs/vesta/specs/2026-09-28-rodada-no-painel-design.md`
- **Comando de teste:** `python3 -m unittest discover -s test -v && python3 -m unittest discover -s skill/scripts -v`
- **Pastas de tela:** `skill/scripts/painel.html`
- **Mockup:** `docs/vesta/mockups/2026-09-28-rodada-no-painel/index.html`

Decisão tomada na aprovação do mockup: durante a execução, o bloco Rodada fica abaixo das
Etapas; antes da execução, fica no topo do centro. Cores: `--verde` e `--ciano` viram `#ff4d00`,
`--coral` vira `oklch(0.93 0 0)` (branco), como no mockup.

Padrões a seguir, valendo para toda etapa: só biblioteca padrão; testes em `unittest`, no
padrão de `skill/scripts/test_painel.py` (repositório descartável em `Base`, HOME temporário e
registros `.jsonl` em `SessaoBase` :294-315, servidor real em porta livre na classe `Servidor`
:406-440) e de `skill/scripts/test_vesta.py` (hook rodado em subprocesso com JSON no stdin,
`Base.hook` :57-60). Hook novo segue `rodar_hook` (`skill/scripts/vesta.py:432-440`): qualquer
exceção sai 0 sem saída. `painel.py` importa de `vesta.py` com `sys.path` na própria pasta
(`painel.py:18-20`).

Formato do registro de sessão (visto nesta máquina): cada linha é um JSON; tool_use vem em
`message.content[]` de linha `type: "assistant"` com `{type: "tool_use", id, name, input}`;
o resultado vem numa linha `type: "user"` com `message.content[]` contendo
`{type: "tool_result", tool_use_id, content}` e, na raiz da linha, `toolUseResult`. Para
AskUserQuestion, `toolUseResult` é `{questions, answers}` com `answers` = `{"<pergunta>": "<rótulo(s) juntados por ', ' ou texto livre>"}`.
A ativação é `name: "Skill"` com `input.skill == "vesta"`. Toda linha tem `timestamp` ISO.

---

## Etapa 1 — Leitor da rodada numa sessão

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/painel.py`, `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - Registro sem invocação da skill `vesta`: `rodada` devolve `formato: "nenhuma"`.
  - Sem arquivo de registro: `formato: "sem"`.
  - Registro com linhas JSON e nenhuma com `message.content` em lista: `formato: "desconhecido"`,
    sem fases, histórico nem atividade.
  - Com a invocação: as oito fases (`ativacao, spec, pesquisa, grill, mockup, plano, execucao,
    concluida`), cada uma com `estado` e `hora` (HH:MM, hora local). A ativação é `feita` ou
    `atual`; cada fase vira feita/atual pelo marco: tool_use Read com `input.file_path`, ou Bash
    com `input.command`, que contenha `skills/vesta/<arquivo>.md` ou `vesta/skill/<arquivo>.md`,
    com arquivo `spec→spec`, `research→pesquisa`, `grill→grill`, `mockup→mockup`,
    `plano→plano`, `execucao→execucao`. `execucao` também por Bash com `vesta.py criar` ou
    `vesta.py iniciar`. A fase atual é a do último marco; as anteriores sem marco são
    `pulada`; as posteriores, `pendente`. `concluida` é `atual` quando o estado da execução está
    encerrado (`vesta.encerrada`).
  - Marco de `skills/vesta-interface/...` não conta como fase.
  - Só conta o que vem depois da última invocação da skill (rodada anterior na mesma sessão
    fica fora).
  - Histórico em ordem: AskUserQuestion com `header`, `pergunta`, `multipla`, `resposta` (de
    `toolUseResult.answers`; `null` se ainda sem resultado), `livre` (verdadeiro quando a
    resposta não é nenhum rótulo nem junção de rótulos), `onde` e `hora`; texto do assistente
    (`message.content[].type == "text"`) como `{tipo: "mensagem", texto, hora}`. Uma pergunta
    com várias `questions` vira um item por questão.
  - `onde`: `painel` ou `knobler` quando `~/.claude/vesta/respostas.jsonl` tiver
    `{"tool_use_id": <id>, "onde": ...}` para aquele tool_use; `terminal` nos outros casos.
    Linha ilegível nesse arquivo é ignorada.
  - Atividade: todo tool_use da rodada, do mais recente ao mais antigo, até 200, com
    `ferramenta` (nome sem prefixo `mcp__x__`), `alvo` e `hora`; `n_atividade` com o total.
    Alvo: `file_path` para Read/Edit/Write; `command` para Bash (primeira linha, até 120
    caracteres); `pattern` para Grep/Glob; `url` ou `query` para buscas; `description` para
    Agent; `skill` para Skill; primeira `question` para AskUserQuestion; vazio nos demais.
  - Linha ilegível no meio do registro é pulada, o resto aparece.
  - Registro do SDK (`_do_sdk`) não é usado.
- **Como fazer:** nova função `rodada(r)` em `painel.py`, ao lado de `sessao()` (:113-153),
  reusando o laço que lê o `.jsonl` e o filtro `_do_sdk` (:105-110), `_instante` (:101-102) e
  `pasta_sessoes` (:96-98). Nesta etapa lê só o registro mais recente não-SDK da pasta do
  projeto (a costura é a etapa 2). Constantes no topo: `FASES` (lista das oito) e
  `MARCO = re.compile(r'(?:skills/vesta|vesta/skill)/(spec|research|grill|mockup|plano|execucao)\.md')`.
  Saída: `{formato, sessoes: [ids], inicio: 'HH:MM', fases, historico, atividade, n_atividade}`.
  `dados()` (:156-169) ganha a chave `rodada`.

## Etapa 2 — Costura entre sessões

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/painel.py`, `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - Duas sessões em pastas de projeto diferentes sob `~/.claude/projects/`, as duas citando o
    caminho da spec da feature atual (`docs/vesta/specs/<data>-<topico>-design.md`), viram uma
    rodada só: `sessoes` com os dois ids em ordem de tempo; histórico e atividade intercalados
    por `timestamp`; fases calculadas sobre o conjunto.
  - A rodada começa na última invocação da skill `vesta` da sessão mais antiga do conjunto.
  - Sessão que não cita a spec fica fora, mesmo na pasta do projeto.
  - Registro modificado antes da data da spec fica fora sem ser lido.
  - Sem spec ainda para a feature: só a sessão atual, como na etapa 1.
  - A sessão atual (registro mais recente da pasta do projeto) sempre entra.
- **Como fazer:** em `rodada(r)`, pegue a feature atual como `dados()` faz (`feature_do_plano`
  ou a primeira de `features()`, :48-71). Com spec, varra
  `glob(~/.claude/projects/*/*.jsonl)`, filtrando por `os.path.getmtime >= meia-noite da data da
  spec` antes de abrir, e por conter a string do caminho da spec. Junte as linhas de todas,
  ordene por `timestamp`, e aplique a leitura da etapa 1 sobre a lista única.

## Etapa 3 — Ponte de perguntas no servidor

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/painel.py`, `skill/scripts/vesta.py`,
  `skill/scripts/test_painel.py`, `skill/scripts/test_vesta.py`, `docs/como-funciona.md`.
- **O que prova a etapa:**
  - `GET /aberto` responde `{"aberto": false}` antes de qualquer `GET /estado`, `true` até 10 s
    depois do último `GET /estado`, `false` depois.
  - `POST /pergunta` com `{id, questions, knobler}` enfileira; `GET /estado` passa a trazer
    `perguntas` com as pendentes em ordem de chegada, cada uma com `{id, questions, knobler, estado}`.
  - `GET /pergunta/<id>`: `{"estado": "pendente"}`; depois de `POST /resposta/<id>` com
    `{"answers": {"<pergunta>": {"labels": [...], "text": "..."}}}`, devolve
    `{"estado": "respondida", "answers": ...}` e a pergunta sai de `perguntas`; `abandonada`
    quando a página não pede `/estado` há mais de 15 s; `desconhecida` para id que não existe.
  - `POST /pergunta/<id>/encerrar` com `{"motivo": "knobler"}`: a pergunta fica em
    `perguntas` com `estado: "outro"` por 5 s e depois sai; `GET /pergunta/<id>` devolve
    `encerrada`.
  - `POST /resposta/<id>` para id encerrado ou respondido: 409, nada muda.
  - Corpo que não é JSON ou sem os campos: 400.
  - Duas threads postando ao mesmo tempo não perdem pergunta (fila com `threading.Lock`).
  - `painel.achar(r)`: devolve a url do servidor de `r` já no ar (sequência de portas a partir de
    `porta(r)`, parando na primeira porta livre) ou `None`, sem subir nada.
  - `vesta.py aberto <cwd>` sai 0 quando o painel da raiz de `<cwd>` responde `aberto: true`,
    1 sem painel, com painel fechado, ou em qualquer erro; nunca imprime nada.
  - `test_estado_devolve_dados_da_raiz` continua passando (comparar sem a chave `perguntas`,
    que vem da memória do servidor).
- **Como fazer:** em `servir()` (`painel.py:172-212`) acrescente `do_POST` e o estado em memória
  (`perguntas` dict por id + lista de ordem, `visto` = hora do último `/estado`), protegidos por
  um `threading.Lock`. `/estado` grava `visto` e soma `perguntas` ao JSON de `dados(r)`.
  `achar(r)` reaproveita `_quem`/`_ocupada` (:219-232) com o mesmo laço de `subir` (:235-254).
  Em `vesta.py`, comando `cmd_aberto` no dicionário `COMANDOS` (:557), com saída por código:
  trate como exceção à forma de imprimir resultado dos outros comandos (ver `main`, :560-576).
  `docs/como-funciona.md` cita o comando `aberto` (exigido por `test/test_docs.py:143-149`).

## Etapa 4 — Hook de menu

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/vesta.py`, `skill/hooks/hooks.json`,
  `skill/scripts/test_vesta.py`, `test/test_plugin.py`.
- **O que prova a etapa:**
  - Sem painel do projeto no ar, ou com `aberto: false`: o hook sai sem saída (menu no terminal)
    em menos de 2 s, sem tocar no Knobler.
  - Painel aberto e Knobler fora do ar: posta no painel, espera; resposta dada no painel sai como
    `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
    "updatedInput": {"questions": <originais>, "answers": {"<pergunta>": "<texto ou rótulos juntados por ', '>"}}}}`;
    texto livre não vazio vence os rótulos.
  - Painel aberto e Knobler no ar (servidor falso de teste em porta indicada por
    `KNOBLER_PORT`): posta nos dois com o mesmo id e `source` = nome da pasta do `cwd`; resposta
    no Knobler (`GET /ask/<id>` com `answered: true` e `answers` no mesmo formato) sai como acima
    e o hook chama `POST /pergunta/<id>/encerrar` no painel; resposta no painel faz o hook chamar
    `POST /ask/<id>/cancel` no Knobler.
  - Knobler cancelado (`cancelled: true`): segue esperando o painel.
  - Painel devolve `abandonada`: se o Knobler recebeu, segue esperando só ele; se não, sai sem
    saída.
  - Prazo: com `VESTA_PRAZO_MENU` curto no teste (padrão 3600 s), o hook cancela no Knobler e
    sai sem saída.
  - Erro de rede no meio: cancela no Knobler o que mandou e sai sem saída; código 0 sempre.
  - Cada resposta entregue grava uma linha `{"tool_use_id", "onde": "painel"|"knobler"}` em
    `~/.claude/vesta/respostas.jsonl`.
  - `hooks.json` tem `PreToolUse` com matcher `AskUserQuestion`, comando
    `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vesta.py" hook-menu || true` e `"timeout": 3660`.
  - `test/test_plugin.py` passa a aceitar `PreToolUse` além dos três de antes, e confere o
    matcher e o timeout.
- **Como fazer:** `hook_menu(entrada)` em `vesta.py`, registrado em `HOOKS` (:557), rodado por
  `rodar_hook`. Use `painel.achar(raiz(cwd))` e `urllib.request` com timeout de 1 a 2 s por
  chamada; consulta a cada 1 s. Knobler em `http://localhost:${KNOBLER_PORT:-4477}` com as rotas
  `POST /ask`, `GET /ask/<id>`, `POST /ask/<id>/cancel` (o `knobler-ask.sh` em
  `~/.claude/hooks/` mostra o formato; `NotchAPIServer.swift:418` lista as rotas). Id da
  pergunta: `menu-<tool_use_id>`.

## Etapa 5 — Painel na ativação da skill

- **Tela:** não.
- **Arquivos:** mudar `skill/scripts/vesta.py`, `skill/scripts/painel.py`,
  `skill/hooks/hooks.json`, `skill/scripts/test_vesta.py`, `skill/scripts/test_painel.py`,
  `test/test_plugin.py`.
- **O que prova a etapa:**
  - PreToolUse de `Skill` com `tool_input.skill == "vesta"` em projeto sem `docs/vesta` nem
    `.claude/vesta`: o painel sobe e não cria pasta nenhuma no projeto.
  - Sem página aberta: chama o abridor (`open <url>`, trocável por `VESTA_ABRIR` no teste) uma
    vez. Com página aberta: não abre.
  - Skill com outro nome: nada acontece.
  - O hook nunca bloqueia a ferramenta (sai sem `permissionDecision`), código 0 sempre.
  - `subir(r)` sem argumento continua recusando projeto sem Vesta
    (`test_sem_vesta_nao_sobe`, `test_painel.py:532-533`); `subir(r, forcar=True)` sobe.
  - `hooks.json` ganha o grupo PreToolUse com matcher `Skill` e comando `hook-ativacao`.
- **Como fazer:** `subir(r, forcar=False)` pula a guarda de `painel.py:236-238` quando
  `forcar`. `hook_ativacao` em `vesta.py`, registrado em `HOOKS`, usa `achar` + `GET /aberto`
  da etapa 3 para decidir se abre.

## Etapa 6 — Tela da rodada

- **Tela:** sim. Implementa o mockup inteiro: pergunta pendente, faixa de fases, histórico e
  atividade, avisos de "sem registro", "formato desconhecido" e "nenhuma rodada", a palavra
  grande com a fase antes da execução, título e favicon com pergunta, cores `#ff4d00` e
  travada em branco. Durante a execução, Rodada abaixo das Etapas.
- **Arquivos:** mudar `skill/scripts/painel.html`, `skill/scripts/painel.py`,
  `skill/scripts/test_painel.py`.
- **O que prova a etapa:**
  - `dados()` sem execução e com rodada ativa devolve `momento`
    `{"tipo": "fase", "fase": "<Nome da fase atual>", "texto": "Fase N de 8"}`; com execução,
    o `momento` de hoje.
  - A página servida contém os ids do mockup (`pergunta`, `p-opcoes`, `p-livre`, `p-enviar`,
    `rodada`, `fases`, `hist`, `ativ`, `rodada-aviso`) e as cores novas no `:root`
    (`--verde:#ff4d00`, `--ciano:#ff4d00`, `--coral:oklch(0.93 0 0)`), sem `#5fd08a`,
    `#5cc8e0` nem `#f07a62`.
  - Enviar pela página: `POST /resposta/<id>` com `labels` marcados e `text` do campo; sem
    nada marcado e sem texto, não envia e mostra "Marque uma opção ou escreva uma resposta.".
  - Verificação da vesta-interface na página real servida (`painel.py servir`), com registro de
    exemplo e uma pergunta pendente: prints 375 e 1440, detector nas duas larguras, console sem
    erro, sem rolagem lateral; nenhum alarme novo em `#rodada` ou `#pergunta` além dos refutados
    no `relatorio.md` do mockup.
- **Como fazer:** copie do mockup
  (`docs/vesta/mockups/2026-09-28-rodada-no-painel/index.html`) o CSS da seção "rodada", o HTML
  de `#pergunta` e `#rodada`, e as funções `rodada`, `pergunta`, `status` e o envio; deixe fora
  a barra `.demo` e os dados de exemplo. `puxar()` continua em 3 s; o envio usa `fetch` com
  POST. Mova `#rodada` para depois do bloco Etapas quando houver execução (duas posições no
  DOM, ou `order` num contêiner flex). `momento()` em `painel.py:28-45` ganha o caso `fase`.

## Etapa 7 — Toda pergunta da Vesta por menu

- **Tela:** não.
- **Arquivos:** mudar `skill/SKILL.md`, `skill/spec.md`, `skill/grill.md`, `skill/mockup.md`,
  `skill/plano.md`, `skill/execucao.md`; criar `test/test_menu.py`.
- **O que prova a etapa:**
  - Cada um dos seis arquivos diz que perguntas ao usuário vão pelo `AskUserQuestion`, com a
    recomendada primeiro, marcada "(Recomendado)", e resposta livre aceita.
  - Os pontos de pergunta citam o menu: classificação e confirmação da sondagem
    (`spec.md`), perguntas de propósito, abordagens, cada seção do design e revisão da spec
    (`spec.md`), cada pergunta do grill e o fim do grill (`grill.md`), bifurcação, copy faltando
    e aprovação do mockup (`mockup.md`), parada 1 e commit/stash (`plano.md`), parada 2,
    ajuste e fechamento (`execucao.md`), e as paradas em `SKILL.md`.
  - Nenhum dos seis contém "Pare até o sim explícito", "espere o sim" ou "Peça ao usuário que
    revise" sem citar o menu na mesma frase.
  - `test/test_mockup.py:67-90` continua passando.
- **Como fazer:** os 22 pontos estão listados em
  `docs/vesta/research/2026-09-28-rodada-no-painel-research.md`, A11. A mensagem de cinco linhas
  das paradas continua; a decisão dela passa a ser um menu logo depois. A escolha entre as duas
  direções do mockup já é menu na vesta-interface (passo 3, item 4 do `SKILL.md` dela).

## Etapa 8 — O Knobler sai da frente com o painel aberto

- **Tela:** não.
- **Arquivos:** mudar `~/.claude/hooks/knobler-ask.sh` e
  `~/Code/claude-tooling/config/claude/hooks/knobler-ask.sh` (hoje iguais); criar
  `test/test_knobler.py`.
- **O que prova a etapa:**
  - Contrato: os dois arquivos contêm, antes do primeiro `curl`, a linha
    `python3 "$HOME/.claude/skills/vesta/scripts/vesta.py" aberto "$(printf '%s' "$INPUT" | jq -r '.cwd // ""')" && exit 0`,
    e continuam iguais entre si.
  - Rodando o `knobler-ask.sh` instalado com JSON de AskUserQuestion no stdin, `cwd` de um
    projeto com painel aberto (servidor real do teste) e `KNOBLER_PORT` apontando para uma porta
    falsa que registra pedidos: nenhum pedido chega ao Knobler e a saída é vazia.
  - Com o painel fechado: o pedido `POST /ask` chega ao Knobler falso como hoje.
- **Como fazer:** a linha entra logo depois de `INPUT="$(cat)"`. Commit no `claude-tooling`
  separado, com a mensagem citando este plano; o commit desta etapa aqui leva só o teste.
  Esta etapa mexe em outro repositório: a prova daqui só enxerga o teste de contrato.
