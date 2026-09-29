# Rodada no painel

## Resultado

Acompanhar uma rodada inteira da Vesta só pelo painel, da ativação da skill à parada 2, sem
voltar ao terminal nem para ler nem para responder. Hoje o painel só enxerga a Vesta quando
existe arquivo em `docs/vesta/` ou execução em `.claude/vesta/estado.json`; tudo antes disso
(classificação, perguntas, respostas, pesquisa) é invisível.

## O que o usuário disse

- O painel mostra a fase atual ao vivo, desde a ativação da skill.
- O painel mostra o histórico: cada pergunta, a resposta dada, a decisão.
- O painel mostra o que a Vesta está fazendo dentro da fase.
- As perguntas podem ser respondidas pelo painel.
- Painel aberto decide: aberto, as perguntas vão para ele; fechado, ficam no terminal.
- Toda pergunta da Vesta, inclusive revisão e paradas, passa a ser menu (AskUserQuestion),
  sempre com resposta livre possível.
- Abordagem: um hook intercepta o menu antes de ele aparecer (abordagem 1).
- A rodada que atravessa sessões é costurada numa só.
- O menu vai para o painel em qualquer AskUserQuestion do projeto, não só nos da Vesta.
- Na ativação da skill, o painel sobe e abre sozinho no navegador se não estiver aberto.

## O que foi suposto

- Um usuário, na mesma máquina, com o painel ao lado do terminal.
- "Painel aberto" é: a página pediu `/estado` nos últimos 10 segundos.
- Sem dependência nova, sem build: segue o `painel.py`/`painel.html` existentes.

## Arquitetura

Três peças, todas em `skill/`:

1. **Leitor da rodada** (`painel.py`): extrai do registro da sessão (`~/.claude/projects/<pasta>/*.jsonl`)
   fase, histórico e atividade, e entrega em `/estado` sob a chave `rodada`.
2. **Ponte de perguntas** (`painel.py`, rotas novas): o servidor do painel guarda a fila de
   perguntas pendentes e as respostas.
3. **Hook de menu** (`vesta.py hook-menu`, PreToolUse com matcher `AskUserQuestion`): decide
   entre painel e terminal e espera a resposta.

Mais um hook na ativação da skill (PreToolUse, matcher `Skill`, quando a skill é `vesta`)
que sobe o painel e o abre no navegador.

## Leitor da rodada

Rodada começa na última invocação da skill `vesta` (tool_use `Skill` com `skill: "vesta"`)
e vai até o fim do registro.

Fase atual, pela ordem dos marcos no registro:

- `ativacao` — a invocação da skill.
- `spec`, `pesquisa`, `grill`, `mockup`, `plano`, `execucao` — um tool_use que lê
  `~/.claude/skills/vesta/{spec,research,grill,mockup,plano,execucao}.md` (Read, ou Bash com o
  caminho no comando).
- `execucao` também quando `vesta.py criar` ou `iniciar` aparece.
- `concluida` — o estado da execução encerrado (regra de hoje, `encerrada`).

Fase sem marco, com marco de fase posterior já no registro, é pulada (o caminho pequeno pula
pesquisa, grill e plano), não pendente.

Histórico, em ordem: cada AskUserQuestion com pergunta, opções e resposta (do tool_result,
incluindo texto livre e múltiplas escolhas), e cada mensagem de texto do assistente. Pergunta
sem resposta ainda aparece como pendente.

Atividade: os tool_use da rodada, do mais recente para o mais antigo, cada um com nome e alvo
resumido (arquivo para Read/Edit/Write, comando para Bash, padrão para Grep, url para
buscas). Limite de 200 itens.

### Costura entre sessões

Uma rodada pertence a uma feature quando o registro cita o caminho da spec dela
(`docs/vesta/specs/<data>-<topico>-design.md`). O painel junta, em ordem de tempo, os
registros de qualquer pasta em `~/.claude/projects/` modificados desde a data da spec e que
citem esse caminho, mais a sessão atual. Antes de a spec existir, a rodada é só a sessão
atual. Registros do SDK (`entrypoint: sdk`) continuam fora.

## Ponte de perguntas

Rotas novas no servidor do painel:

- `POST /pergunta` — o hook entrega `{id, perguntas}` (o `input` do AskUserQuestion);
  responde se há página aberta.
- `GET /pergunta/<id>` — o hook consulta: `pendente`, `respondida` com as respostas, ou
  `abandonada` (página sem pedir `/estado` há mais de 15 segundos).
- `POST /resposta/<id>` — a página envia as respostas.

`/estado` passa a trazer `perguntas` pendentes, em ordem de chegada. A página mostra uma de
cada vez, com as opções, multiseleção quando a pergunta pede e campo de resposta livre. Com
pergunta pendente, o título da aba vira "pergunta · <projeto>" e o favicon pisca.

Fila só em memória: servidor reiniciado perde as pendentes, e o hook, sem resposta do
servidor, devolve o menu ao terminal.

## Hook de menu

1. Sem servidor do painel do projeto, ou sem página aberta: sai sem nada; o menu aparece no
   terminal.
2. Com página aberta: `POST /pergunta`, depois consulta a cada segundo.
3. `respondida`: devolve a resposta à sessão pelo caminho que a pesquisa confirmar
   (preencher `answers` via `updatedInput`, ou negar com a resposta no motivo).
4. `abandonada`, erro de rede ou exceção: sai sem nada; o menu aparece no terminal.

Sem prazo para responder enquanto a página estiver aberta, até o limite de tempo que o hook
aceita (a pesquisa confirma o máximo).

## Mudanças na Vesta

Toda pergunta ao usuário passa a ser AskUserQuestion: classificação, perguntas da spec,
revisão da spec, perguntas do grill, aprovação do mockup, paradas 1 e 2. `SKILL.md`,
`spec.md`, `grill.md`, `mockup.md`, `plano.md` e `execucao.md` dizem isso.

`hooks.json` ganha o hook de menu e o de ativação. `/vesta-painel` continua igual.

`subir` passa a aceitar projeto sem `docs/vesta/` quando chamado pela ativação.

## Tela

Bloco novo "Rodada" no painel: faixa com as fases (a atual acesa, as puladas marcadas), e
abaixo histórico e atividade lado a lado; a pergunta pendente aparece em destaque acima da
faixa. Passa pelo mockup da vesta-interface antes de ser construída.

## Erros

- Linha ilegível no registro: ignorada. Sem registro: o bloco mostra "sem registro"; o resto
  do painel continua.
- Hook de menu nunca trava a sessão por falha própria: toda falha cai no terminal.
- Duas perguntas ao mesmo tempo (subagentes): fila, uma de cada vez.

## Testes

Biblioteca padrão, no padrão de `test_painel.py`/`test_vesta.py`:

- fases lidas de um registro de exemplo, incluindo fase pulada;
- histórico com pergunta, resposta simples, múltipla e livre, e pergunta pendente;
- atividade com alvo resumido e limite;
- costura de duas sessões em pastas diferentes pela spec;
- hook de menu: página fechada, página respondendo, página fechada no meio da espera,
  servidor fora do ar;
- instruções da Vesta sem pedido de resposta em texto livre.

## Execução

O código mora em `~/Code/vesta`. A execução roda numa sessão aberta lá, porque a trava de
parada segue a pasta da sessão.
