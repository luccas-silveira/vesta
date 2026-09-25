> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# Pesquisa — spec-flow, fase 5

Spec: `docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md`

Fontes externas principais: o artigo original, https://shopify.engineering/helix (Talha
Naqvi, 21/09/2026), e a doc de hooks, https://code.claude.com/docs/en/hooks. A spec foi
escrita a partir do vídeo do AI Labs; onde o artigo difere, o achado diz.

## Achados

### A1 — O Claude Code já encerra o turno depois de 8 bloqueios seguidos do hook de parada, e o hook não fica sabendo
- Fonte: https://code.claude.com/docs/en/env-vars (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`),
  https://code.claude.com/docs/en/hooks-guide#stop-hook-hits-the-block-cap,
  https://github.com/anthropics/claude-code/issues/77686
- Contradiz a spec: parcial
- Pergunta que levanta: a desistência depois de 5 bloqueios sem progresso continua valendo,
  porque vem antes do limite de 8. Mas o estado pode ficar dizendo "executando" com a sessão
  parada. Isso pede o mesmo caminho de retomada do A2.

### A2 — O hook de parada não dispara no Esc nem em erro de API, limite de uso ou credencial
- Fonte: https://code.claude.com/docs/en/hooks#stop (nesses erros dispara o `StopFailure`,
  que não consegue bloquear)
- Contradiz a spec: sim. A válvula de 5 bloqueios diz cobrir limite de uso e credencial, e
  nesses casos o hook nem roda.
- Pergunta que levanta: se o seu limite de uso acabar no meio da noite, a sessão para e fica
  parada. Basta retomar à mão com um comando, ou você quer algo que retome sozinho quando o
  limite voltar?

