# Plano — repositório próprio da Vesta

Objetivo: a Vesta passa a morar neste repositório, que a explica para quem nunca a viu, e
`~/.claude` só aponta para cá.

Spec: `docs/exemplo/spec.md` (cópia de `~/Code/claude-tooling/docs/vesta/specs/2026-09-25-repositorio-vesta-design.md`).
Pesquisa: `docs/exemplo/pesquisa.md`.

Comando de teste, da raiz:

```
python3 -m unittest discover -v -s skill/scripts && python3 -m unittest discover -v -s test
```

Pastas de tela: nenhuma. Mockup: nenhum: sem tela. O mockup de demonstração da etapa 5 é
conteúdo da documentação, não tela do produto.

Estado de partida: o commit inicial traz `skill/` e `commands/` copiados sem mudança de
`~/.claude/skills/vesta` e `~/.claude/commands/vesta-*.md`. Nesse ponto o teste de registro
(`skill/scripts/test_vesta.py:443-467`) quebra, porque procura um `settings.json` três pastas
acima; a etapa 1 resolve.

A execução roda numa sessão aberta em `~/Code/vesta`: a trava de parada usa a pasta da sessão.

---

## Etapa 1 — Plugin e hooks dentro do repositório

**Tela:** não.

**Arquivos:**
- criar `skill/.claude-plugin/plugin.json`
- criar `skill/hooks/hooks.json`
- criar `test/test_plugin.py`
- mudar `skill/scripts/test_vesta.py` (sai a classe `Registro`, linhas 443-467, com a constante
  `RAIZ_CLAUDE` e a regex `GUARDA`)

**O que prova a etapa:**
- `skill/.claude-plugin/plugin.json` é JSON válido, com `name` igual a `vesta`.
- `skill/hooks/hooks.json` é JSON válido e registra exatamente três hooks da Vesta: um
  `PostToolUse` com `matcher` `Bash` que chama `vesta.py" hook-adocao`, um `SessionStart` que
  chama `vesta.py" hook-inicio` e um `Stop` que chama `vesta.py" hook-parada`.
- Todo comando do `hooks.json` termina em `|| true` (script sumido nunca vira bloqueio de parada).
- Todo comando do `hooks.json` chama o script por `${CLAUDE_PLUGIN_ROOT}/scripts/vesta.py`, e esse
  arquivo existe em `skill/scripts/vesta.py`.
- `test_vesta.py` não lê mais nenhum `settings.json`: a suíte de `skill/scripts` passa rodando da
  raiz do repositório, sem `~/.claude` por perto.
- Implementação errada que o teste reprova: um `hooks.json` com o hook de parada sem `|| true`,
  ou com um quarto hook `silenciar` (a guarda do supacode não é da Vesta).

