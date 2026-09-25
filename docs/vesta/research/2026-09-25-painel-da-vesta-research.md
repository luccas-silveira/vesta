# Pesquisa — painel da Vesta

Spec: `docs/vesta/specs/2026-09-25-painel-da-vesta-design.md`

## Achados

### A1 — O pre-commit do claude-tooling mora dentro de `panel/`
- Fonte: `claude-tooling/panel/hooks/pre-commit:1-19`, `git config core.hooksPath` = `panel/hooks`
- Contradiz a spec: sim
- Pergunta que levanta: apagar o painel desliga a única checagem antes de commit do
  claude-tooling. Ela ainda serve para algo, ou morre junto?

### A2 — Seis projetos têm mapas reais do wayfinder, não só os arquivos padrão
- Fonte: `~/Desktop/ZOI/Projetos_ZOI/{evolution,Gabriel Samra,GHL_DOOM,automaster_v2,evolution/graft}/docs/wayfinder`
- Contradiz a spec: parcial (a spec só apaga os que têm os dois arquivos padrão)
- Pergunta que levanta: esses mapas perdem o leitor. Ficam onde estão, sem painel, ou migram
  para `docs/historico/` como no claude-tooling?

### A3 — 12 projetos têm só as cópias plantadas
- Fonte: `claude-kit`, `vesta`, `Projetos_ZOI` e 9 subpastas dela (lista no relatório interno)
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; a limpeza lista e pede confirmação.

### A4 — O teste do plugin só aceita hooks que chamam `vesta.py`, e exatamente três
- Fonte: `~/Code/vesta/test/test_plugin.py:28-31,49-52`
- Contradiz a spec: sim (a spec registra um `painel.sh` pelo plugin)
- Pergunta que levanta: o painel sobe pelo hook de início de sessão que a Vesta já tem, em vez
  de um hook novo. Sem script bash, sem `jq`, sem `nc`.

### A5 — `vesta.py` já tem a leitura e a classificação do estado
- Fonte: `skill/scripts/vesta.py:34-122` (`raiz`, `ler`, `validar`, `encerrada`, `proxima`),
  `:442-471` (`hook_inicio` já distingue travada, interrompida, rodando)
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; `painel.py` importa de `vesta.py`.

### A6 — O painel atual abre a aba do navegador uma vez por dia
- Fonte: `~/.claude/hooks/painel.sh:83-86`
- Contradiz a spec: parcial (a spec só informa o endereço)
- Pergunta que levanta: você quer que o painel abra sozinho no navegador, ou basta o endereço?

### A7 — `ThreadingHTTPServer` é obrigatório com polling
- Fonte: https://docs.python.org/3/library/http.server.html
- Contradiz a spec: não
- Pergunta que levanta: nenhuma.

### A8 — Processo em segundo plano precisa soltar stdin/stdout, e o macOS não tem `setsid`
- Fonte: prática de shell; https://code.claude.com/docs/en/hooks (hook bloqueia até terminar)
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; em Python, `subprocess.Popen` com `start_new_session=True` e
  saídas em `DEVNULL`.

### A9 — Markdown no navegador: `marked` salvo junto, sem CDN
- Fonte: https://marked.js.org
- Contradiz a spec: não (a spec não fixou como renderizar)
- Pergunta que levanta: nenhuma; um arquivo de ~40 KB mantém "sem dependência instalada" e
  funciona offline.

### A10 — O painel atual tem design aprovado
- Fonte: `claude-tooling/panel/DESIGN.md` (escuro, Saira, verde de sinal)
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; o mockup herda os tokens.

### A11 — ADRs 0011, 0012 e 0013 do claude-tooling descrevem o que sai
- Fonte: `claude-tooling/docs/decisions/0011*`, `0012-painel-por-projeto.md`, `0013-o-grafico-e-a-fila.md`
- Contradiz a spec: parcial
- Pergunta que levanta: nenhuma; um ADR novo registra que os três foram superados.

### A12 — `backup/sync.sh` espelha `~/.claude/hooks` e `skills`
- Fonte: `claude-tooling/backup/sync.sh:20`
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; apagar nos dois lugares no mesmo commit.

### A13 — A Vesta não tem comando de teste escrito
- Fonte: `~/Code/vesta` sem pre-commit; testes em `test/` e `skill/scripts/test_vesta.py`
- Contradiz a spec: não
- Pergunta que levanta: nenhuma; o plano usa `python3 -m unittest discover -s test && python3 -m unittest discover -s skill/scripts`.

## Fila do grill

1. A2 — o que fazer com os mapas reais do wayfinder em seis projetos
2. A1 — o pre-commit do claude-tooling morre ou fica
3. A4 — o painel sobe pelo hook que a Vesta já tem
4. A6 — abrir o navegador sozinho ou só dar o endereço
