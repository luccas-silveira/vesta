# Painel da Vesta

## Resultado

Abrir qualquer projeto com a Vesta em uso e ver, sem fazer nada, em que ponto está a
execução e ler os documentos da feature. O painel atual (React/Vite, lê o tracker do
wayfinder) sai, junto com o wayfinder.

## O que o usuário disse

- A tela mostra a execução em destaque e, abaixo, a trilha da feature.
- Painel novo e mínimo, não adaptação do atual.
- Os mapas antigos do wayfinder em `claude-tooling/docs/wayfinder/` vão para `docs/` como
  registro histórico.
- O painel mora onde for melhor: fica no repositório da Vesta.

## O que foi suposto

- O hook de início de sessão sobe o painel só em projeto que tem `docs/vesta/` ou
  `.claude/vesta/`, e não planta pasta nenhuma em outros projetos.
- Busca, grafo, linha do tempo e atalhos de teclado ficam de fora.

## Arquitetura

Um script Python, só biblioteca padrão, em `skill/scripts/painel.py`, com um servidor HTTP
local e uma página HTML única embutida. Sem Node, sem dependência, sem build.

Duas rotas de dados, em JSON:

- `/estado` — a execução ativa (conteúdo de `.claude/vesta/estado.json`, ou nada) e a lista de
  features.
- `/doc?caminho=...` — o texto de um arquivo de `docs/vesta/`.

A página busca `/estado` a cada 3 segundos e renderiza o markdown no navegador.

## Dados

Feature é o par data + tópico tirado do nome dos arquivos em `docs/vesta/`:
`specs/<data>-<topico>-design.md`, `research/<data>-<topico>-research.md`,
`plans/<data>-<topico>.md`, `mockups/<data>-<topico>*`. Cada feature traz cinco passos: spec,
pesquisa, grill (feito quando a spec tem a seção `## Decisões do grill`), mockup e plano.
Passo sem arquivo aparece apagado.

A execução se liga à feature pelo campo `plano` do estado. Plano `chat` (caminho pequeno)
fica sem trilha.

Linha do momento, no topo: esperando aprovação do plano (`espera == "plano"`), pausada com
o motivo (`espera == "interrompida"`), travada (alguma etapa `travada`), concluída (todas
`feita`), ou rodando na etapa N.

Cada etapa mostra título, status, se a prova de teste tem vermelho e resultado, e o commit.

Sem execução, a página lista as features da mais recente para a mais antiga.

## Erros

- Estado ilegível ou fora do formato: aviso na página, o resto continua.
- `/doc` só serve arquivo dentro de `docs/vesta/`; caminho que resolve para fora é recusado
  com 404.
- O servidor escuta só em `127.0.0.1`.

## Hook

`painel.sh` passa a morar na Vesta e a ser registrado pelo plugin dela. Porta estável por
projeto, derivada do caminho, como hoje. Sobe `painel.py` em segundo plano quando há Vesta
no projeto e a porta não está ocupada pelo próprio painel; informa o endereço.

## Remoções

- `~/.claude/skills/wayfinder` e o espelho em `claude-tooling/config/claude/skills/wayfinder`.
- `claude-tooling/panel/`, o `~/.claude/hooks/painel.sh` e seu registro no `settings.json`.
- `~/Code/vesta/panel/` e `~/Code/vesta/docs/wayfinder/` (cópias plantadas pelo hook antigo).
- `claude-tooling/docs/wayfinder/` vira `claude-tooling/docs/historico/wayfinder/`.
- Referências ao wayfinder e ao painel no `CLAUDE.md` e `README.md` do claude-tooling.
- Cópias plantadas em outros projetos (`panel/` com `.versao`, `docs/wayfinder/` só com os
  dois arquivos padrão) são listadas e apagadas com confirmação.

## Testes

Funções puras em `painel.py` (agrupar features, montar o momento, validar caminho) com
testes em `skill/scripts/test_painel.py`, no mesmo estilo de `test_vesta.py`. A página é
verificada abrindo no navegador contra um estado de exemplo.
