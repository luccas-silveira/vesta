# Pesquisa — repositório próprio da Vesta

Spec: `docs/vesta/specs/2026-09-25-repositorio-vesta-design.md`

## Achados

### A1 — Existe um jeito oficial de a pasta da skill carregar os próprios hooks, sem editar o settings.json
- Fonte: https://code.claude.com/docs/en/plugins/create ("loads any folder there that contains a `.claude-plugin/plugin.json` as a plugin"), https://code.claude.com/docs/en/plugins/loading ("loads in place and is never copied"). Testado no Claude Code 2.1.282: `~/.claude/skills/zzplug` como link, hook em `hooks/hooks.json`, `claude plugin list` mostrou `zzplug@skills-dir ✔ loaded` e o hook disparou com `CLAUDE_PLUGIN_ROOT` igual ao caminho do link.
- Contradiz a spec: sim. A spec descartou plugin porque o script é chamado por `~/.claude/skills/vesta`; nesse formato o caminho continua o mesmo. Os hooks passariam a morar no repositório, e o `install.sh` só criaria links.
- Pergunta que levanta: os hooks da Vesta passam a viver dentro do repositório, versionados com ela, em vez de um script mexer no seu settings.json?

### A2 — O Claude Code às vezes regrava o settings.json com uma cópia antiga e apaga hooks
- Fonte: https://github.com/anthropics/claude-code/issues/93742 (aberta, 2.1.269: "salvar como padrão" no `/model` desfez 5 hooks), #49849, #46921.
- Contradiz a spec: parcial. A spec põe os hooks da Vesta no settings.json; qualquer regravação dessas apaga a trava sem aviso.
- Pergunta que levanta: reforça o A1.

### A3 — São 3 hooks próprios, não 4; o quarto é uma guarda embutida no hook do supacode
- Fonte: `~/.claude/settings.json:127` (adoção), `:277` (início), `:315` (parada) e `:297` (guarda `silenciar` como prefixo do comando `supacode-managed-hook`). `test_vesta.py:454-467` testa essa divisão.
- Contradiz a spec: parcial. A guarda não é um registro da Vesta: é um pedaço do comando de outra ferramenta. Nem um plugin nem um `install.sh` "registra" isso sem reescrever o hook do supacode.
- Pergunta que levanta: a guarda que silencia a notificação do supacode durante a execução continua sendo mantida à mão no settings.json, fora do repositório?

### A4 — O exemplo proposto, o espelho, parou antes do fim e cita clientes e caminhos da máquina
- Fonte: `~/Code/claude-kit/.claude/vesta/estado.json` (`espera: interrompida`, etapa 7 só com `aa0d38a test(etapa 7)`); todas as etapas com `tentativas: 0`. Spec do espelho `docs/vesta/specs/2026-09-25-espelho-claude-design.md:46` lista nomes de clientes; pesquisa `:20,38,53` e plano do kit `:86-95,201` citam caminhos de `~/Desktop/ZOI`, `~/.config/*` e `/Users/luccassilveira`.
- Contradiz a spec: sim. O exemplo não mostra a feature terminada nem uma prova vermelha seguida de conserto, e os artefatos ficam em dois repositórios.
- Pergunta que levanta: o exemplo é um caso real incompleto e editado para tirar dados, ou um caso pequeno feito do começo ao fim só para o README?

### A5 — Numa máquina nova, o backup e o espelho do claude-kit não trazem o repositório da Vesta
- Fonte: `backup/sync.sh:10,23` copia o link como link; `backup/restore.sh` não clona repositórios, então o link volta quebrado. `claude-kit/espelho.py:85-112` copia o conteúdo do link como pasta real, porque `~/Code/vesta` não está em `claude-kit/fontes.json:20-26`; com ele lá, vira link com `__HOME__` e o repositório é clonado (`espelho.py:190-196,241-273`).
- Contradiz a spec: parcial. A spec não cita o claude-kit.
- Pergunta que levanta: o claude-kit passa a clonar o repositório da Vesta numa máquina nova, e o backup do claude-tooling aceita ficar com o link?

### A6 — Duas execuções da Vesta estão interrompidas, e nenhuma está ativa
- Fonte: `~/Code/claude-kit/.claude/vesta/estado.json` e `~/Desktop/ZOI/Projetos_ZOI/Financeiro_ZOI/.claude/vesta/estado.json`, ambas `espera: interrompida`. Com `espera` preenchido, `ativa()` é falso (`vesta.py:118-119`) e a parada não bloqueia. O estado mora no projeto (`vesta.py:13,34-38`), não na pasta da skill.
- Contradiz a spec: parcial. A spec exige "nenhuma em andamento"; interrompida não é em andamento, e o estado não depende do caminho do script.
- Pergunta que levanta: a troca pode acontecer com essas duas paradas, sabendo que elas retomam normalmente depois?