**Como fazer:**
- `plugin.json`: `{"name": "vesta", "description": "<a descrição do skill/SKILL.md:3>", "version": "1.0.0"}`.
  A pasta `skill/` vira plugin carregado da pasta de skills do Claude Code: qualquer pasta em
  `~/.claude/skills/` com `.claude-plugin/plugin.json` carrega como plugin, no lugar, sem cópia
  (https://code.claude.com/docs/en/plugins/create). O `SKILL.md` da raiz continua sendo a skill
  `vesta`.
- `hooks.json`, no formato de hooks de plugin:
  ```json
  {"hooks": {
    "PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "timeout": 10,
      "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/vesta.py\" hook-adocao || true"}]}],
    "SessionStart": [{"hooks": [{"type": "command", "timeout": 10,
      "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/vesta.py\" hook-inicio || true"}]}],
    "Stop": [{"hooks": [{"type": "command", "timeout": 10,
      "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/vesta.py\" hook-parada || true"}]}]
  }}
  ```
  São os mesmos três registros de hoje em `~/.claude/settings.json` (adoção na linha 127,
  início na 277, parada na 315), com o caminho trocado por `${CLAUDE_PLUGIN_ROOT}`, que o Claude
  Code preenche com o caminho do link.
- `test/test_plugin.py`: `unittest`, só biblioteca padrão. Acha a raiz como
  `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`. Absorve o que a classe
  `Registro` de `test_vesta.py:448-461` verificava, agora sobre `skill/hooks/hooks.json`. O teste
  `test_notificacao_do_supacode_com_guarda` (`test_vesta.py:463-467`) não é portado: a guarda fica
  no settings.json do usuário e passa a ser checada pelo `install.sh` (etapa 2).

---

## Etapa 2 — Instalador

**Tela:** não.

**Arquivos:**
- criar `install.sh` (executável)
- criar `test/test_install.py`

**O que prova a etapa:** todos os testes rodam com `CLAUDE_HOME` apontando para uma pasta
temporária que imita `~/.claude`, e o `.claude.json` imitado fica em `$CLAUDE_HOME/../.claude.json`.
- Primeira instalação numa pasta vazia: `skills/vesta` vira link para `<repo>/skill`,
  `commands/vesta-retomar.md` e `commands/vesta-pausar.md` viram links para os arquivos de
  `<repo>/commands/`; sai com código 0. As pastas `skills` e `commands` são criadas se faltarem.
- Segunda execução seguida: nada muda, nenhum arquivo `*.antes-da-vesta-*` aparece, código 0.
- `skills/vesta` já existe como pasta de verdade: ela é renomeada para
  `skills/vesta.antes-da-vesta-<AAAAMMDDhhmmss>` com o conteúdo intacto, o link é criado, e a saída
  diz o nome da cópia guardada. O mesmo para um comando que já existe como arquivo comum.
- `skills/vesta` é link para outro lugar: passa a apontar para `<repo>/skill`, sem cópia guardada.
- Falta `skills/grill-me/SKILL.md`: a saída tem uma linha de aviso citando `grill-me`; o mesmo
  para `hallmark`. Com as duas presentes, nenhum aviso sobre elas.
- `.claude.json` sem servidor MCP `inspo` em `mcpServers`: aviso citando `inspo`. Com ele, sem aviso.
  Sem `.claude.json`, aviso também, sem erro.
- `settings.json` com algum hook cujo comando contém `vesta.py" hook-`: aviso de que os hooks da
  Vesta rodariam duas vezes, mandando remover do settings.json. O instalador não edita o arquivo:
  o conteúdo continua byte a byte igual.
- `settings.json` com hook `Stop` cujo comando contém `supacode-managed-hook` e nenhum `Stop` com
  `vesta.py" silenciar`: aviso sobre a guarda do supacode. Com a guarda, sem esse aviso. Sem
  supacode, sem esse aviso. Sem `settings.json`, sem erro.
- Todo aviso começa com `aviso:`. Avisos nunca mudam o código de saída, que é 0.
- Implementação errada que o teste reprova: um instalador que apaga a pasta antiga em vez de
  guardar, ou que "conserta" o settings.json sozinho.

**Como fazer:**
- `bash`, `set -eu`. `CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"`,
  `REPO="$(cd "$(dirname "$0")" && pwd -P)"`.
- Uma função `ligar <destino> <alvo>`: link que já aponta para o alvo, não faz nada; link para
  outro lugar, `ln -sfn`; arquivo ou pasta de verdade, `mv` para
  `<destino>.antes-da-vesta-$(date +%Y%m%d%H%M%S)`, imprime o nome, e cria o link.
- As checagens de JSON num `python3 - <<'PY'` embutido, só biblioteca padrão, lendo
  `$CLAUDE_HOME/settings.json` e `$CLAUDE_HOME/../.claude.json`, imprimindo linhas `aviso: ...`.
  JSON ilegível vira aviso, não erro.
- O teste roda o script com `subprocess.run(['bash', INSTALL], env={**os.environ, 'CLAUDE_HOME': tmp})`
  e confere com `os.path.islink` e `os.path.realpath`.
- No fim, o instalador imprime uma linha dizendo que os hooks vêm do plugin e só carregam em
  sessão nova.

---

## Etapa 3 — README e verificação da documentação

**Tela:** não.

**Arquivos:**
- criar `README.md`
- criar `test/test_docs.py`

**O que prova a etapa:**
- `README.md` tem, nesta ordem, os títulos `## O que a Vesta resolve`, `## Como o fluxo anda`,
  `## Exemplo de ponta a ponta`, `## Instalação` e `## Uso`.
- `## Como o fluxo anda` tem um bloco ` ```mermaid ` e cita as cinco fases pelo nome (Spec,
  Pesquisa, Grill, Mockup e plano, Execução) e os três caminhos (sondagem, pequeno, estrutural).
- Todo caminho citado no README e em `docs/*.md` (só o primeiro nível de `docs/`, sem
  `docs/decisoes/` nem `docs/exemplo/`) existe: alvo de link markdown relativo, resolvido a partir
  do arquivo, e texto em crase que tenha `/` ou termine em `.md`, `.py`, `.sh` ou `.json`, resolvido
  a partir da raiz do repositório. Ficam de fora os que começam com `~`, `/`, `http`, `$` ou `.claude/`
  (pasta criada em cada projeto do usuário), os que têm `<` ou `*`, e os que casam
  `docs/vesta/`, que são caminhos dentro do projeto do usuário.
- Nenhum desses arquivos contém `/Users/`: a explicação usa `~`.
- Implementação errada que o teste reprova: README que cita `docs/como-funciona.md` antes de o
  arquivo existir. Essa citação só entra na etapa 4.

**Como fazer:**
- Leitor: quem usa Claude Code mas nunca viu a Vesta. Fala em skill e hook sem definir.
- `## O que a Vesta resolve`: sem ela, o agente pula para o código, interroga sem ter pesquisado,
  declara pronto sem teste, para no meio da execução, e a tela só aparece depois de construída.
  Cada fase ligada ao problema que resolve.
- `## Como o fluxo anda`: diagrama mermaid dos três caminhos e das cinco fases com as paradas de
  aprovação (mockup, parada 1, parada 2). Uma seção curta por fase: entrada, saída, onde para.
  Fontes, lidas em `skill/`: `SKILL.md`, `spec.md`, `research.md`, `grill.md`, `mockup.md`,
  `plano.md`, `execucao.md`. Descreva o que esses arquivos mandam hoje, não o que os documentos
  antigos dizem.
- `## Exemplo de ponta a ponta`: a criação deste repositório. Trechos curtos de
  `docs/exemplo/spec.md` (objetivo), `docs/exemplo/pesquisa.md` (um achado que mudou a spec: o A1,
  hooks dentro do repositório), da seção "Decisões do grill" da spec, e do `docs/exemplo/plano.md`
  (a lista de etapas). Os commits das etapas entram como `git log --oneline` colado ao fim da
  execução; nesta etapa, escreva a lista de etapas do plano e uma frase dizendo que cada uma tem
  um commit `test(etapa N)` e um `feat(etapa N)`. Um parágrafo sobre o caminho com tela, que este
  exemplo não tem: o mockup em HTML aprovado antes do plano, e a recusa do script em começar sem ele.
- `## Instalação`: clonar em `~/Code/vesta`, rodar `./install.sh`, o que ele liga e o que ele só
  avisa; abrir sessão nova.
- `## Uso`: `/vesta` ou um pedido de feature; `/vesta-retomar`; `/vesta-pausar`.
- `test/test_docs.py`: `re` para links `\[[^\]]*\]\(([^)#\s]+)` e crases `` `([^`\s]+)` ``, fora de
  blocos de código cercados por três crases.

---

## Etapa 4 — Como funciona por dentro, dependências e limites

**Tela:** não.

**Arquivos:**
- criar `docs/como-funciona.md`, `docs/dependencias.md`, `docs/limites.md`
- mudar `README.md` (um parágrafo no fim de `## Como o fluxo anda` ligando os três)
- mudar `test/test_docs.py`

**O que prova a etapa:**
- Os três arquivos existem, e o README tem link para cada um.
- `como-funciona.md` cita os números como o código conta: 8 provas vermelhas no total da etapa
  (`LIMITE_TENTATIVAS`, `skill/scripts/vesta.py:17`) e 5 paradas bloqueadas sem progresso
  (`LIMITE_BLOQUEIOS`, `vesta.py:18`). O teste lê as duas constantes do `vesta.py` e confere que
  os dois números aparecem no texto. Implementação errada que ele reprova: o texto dizer "6
  paradas" ou "8 seguidas" depois de alguém mudar a constante.
- `como-funciona.md` cita cada subcomando do `vesta.py`. O teste tira a lista das chaves do
  dicionário `COMANDOS` (`vesta.py:467-470`: `criar`, `iniciar`, `mostrar`, `prova`, `concluir`,
  `retomar`, `pausar`, `adicionar`, `fechar`, `guarda`) mais `silenciar` (`vesta.py:477`), e
  confere que cada um aparece em crase no texto. Implementação errada que ele reprova: um
  subcomando novo no script sem explicação.
- `dependencias.md` cita `grill-me`, `hallmark`, `inspo`, `superpowers` e `supacode`.
- As regras de caminho da etapa 3 valem para os três arquivos novos.

**Como fazer:**
- `como-funciona.md`, lido de `skill/scripts/vesta.py` e `skill/execucao.md`: o estado em
  `.claude/vesta/estado.json` de cada projeto, que nunca suja a árvore (`vesta.py:13-16`); o
  ciclo de etapa (escritor de teste, commit, `prova vermelho`, implementador, commit,
  `prova teste`, `concluir`) e o que cada prova recusa (`vesta.py`, `cmd_prova`); a trava de
  parada e os três hooks de `skill/hooks/hooks.json`; a sessão dona, marcada pelo hook de adoção
  quando um comando Bash roda `vesta.py iniciar|retomar|adicionar` (`vesta.py:357-372`); os
  limites; a trava do mockup (`exigir_mockup`, `vesta.py:146-153`).
- `dependencias.md`: grill-me (fase 3), hallmark e inspo (fase 4 e etapas de tela), o conflito com
  o superpowers e a regra do `~/.claude/CLAUDE.md` que proíbe o `brainstorming`, o `writing-plans`
  e o `executing-plans` dentro do fluxo; a guarda opcional do supacode (`vesta.py silenciar`
  embutido no hook Stop do supacode, mantido à mão no settings.json, checado pelo `install.sh`);
  Python só com biblioteca padrão; git obrigatório (cada etapa é um commit).
- `limites.md`: uma etapa visível marcada como sem tela escapa da trava do mockup; o script sabe
  que o mockup está commitado, não que foi aprovado; a fase 1 nunca foi observada disparando
  sozinha a partir de um pedido cru; `/skills` pode não listar a Vesta por ser link (issue
  https://github.com/anthropics/claude-code/issues/14836), embora ela funcione; app desktop e
  extensão de IDE não testados; o Claude Code às vezes regrava o settings.json com cópia antiga
  (https://github.com/anthropics/claude-code/issues/93742), o que apagaria a guarda do supacode.

---

## Etapa 5 — História e mockup de demonstração

**Tela:** não.

**Arquivos:**
- criar `docs/decisoes/0016-execucao-travada-por-provas.md`, `docs/decisoes/0017-vesta.md`,
  `docs/decisoes/0018-mockup-e-frontend-na-vesta.md`,
  `docs/decisoes/2026-09-25-execucao-travada-spec.md`,
  `docs/decisoes/2026-09-25-execucao-travada-pesquisa.md`,
  `docs/decisoes/2026-09-25-execucao-travada-plano.md`, `docs/decisoes/README.md`
- criar `docs/exemplo/mockup/index.html`
- mudar `README.md` (link para `docs/decisoes/README.md` e para o mockup de demonstração)
- mudar `test/test_docs.py`

**O que prova a etapa:**
- Todo `.md` de `docs/decisoes/`, fora o `README.md`, tem como primeira linha exatamente
  `> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).`
- O resto de cada um é idêntico byte a byte ao original em `~/Code/claude-tooling`. O teste
  compara com o original quando `~/Code/claude-tooling` existe, e pula a comparação quando não.
  Origens: `docs/decisions/0016-execucao-travada-por-provas.md`, `docs/decisions/0017-vesta.md`,
  `docs/decisions/0018-mockup-e-frontend-na-vesta.md`,
  `docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md`,
  `docs/vesta/research/2026-09-25-spec-flow-execucao-research.md`,
  `docs/vesta/plans/2026-09-25-spec-flow-execucao-parte-1.md`.
- `docs/decisoes/README.md` lista os seis arquivos com link, em ordem de data, uma linha cada.
- `docs/exemplo/mockup/index.html` existe, contém a palavra `demonstração` visível no corpo, e não
  referencia arquivo externo fora de `fonts.googleapis.com` e `fonts.gstatic.com`.
- O README tem link para `docs/decisoes/README.md` e para `docs/exemplo/mockup/index.html`.
- Implementação errada que o teste reprova: reescrever o texto antigo para atualizar nomes.

**Como fazer:**
- Copiar os seis originais com o aviso na frente e uma linha em branco; não editar mais nada.
- O mockup é a tela de um recurso pequeno inventado, dito como tal no topo da página ("Mockup de
  demonstração: mostra o formato que a fase 4 produz"). Seguir `skill/mockup.md`: ler
  `~/.claude/skills/hallmark/SKILL.md` e seguir o fluxo de design dela; HTML autocontido, CSS e
  JS dentro, fontes do Google Fonts, sem rolagem lateral em tela de celular.
- As mudanças no `~/Code/claude-tooling` não são desta etapa: ficam para a etapa 6.

---

## Etapa 6 — A troca real

**Tela:** não.

**Arquivos:**
- criar `test/test_instalacao_real.py`
- mudar, fora deste repositório: `~/.claude/skills/vesta`, `~/.claude/commands/vesta-*.md`,
  `~/.claude/settings.json`, e no `~/Code/claude-tooling`: `docs/README.md`,
  `docs/reference/vesta.md`, `panel/hooks/pre-commit`, os seis arquivos da etapa 5 (saem),
  `docs/vesta/specs/2026-09-25-repositorio-vesta-design.md` e
  `docs/vesta/research/2026-09-25-repositorio-vesta-research.md` (saem; moram em `docs/exemplo/`)

**O que prova a etapa:** `test_instalacao_real.py` confere a máquina onde roda e pula tudo quando
`~/.claude/skills/vesta` não existe (máquina sem a Vesta).
- `~/.claude/skills/vesta` é link e `os.path.realpath` dele é a pasta `skill/` deste repositório.
- Os dois comandos em `~/.claude/commands/` são links para `commands/` deste repositório.
- Nenhum hook do `~/.claude/settings.json` tem comando contendo `vesta.py" hook-`: com o plugin,
  eles rodariam duas vezes.
- Não sobra `~/.claude/skills/vesta.antes-da-vesta-*` nem `~/.claude/commands/vesta-*.antes-da-vesta-*`.
- Implementação errada que o teste reprova: trocar a pasta por link e esquecer os registros do
  settings.json.

**Como fazer, nesta ordem:**
1. Conferir que nenhum projeto tem execução ativa além desta: procurar `.claude/vesta/estado.json`
   em `~/Code`, `~/Desktop` (profundidade 5) e ler `espera`; as interrompidas do claude-kit e do
   Financeiro_ZOI ficam como estão.
2. `./install.sh`. Ele guarda a pasta e os comandos antigos como `*.antes-da-vesta-*` e cria os links.
3. `diff -r` entre a cópia guardada e `skill/`, ignorando `__pycache__`, `.claude-plugin/` e
   `hooks/`: tem que sair vazio fora desses.
4. Rodar os três hooks pelo link com entrada de exemplo
   (`echo '{"session_id":"x","cwd":"'"$HOME"'/Code/claude-kit"}' | python3 ~/.claude/skills/vesta/scripts/vesta.py hook-inicio`,
   e o mesmo para `hook-parada` e `hook-adocao` com `tool_name`/`tool_input`): terminam com código
   0; o `hook-inicio` no claude-kit e no Financeiro_ZOI ainda avisa da execução interrompida.
5. `claude plugin list` mostra `vesta@skills-dir` carregado.
6. Remover do `~/.claude/settings.json` os três registros com `vesta.py" hook-` (linhas 127, 277 e
   315 hoje), com `python3` lendo e gravando o arquivo numa operação só, `json.dump(..., indent=2,
   ensure_ascii=False)`; manter a guarda `vesta.py" silenciar` do supacode (linha 297). Reler e
   conferir que a guarda está lá e os três saíram. Este passo desliga a trava da sessão que está
   executando, porque os hooks do plugin só carregam em sessão nova; por isso é o último que mexe
   em `~/.claude`.
7. Apagar as cópias `*.antes-da-vesta-*`.
8. No `~/Code/claude-tooling`: `git rm` dos seis arquivos da etapa 5 e dos dois de
   `docs/exemplo/`; em `docs/README.md` as linhas dos ADRs 0016, 0017 e 0018 viram uma linha só
   apontando para `~/Code/vesta/docs/decisoes/`; `docs/reference/vesta.md` vira um ponteiro de
   poucas linhas para `~/Code/vesta/README.md`; em `panel/hooks/pre-commit` sai o bloco das
   linhas 22-34 que roda os testes da Vesta; `bash backup/sync.sh`. O implementador lista esses
   arquivos à parte; o orquestrador commita no claude-tooling e confere que `npm test --prefix panel`
   passa.
9. Uma linha em `~/.claude/projects/-Users-luccassilveira-Code-claude-tooling/memory/MEMORY.md`
   com a mudança e a pendência do claude-kit (incluir `~/Code/vesta` em `fontes.json` quando a
   execução dele for retomada).

---

Depois da parada 2, com o sim do usuário: `gh repo create luccas-silveira/vesta --private --source . --push`,
e colar o `git log --oneline` final na seção de exemplo do README.
