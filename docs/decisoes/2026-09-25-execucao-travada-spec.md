> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# spec-flow, fase 5 — execução travada por provas

Data: 2026-09-25. Origem: vídeo do AI Labs sobre o Helix, o fluxo que a Shopify usou para
reconstruir um app de 300 telas com agentes
(https://www.youtube.com/watch?v=bBMp5tLxShQ).

## Problema

O spec-flow termina no plano. Daí em diante a qualidade depende de instrução em prosa, e
prosa não segura regra — a tese do ADR-0014, a mesma do vídeo. Quatro sintomas, todos
confirmados pelo usuário:

1. O agente para antes do fim: declara pronto sem testar, abandona tarefa no meio.
2. O código passa no teste mas é ruim: duplicado, bagunçado, fora do padrão.
3. A interface sai diferente do que foi pedido.
4. O erro corrigido numa feature volta na próxima.

## Objetivo

Acrescentar ao spec-flow uma fase 5 de execução que percorre o plano sozinha e não consegue
parar enquanto houver trabalho sem prova. As fases 1 a 3 (spec, pesquisa, grill) não mudam.

Alvo: qualquer projeto — frontend, backend, integração. O fluxo se adapta ao que o projeto
tiver.

## Decisões tomadas no brainstorming

- Execução autônoma até o fim, como no Helix. O humano para duas vezes: aprovação do plano
  e revisão final.
- No frontend, a referência da prova visual é um protótipo HTML gerado no planejamento e
  aprovado junto com o plano.
- Aprendizados por projeto, não globais.
- Abordagem: fase própria dentro do spec-flow, independente do superpowers. Descartado
  montar o hook sobre o `subagent-driven-development`, que tem ciclo de revisão próprio e
  muda a cada versão do plugin.
- Onde dá, o hook confere o fato, não a palavra do agente.

## Decisões do grill

- **A4** — um commit ao fim de cada etapa; a impressão digital é o commit com a árvore
  limpa. Motivo: o hash da árvore com não rastreados se invalidava com o próprio estado e
  grava objetos no `.git` (A3); o Helix commita por etapa.
- **A5** — a fase 4 vira roteiro próprio (`plano.md`); o `writing-plans` sai do fluxo.
  Motivo: ele impõe cabeçalho, formato e handoff que brigam com etapas, e esse texto
  muda entre versões do superpowers (`writing-plans/SKILL.md:61,94-97,167-192`).
- **A6** — pedido pequeno pula pesquisa, grill e plano, mas passa pela fase 5 com uma
  etapa. Motivo: parar antes do fim acontece muito em tarefa pequena; o override do
  brainstorming citava texto que sumiu e deixava esse caminho sem trava.
- **A2, A1, A7** — retomada à mão, com aviso no começo de toda sessão do projeto quando
  houver execução interrompida; o mesmo comando cobre /clear e fork. Motivo: o hook de parada
  não dispara em Esc, erro de API ou limite de uso, e o corte de 8 bloqueios não o avisa.
  Descartada a retomada agendada: um agendamento por execução, e a primeira tentativa cai se
  o limite não tiver voltado.
- **A8** — 8 rodadas por prova antes de travar, escolha do usuário contra a recomendação de 3.
  O Helix não tem limite; algum limite é necessário pelo corte de 8 bloqueios e pelo custo de
  subagente. Consequência aceita: uma prova impossível pode consumir até 8 rodadas de correção
  antes de chegar ao usuário.
- **A9** — prova visual com um revisor, como no Helix: veredito de comparação inválida,
  escopo limitado à etapa, diferença com gravidade e lugar. Sai o revisor de
  comportamento, que duplicava a prova de teste.
- **A10** — correção que toca arquivo de tela derruba a prova visual, como no Helix. Sai a
  concessão da spec, que deixava o parecer visual valer depois de mudança na tela. O plano
  declara quais pastas contam como tela.
- **A15** — aceito que o revisor visual receba o CLAUDE.md e as regras injetadas em todo
  subagente. O pedido a ele não inclui as instruções do projeto e manda julgar só pelas
  capturas, pelo protótipo e pelo `DESIGN.md`. Sessão separada fica para quando houver erro
  causado pelo vazamento.
- **A12** — escritor de teste e implementador continuam separados. Custo aceito: pelo menos
  5 subagentes por etapa com tela, cerca de 55 mil tokens cada só para começar. Motivo:
  o agente que escreve o teste e o faz passar tende a testar o que o código já faz; o Helix
  separa pelo mesmo motivo.
- **A10, revisão** — um crítico e um corretor, como o AI Labs, e não dois críticos
  independentes, como o Helix. Motivo: custo por rodada com até 8 rodadas, e a prova de teste
  já pega a maior parte antes. Se a revisão final do usuário começar a achar o que o crítico
  deixou passar, entra o segundo crítico.
- **A11** — o crítico julga pelo que já existe, sem documento de arquitetura novo. O arquivo
  de aprendizados vira esse padrão com o tempo. Descartado a pesquisa montar um padrão
  mínimo: mais um documento por projeto para manter.
- **A13** — supacode e impeccable ficam desligados durante a execução, fora das duas
  paradas, por um invólucro no registro de cada um. Motivo: dezenas de avisos falsos de
  "terminou" e achados de design competindo com a prova visual.
- **A16** — scripts em Python, testes ao lado deles na pasta da skill, rodados pelo
  pre-commit deste repositório via cópia do backup. Motivo: ADR-0014 (barreira que não roda
  morre) e o bug aberto de tratamento de erro no hook em shell do ralph-loop.
- **A17** — "checkpoint" vira **etapa** e "gate" vira **prova**, escolha do usuário contra a
  recomendação de manter os nomes do Helix. Motivo: os dois colidiam com sentidos já em uso
  (a seção "Regras dos gates" do spec-flow, os "4 gates verdes" do Zoi Studio, o checkpoint
  de rewind do Claude Code). A seção antiga do `SKILL.md` passa a se chamar "Regras de fase".
- **A14, A19, A20** — subagentes só em primeiro plano e hook liberando com tarefa em segundo
  plano; bloqueio sem mensagem ao usuário; estado sempre na raiz do projeto.
- **A18** — o molde citado deixa de ser o pipeline-reuniao, cujo comando já não existe, e
  passa a ser o ralph-loop oficial.

## Fluxo

Fases 1 a 3: sem mudança, exceto que a pesquisa passa a ler o arquivo de aprendizados do
projeto, quando existir.

Pedido pequeno (o caminho "bounded" do brainstorming: mudança pequena em fluxo que já
existe) continua sem pesquisa, grill e plano escrito, mas entra na fase 5 com uma etapa
só: prova de teste, revisão e trava. O design aprovado no chat conta como parada 1. O override
do brainstorming no `SKILL.md` é reescrito para cobrir os dois caminhos, porque o texto que
ele cita hoje já não existe na versão 6.4.1 do superpowers.

Fase 4 (plano) deixa de usar o `superpowers:writing-plans` e vira roteiro próprio do
spec-flow, em `plano.md`, no mesmo molde de `research.md` e `grill.md`. O roteiro copia o que
o writing-plans faz bem: tarefas pequenas, caminhos de arquivo exatos, código completo no
plano, nenhum "a definir". E muda a forma:

- O plano é uma lista de etapas, do mais simples ao mais complexo. Cada uma se apoia na
  anterior.
- Cada etapa declara os testes que a provam e as provas que precisa passar: teste e
  revisão sempre, visual quando mexe em tela.
- Feature com interface: o protótipo HTML é gerado nesta fase, seguindo o `DESIGN.md` do
  projeto quando existir.
- O comando de teste do projeto, descoberto na pesquisa, é gravado no estado. Projeto sem
  testes ganha uma etapa zero que monta o mínimo para rodar testes.
- A lista de etapas é gravada no arquivo de estado.

Parada 1: o usuário aprova plano e protótipo na mesma revisão.

Fase 5 (execução): o agente percorre as etapas sem voltar ao usuário. Em cada
etapa, as provas rodam na ordem teste, visual (se houver), revisão.

Parada 2: todas as etapas passaram, ou uma travou. O usuário testa a feature. Cada
ajuste pedido vira etapa nova, passa pelas mesmas provas, e a lição vai para o arquivo
de aprendizados. O ciclo termina quando o usuário aprova.

## As provas

### Teste

1. Um subagente escreve os testes da etapa antes do código.
2. Os testes precisam falhar. Teste que nasce verde não prova nada e é refeito.
3. Outro subagente implementa.
4. Um script do spec-flow, não o agente, roda o comando de teste e grava o resultado junto
   com a impressão digital do código: o commit atual, e só se a árvore de trabalho estiver
   limpa. Com código não commitado, o script recusa rodar.
5. A prova só conta como passada se o resultado for verde e o commit gravado for o commit
   atual, sem nada alterado depois. Qualquer mudança posterior invalida a prova sozinha.

Cada etapa termina num commit. O commit é o ponto de volta da etapa e a base da
impressão digital. Estado, pareceres e protótipo ficam fora do git, para gravá-los não
sujar a árvore.

### Visual

Só em etapa que mexe em tela.

1. Um subagente revisor novo recebe as capturas do app e do protótipo no mesmo estado de
   tela. Comportamento não é com ele: é da prova de teste.
2. Ele julga só contra o protótipo e o `DESIGN.md`, e só o que a etapa construiu. Na
   etapa do esqueleto, não cobra a seção que ainda não existe.
3. Lista toda diferença, cada uma com gravidade e lugar na tela. Diferença corrigível em
   código reprova por padrão.
4. Se as duas capturas não estiverem no mesmo estado, o veredito é "comparação inválida", e
   as telas são capturadas de novo. Comparação inválida não conta como rodada de correção.
5. O parecer, com o veredito, fica gravado. A prova passa quando o revisor aprova.

O modelo é o Claude. O Helix usa Gemini pela noção espacial; o AI Labs trocou por Claude, e
aqui fica igual até haver motivo medido para mudar.

### Revisão adversária

1. Um subagente crítico parte do princípio de que há bug e procura. O padrão dele: as
   instruções do projeto, o arquivo de aprendizados, as regras de código mínimo em uso e o
   padrão que o código do projeto já segue. Nenhum documento de arquitetura é criado para
   isso.
2. Se achar problema, um subagente corretor conserta e o crítico revê.
3. A prova passa quando o crítico aprova.
4. A correção muda o código, o que derruba a prova de teste, que roda de novo.
5. Se a correção mudar algo visível, a prova visual também cai e roda de novo. O script
   compara os arquivos mudados com as pastas que o plano declara como tela (componentes,
   estilos, templates). Correção só de lógica mantém o parecer visual.

## Estado e trava

Estado em `.claude/spec-flow/estado.json`, sempre na raiz do projeto, nunca no diretório
atual do agente, e fora do git. Guarda: caminho do plano,
comando de teste, sessão que começou a execução, fase de espera (nenhuma, plano, revisão
final), contador de bloqueios sem mudança e a lista de etapas. Cada etapa tem id,
título, se mexe em tela, status (pendente, feita, travada), tentativas por prova e o resultado
de cada prova: para o teste, verde ou vermelho e a impressão digital; para visual e revisão, o
caminho do parecer.

O hook de parada decide, nesta ordem:

1. Sem arquivo de estado: libera. É o caso de toda sessão fora da fase 5.
2. Tarefa em segundo plano ainda rodando: libera. O orquestrador só usa subagentes em
   primeiro plano; a regra evita o laço com tarefa zumbi marcada como "rodando".
3. Sessão diferente da que começou a execução: libera.
4. Estado esperando o usuário (parada 1 ou 2): libera.
5. Todas as etapas feitas, ou alguma travada: libera.
6. Caso contrário: bloqueia, com a mensagem dizendo qual prova de qual etapa é a
   próxima.

O motivo do bloqueio vai só para o agente. O usuário não vê mensagem nenhuma entre as duas
paradas.

O molde é o hook de parada do ralph-loop oficial: sessão lida da entrada do hook, saída JSON
com `decision: block`, gravação atômica do estado e comando de cancelamento. O critério de
parada é outro: o ralph confia numa frase do agente; aqui o hook confere o estado.

### Válvula de escape

- Por etapa: a mesma prova falhando em 8 rodadas seguidas marca a etapa como
  travada. As rodadas acontecem dentro do turno, sem o agente tentar parar entre uma e
  outra, para não esbarrar no corte de 8 bloqueios do Claude Code. Como as etapas se apoiam umas nas outras, a execução não pula para a próxima:
  vai direto à parada 2 com o diagnóstico das tentativas.
- Por sessão: 5 bloqueios seguidos sem mudança no estado fazem o hook liberar e gravar o
  motivo. Cobre o agente que continua respondendo mas não consegue agir, como um comando de
  teste quebrado. O Claude Code já corta sozinho em 8 bloqueios seguidos, sem avisar o hook;
  os 5 vêm antes disso para que o motivo fique gravado.
- Manual: um comando encerra a execução e mantém o estado para retomar.

### Convivência com outros hooks de parada

Todos os hooks de parada rodam juntos a cada tentativa de parar. Dois atrapalham a execução
autônoma e ficam desligados enquanto houver execução ativa no projeto, a não ser nas duas
paradas previstas:

- a notificação do supacode, que avisaria "terminou" a cada bloqueio;
- a análise de design do impeccable, que devolve ao agente achados que competem com a prova
  visual.

Os scripts deles não são editados, porque são de terceiros e se atualizam. O registro de
cada um no settings passa por um invólucro que confere o arquivo de estado e pula a chamada.

### Retomada

O hook de parada não roda no Esc, em erro de API, em limite de uso ou em credencial
inválida, nem quando o Claude Code força o fim depois de 8 bloqueios. A sessão para e o
estado continua dizendo "executando".

- Retomar é à mão, com um comando que passa a execução para a sessão atual e segue da
  etapa onde parou.
- Toda sessão que começa no projeto confere o estado. Se houver execução interrompida, o
  primeiro aviso da sessão diz onde ela parou e qual comando retoma.
- O mesmo comando resolve o /clear e o fork, que trocam o identificador da sessão e
  deixariam a trava desligada.
- A sessão gravada no estado vem sempre da entrada de um hook, nunca de variável de
  ambiente. Estado com sessão vazia ou desconhecida libera a parada e cai no aviso de
  execução interrompida, em vez de virar lixo que nunca trava nem é limpo.

## Aprendizados

Arquivo `.claude/spec-flow/aprendizados.md`, no projeto, no git.

- Só entra o que vier da revisão final do usuário. Conclusão do próprio agente não entra.
- Cada entrada: data, o que aconteceu, por quê.
- Subagente não lê arquivo por conta própria: o orquestrador cola os aprendizados no pedido
  de cada subagente.
- A fase de pesquisa também os lê.

## Arquivos

Em `~/.claude/skills/spec-flow/`:

- `SKILL.md`: fase 4 apontando para o roteiro próprio, fase 5.
- `plano.md` (novo): roteiro da fase 4, plano em etapas.
- `execucao.md` (novo): roteiro da fase 5 e as instruções de cada subagente (escritor de
  teste, implementador, revisor visual, crítico, corretor).
- Script de prova de teste (novo): roda o comando, calcula a impressão digital, grava no
  estado.
- Script do hook de parada (novo), registrado em `~/.claude/settings.json`.
- Script do aviso de início de sessão (novo), registrado no mesmo arquivo.
- Comandos de retomar e encerrar a execução.
- Invólucro para os hooks do supacode (`~/.claude/settings.json`) e do impeccable
  (`~/.claude/settings.local.json`).

Neste repositório: `docs/reference/vesta.md` atualizado, o ADR-0016 e o
`panel/hooks/pre-commit` estendido.

## Como provar que funciona

- Os scripts são em Python, só biblioteca padrão. Ganham testes automáticos com estados
  montados à mão, cada um com a decisão esperada do hook (libera, bloqueia, trava, desiste)
  e da prova (verde válido, verde com commit velho, árvore suja, vermelho).
- Scripts e testes moram juntos em `~/.claude/skills/spec-flow/`. O backup os copia para
  `config/claude/skills/spec-flow/` neste repositório, e o pre-commit daqui passa a rodar
  esses testes quando o commit toca essa pasta.
- O fluxo só conta como pronto depois de rodar numa feature pequena de um projeto real do
  usuário, com pelo menos uma prova falhando e se recuperando.

## Entrega em partes

Cada parte é utilizável sozinha:

1. Trava com a prova de teste.
2. Revisão adversária.
3. Prova visual e protótipo.
4. Aprendizados.

A trava vem primeiro porque sem ela as outras provas voltam a ser conselho.

## Fora do escopo

- Visualizador web do plano. O plano em markdown já é legível; só compensaria em plano muito
  grande.
- Rodar a fase 5 sem as fases 1 a 4.
- Aprendizados globais.