### A7 — A documentação que existe hoje descreve uma Vesta que já mudou
- Fonte: `docs/reference/vesta.md:24-29` (override do brainstorming, que não existe mais), `:42-52` ("três arquivos", uma corrida só). `docs/decisions/0016:40` cita `/spec-flow-retomar`. `0018:30-31` diz que o impeccable segue instalado (removido no 0019). A spec da execução travada (`docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md`) descreve prova visual, revisão adversária e aprendizados que não foram construídos (`vesta.py:14-16` só guarda vestígios). O plano `2026-09-25-spec-flow-execucao-parte-1.md` tem 1560 linhas com nomes antigos.
- Contradiz a spec: parcial. A spec coloca esses arquivos em `docs/decisoes/` sem dizer que estão desatualizados; um leitor novo os tomaria como descrição do presente.
- Pergunta que levanta: a explicação é escrita do zero a partir dos arquivos vivos, com os documentos antigos marcados como história?

### A8 — O teste de registro quebra rodando do repositório e até com `cd` no link
- Fonte: `test_vesta.py:444` sobe três pastas de forma textual; `os.getcwd()` devolve o caminho físico (conferido com o link `grill-me`), então `cd ~/.claude/skills/vesta/scripts && python3 -m unittest` também quebra.
- Contradiz a spec: não. A spec já prevê ler `~/.claude/settings.json`. Com o A1, o teste passaria a ler `hooks/hooks.json` do próprio repositório, o que também deixa o pre-commit do repositório testar o que está commitado.

### A9 — O pre-commit do claude-tooling seguiria o link e testaria os arquivos vivos
- Fonte: `panel/hooks/pre-commit:22-32`; `checkout-index` recria o link e o `discover` testa `~/Code/vesta/skill/scripts`.
- Contradiz a spec: não. A spec já tira os testes da Vesta desse pre-commit.

### A10 — Commands e skills por link carregam; a lista `/skills` pode não mostrar
- Fonte: https://code.claude.com/docs/en/skills ("can be a symlink to a directory elsewhere on disk… loads the skill once"). Command por link testado no 2.1.282 (a #80754 foi fechada por inatividade). https://github.com/anthropics/claude-code/issues/14836 (aberta): `/skills` mostra "No skills found" para diretório por link, embora a skill funcione. Problemas no app desktop e na extensão de IDE: #72631, #93987.
- Contradiz a spec: não.

### A11 — O caminho que o Claude Code informa para a skill é o do link
- Fonte: registros de sessão com "Base directory for this skill: /Users/luccassilveira/.claude/skills/grill-me" (link para `~/.agents/skills/grill-me`); `${CLAUDE_SKILL_DIR}` igual no teste.
- Contradiz a spec: não. As instruções que chamam `~/.claude/skills/vesta/scripts/vesta.py` seguem valendo.

### A12 — Plugin dá prefixo aos commands
- Fonte: https://code.claude.com/docs/en/plugins/create. Commands dentro do plugin viram `/vesta:vesta-pausar`. `${CLAUDE_PLUGIN_ROOT}` não é substituído dentro do `SKILL.md` da raiz; `${CLAUDE_SKILL_DIR}` é.
- Contradiz a spec: não, se os commands continuarem como links em `~/.claude/commands/`.

### A13 — Os limites que a spec cita estão ditos de um jeito impreciso
- Fonte: `vesta.py:17,244-247` (8 provas vermelhas no total da etapa, não seguidas; zera só no `retomar`); `vesta.py:18,315,326-330` (5 paradas bloqueadas sem progresso; a sexta é liberada e a execução vira interrompida).
- Contradiz a spec: parcial, só no texto que vai para `como-funciona.md`.

## Fila do grill

Ordenada por dependência.

1. A1 — hooks dentro do repositório (plugin na pasta de skills) ou no settings.json (trava A2, A3, A8 e o escopo do `install.sh`)
2. A3 — a guarda do supacode fica mantida à mão
3. A4 — que exemplo de ponta a ponta
4. A7 — explicação escrita do zero, documentos antigos como história
5. A5 — o claude-kit clona o repositório numa máquina nova
6. A6 — troca com as duas execuções interrompidas
7. A13 — texto dos limites (resolve sem pergunta: o `como-funciona.md` usa os números do código)