### A3 — Do jeito que a spec descreve, a impressão digital se invalida sozinha
- Fonte: pesquisa externa, item 33, e interna, item 48. Estado, pareceres, protótipo e
  aprendizados ficam dentro do projeto; gravar qualquer um deles muda o hash. Além disso, o
  cálculo com índice temporário grava objetos no `.git` real, e um arquivo grande não
  ignorado já deixou 79,7 GiB de lixo num caso relatado
  (https://github.com/powerfooI/roamgate/issues/262).
- Contradiz a spec: sim
- Pergunta que levanta: ver A4, que resolve os dois.

### A4 — O Helix faz um commit ao fim de cada checkpoint, com as evidências arquivadas
- Fonte: https://shopify.engineering/helix
- Contradiz a spec: sim, a spec não commita por checkpoint.
- Pergunta que levanta: commitar a cada checkpoint dá um ponto de volta por pedaço, e a
  impressão digital vira "o commit atual, sem nada alterado", que é simples e não suja o
  repositório. O custo é o histórico com um commit por checkpoint. Aceita?

### A5 — Na fase 4, o writing-plans impõe um formato que briga com os checkpoints
- Fonte: `~/.claude/plugins/cache/claude-plugins-official/superpowers/6.4.1/skills/writing-plans/SKILL.md:61`
  (cabeçalho do plano manda usar subagent-driven-development), `:94-97` (formato "Task N"),
  `:167-192` (handoff de execução, que mudou entre as versões 6.3.0 e 6.4.1)
- Contradiz a spec: sim. A spec previa só um override da pergunta final.
- Pergunta que levanta: o plano pode continuar sendo escrito pelo writing-plans, com overrides
  no cabeçalho, no formato e no fim, e quebrar a cada versão do superpowers. Ou a fase 4 pode
  virar um roteiro próprio do spec-flow. O segundo caminho é coerente com a escolha de não
  depender do superpowers na execução.

### A6 — O override atual do brainstorming cita um texto que já não existe
- Fonte: `~/.claude/skills/spec-flow/SKILL.md:30-34` contra
  `.../superpowers/6.4.1/skills/brainstorming/SKILL.md:184-188`. A 6.4.1 também tem um
  caminho "bounded" que vai direto para a implementação, sem plano (`:186-187`).
- Contradiz a spec: parcial. É defeito do spec-flow atual que a spec herdaria.
- Pergunta que levanta: corrigir junto. Pedido pequeno de trabalho classificado como
  "bounded" pula o plano e, com ele, a fase 5: aceitável, ou a fase 5 deve valer para todo
  pedido?

### A7 — Depois de um /clear, a sessão muda de identificador, e a trava se desligaria
- Fonte: https://code.claude.com/docs/en/hooks#sessionstart (`source`: clear, compact,
  fork). Há um estado velho de março no projeto Gabriel Samra, com sessão `unknown`, que
  nunca trava e nunca é limpo (`.../Gabriel Samra/.claude/pipeline-reuniao.state:3`). Bug do
  ralph-loop: gravar a sessão por variável de ambiente, que vinha vazia, travou todas as
  sessões do projeto (https://github.com/anthropics/claude-code/issues/39530).
- Contradiz a spec: sim
- Pergunta que levanta: o comando de retomada do A2 passa a ser também o jeito de retomar
  depois de um /clear, regravando a sessão atual no estado. Estado com sessão vazia ou
  desconhecida libera e avisa uma vez, em vez de ficar parado para sempre.

### A8 — O Helix não tem limite de tentativas
- Fonte: https://shopify.engineering/helix — "It can retry as many times as it needs to,
  but it can't override a failed check."
- Contradiz a spec: parcial. As 3 rodadas por gate e os 5 bloqueios são invenção da spec.
- Pergunta que levanta: com o Claude Code cortando em 8 e o custo por rodada (A14), algum
  limite é necessário. Três rodadas por gate antes de travar e chamar você está bom, ou você
  prefere mais insistência?

### A9 — O gate visual do Helix usa um revisor só, e comportamento é gate de teste, não visual
- Fonte: https://shopify.engineering/helix. Um revisor (Gemini) lista toda diferença, com
  severidade e localização; pode declarar a comparação INVALID se as duas telas não
  estiverem no mesmo estado, e aí recaptura; olha só o que o checkpoint construiu.
- Contradiz a spec: sim. A spec tem dois revisores visuais, um de aparência e outro de
  comportamento.
- Pergunta que levanta: tirar o revisor de comportamento, que duplica o gate de teste e custa
  um subagente a mais por checkpoint, e adotar INVALID e escopo por checkpoint?

### A10 — A revisão do Helix usa dois críticos independentes e refaz o gate visual quando algo visível muda
- Fonte: https://shopify.engineering/helix
- Contradiz a spec: sim. A spec tem um crítico e um corretor, e aceita não refazer o visual.
- Pergunta que levanta: a concessão da spec contradiz o original. Refazer o visual só quando
  a correção tocar arquivo de tela custa pouco e fecha o buraco. Vale?

### A11 — Sem um padrão escrito, a revisão adversária não tem contra o que exigir
- Fonte: https://shopify.engineering/helix — a revisão julga contra uma arquitetura
  documentada "easy for agents to implement". Seus projetos têm CLAUDE.md e alguns têm
  DESIGN.md (`~/Desktop/Projetos/AgentStudio/zoi-studio-frontend/DESIGN.md`,
  `~/Desktop/Projetos/knobler/DESIGN.md`), mas nenhum documento de arquitetura foi
  encontrado.
- Contradiz a spec: parcial
- Pergunta que levanta: em projeto sem padrão escrito, o crítico julga só pelo bom senso e
  pelas regras de código mínimo. Aceitável, ou a pesquisa da fase 2 deve montar um padrão
  mínimo quando não houver?

### A12 — Cada subagente custa cerca de 55,5 mil tokens só para começar
- Fonte: `docs/wayfinder/tickets/011-subagente-como-redutor.md:34-35`
- Contradiz a spec: parcial. A spec prevê até 6 subagentes por checkpoint.
- Pergunta que levanta: um plano de 8 checkpoints com tela chega perto de 50 subagentes antes
  de qualquer rodada de correção. Juntar escritor de teste e implementador num só, como o
  superpowers faz, corta um por checkpoint, mas o mesmo agente que escreve o teste o faz
  passar. Separar vale o custo?

### A13 — Vários hooks de parada já rodam em paralelo, e cada bloqueio dispara todos
- Fonte: `~/.claude/settings.json:264-291` (pipeline-reuniao, notificação do supacode,
  graft), `~/.claude/settings.local.json:73-84` (análise de design do impeccable, até 30 s),
  `.../security-guidance/2.0.8/hooks/hooks.json:97-108` (pode reacordar o agente com outro
  assunto)
- Contradiz a spec: parcial
- Pergunta que levanta: numa execução autônoma, cada bloqueio gera uma notificação do supacode
  e, em frontend, uma análise do impeccable que compete com o gate visual. Silenciar esses
  dois enquanto a fase 5 roda, ou conviver?

### A14 — O Stop dispara com subagente em segundo plano ainda rodando
- Fonte: https://code.claude.com/docs/en/hooks#stop-input (`background_tasks`); laços
  infinitos por tarefa zumbi em https://github.com/anthropics/claude-code/issues/58637
- Contradiz a spec: parcial
- Pergunta que levanta: decisão técnica. Recomendação: o hook libera quando houver tarefa em
  segundo plano, e o orquestrador roda subagentes em primeiro plano.

### A15 — "Não lê as instruções do projeto" não se garante só pelo pedido
- Fonte: `~/.claude/plugins/cache/ponytail/ponytail/4.8.4/hooks/claude-codex-hooks.json:17-28`
  injeta regras em todo subagente; o CLAUDE.md também chega.
- Contradiz a spec: parcial
- Pergunta que levanta: o revisor visual vai receber parte das instruções de qualquer jeito.
  Aceitar e só não mandar as instruções no pedido, ou rodá-lo numa sessão separada do Claude,
  como o AI Labs fez?

### A16 — Hoje nenhum script de hook tem teste, e scripts em ~/.claude ficam fora do pre-commit
- Fonte: `panel/hooks/pre-commit:8,13`; `panel/server/raiz.test.js:4,15-20` é o molde
  (diretório temporário mais execução do script). ADR-0014: a barreira que não roda é
  barreira morta.
- Contradiz a spec: parcial. A spec pede testes, mas não diz onde eles vivem nem o que os roda.
- Pergunta que levanta: os scripts vivem em `~/.claude/skills/spec-flow/` e os testes neste
  repositório, rodando no pre-commit que já existe? Aí mudar o script sem rodar o teste só é
  pego no próximo commit aqui.

### A17 — "Gate" e "checkpoint" já têm outros sentidos no seu setup
- Fonte: `~/.claude/skills/spec-flow/SKILL.md:43-50` ("Regras dos gates" = artefato de fase);
  `~/.claude/memory/tools/zoi-studio-frontend.md:20-21` ("4 gates verdes" = tsc, lint, test,
  build); `~/.claude/settings.json:429` (checkpoint é o rewind do Claude Code)
- Contradiz a spec: parcial
- Pergunta que levanta: manter os nomes do Helix, que você já conhece do vídeo, e renomear a
  seção antiga do spec-flow? Ou trocar os novos por "etapa" e "prova"?

### A18 — O precedente citado na spec está órfão
- Fonte: o hook do pipeline-reuniao manda rodar `/processar-reuniao`, que não existe mais
  em `~/.claude/commands`; o ticket `docs/wayfinder/tickets/003-quais-plugins-saem.md:31-33`
  cogita removê-lo.
- Contradiz a spec: parcial. Só a citação; o mecanismo continua valendo como molde.
- Pergunta que levanta: nenhuma para você; a spec troca a citação pelo ralph-loop oficial.

### A19 — A legenda que os hooks-precedentes mostram viola o silêncio
- Fonte: `~/.claude/plugins/local/pipeline-reuniao/hooks/stop-hook.sh:95` (`systemMessage`);
  `docs/decisions/0003-silencio-override-de-skill.md:28-35`
- Contradiz a spec: parcial
- Pergunta que levanta: decisão técnica. Recomendação: o hook fala só com o agente, nunca com
  você.

### A20 — O estado precisa de raiz fixa
- Fonte: `pipeline stop-hook.sh:10-11` usa o diretório atual; um `cd` numa subpasta faz o
  hook perder o estado e liberar. O graft usa `CLAUDE_PROJECT_DIR`
  (`~/.claude/helpers/graft-hooks.cjs:6`).
- Contradiz a spec: parcial
- Pergunta que levanta: decisão técnica. Recomendação: raiz do projeto, não diretório atual.

### Registro — confirmam a spec

- O Helix aceita desenho e documento de produto como referência visual para feature nova, e
  mudança só de lógica pula o gate visual (artigo). Confirma o protótipo HTML.
- O próprio superpowers aceita método de execução informado de antemão
  (`writing-plans/SKILL.md:170-172`).
- Molde de hook pronto: sessão lida da entrada do hook, saída JSON com `decision:block`,
  gravação atômica e comando de cancelamento (ralph-loop oficial e pipeline-reuniao).
  `stop_hook_active` não serve de guarda aqui: o security-guidance o liga a sessão inteira
  (`security_reminder_hook.py:1911-1923`).
- O subagente não dispara Stop, só SubagentStop; registrar o hook só em Stop não atinge os
  subagentes (doc de hooks).
- Prompts reaproveitáveis do superpowers: implementador, revisor ("Do Not Trust the Report"),
  re-revisão e TDD ("teste que já passa testa o que já existe").
- O critique do impeccable já usa dois subagentes isolados e cegos um ao outro, e o
  visual-companion do brainstorming já gera mockup HTML.
- O Shop amarrou a aprovação do plano a um hash do conteúdo: mudar o plano invalida a
  aprovação (https://shopify.engineering/shop-app-migration). Aplicável à parada 1.
- Os números que circulam sobre o Helix (12 semanas, 6 engenheiros) são da migração do app
  Shop, em outro artigo que não cita o Helix.
- Documentação desatualizada, fora do escopo: `docs/reference/estado-atual.md:33-42` não
  lista nenhum hook de parada; `~/.claude/skills/spec-flow/research.md:18` procura em
  `docs/adr/`, e este repositório usa `docs/decisions/`.

## Fila do grill

Ordenada por dependência — decisão que trava outras vem primeiro.

1. A4 — Commit por checkpoint (trava A3, A10)
2. A5 — Fase 4 própria ou writing-plans com overrides (trava A6, A17)
3. A6 — Pedido "bounded" pula a fase 5?
4. A2 — Retomada depois de limite de uso: à mão ou sozinha (trava A1, A7)
5. A7 — Retomada depois de /clear e estado sem sessão
6. A8 — Limite de tentativas
7. A9 — Um revisor visual, INVALID, escopo por checkpoint (trava A10, A15)
8. A10 — Refazer o visual quando a correção toca tela
9. A15 — Revisor visual em sessão separada?
10. A12 — Separar escritor de teste e implementador
11. A11 — Projeto sem padrão escrito
12. A13 — Silenciar supacode e impeccable durante a fase 5
13. A16 — Onde vivem os testes dos scripts
14. A17 — Nomes
15. A14, A19, A20 — decisões técnicas com recomendação, confirmadas em bloco
