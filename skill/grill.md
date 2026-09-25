# Fase 3 — Grill

Não anuncie a entrada nesta fase. Sua primeira mensagem aqui já é a primeira pergunta.

## O interrogatório

Interrogue o usuário implacavelmente sobre cada aspecto da spec até chegarem a
entendimento compartilhado. Percorra cada galho da árvore de decisão, resolvendo as
dependências entre decisões uma a uma. Para cada pergunta, forneça sua resposta
recomendada.

Faça as perguntas **uma de cada vez**, esperando resposta antes de continuar.

Se uma pergunta pode ser respondida explorando o codebase, explore o codebase em vez de
perguntar.

## A fila é o dossiê

Comece pela `## Fila do grill` do dossiê da fase 2, na ordem em que está — foi ordenada
por dependência.

Toda pergunta cita o achado que a motiva. Mas a pergunta é **do usuário**, então ela vem
na linguagem dele: o que ele ganha, o que ele perde, o que quebra. O identificador técnico
entra depois, como referência, nunca como o enunciado.

Errado:

> **A3** — `src/leads/export.ts:88` já faz paginação com cursor, a spec propõe offset.
> Por que não reusar?

Certo:

> **A3** — Do jeito que a spec está, a exportação pode repetir o mesmo lead se alguém
> mexer na lista enquanto ela roda. O projeto já tem um jeito de exportar que não tem esse
> problema (`src/leads/export.ts:88`). Uso o que já existe?
>
> Recomendo que sim.

Pergunta que o usuário só consegue responder lendo código é pergunta mal feita — ou você
explora o código e responde sozinho, ou reescreve até ele conseguir decidir.

Pergunta sem achado por trás vem depois da fila, e só para galho que a spec deixou
genuinamente em aberto.

Resposta do usuário abre galho novo? Insira na fila na posição certa e siga. Não deixe
pra depois.

## Glossário

Termo que o usuário usar em conflito com `CONTEXT.md` ou com o vocabulário do projeto:
interrompa na hora. "Seu glossário define 'cancelamento' como X, você parece querer dizer
Y — qual é?"

## Edite a spec inline

Cada decisão fechada vai pra spec **imediatamente**. Não acumule pra escrever no fim —
decisão não escrita é decisão que evapora e vira retrabalho no plano.

## Fim

Encerra quando: fila vazia **e** o usuário confirma que não há galho aberto.

Anexe na spec:

```markdown
## Decisões do grill

- **A3** — trocado offset por cursor. Motivo: `src/leads/export.ts:88` já resolve, e
  offset duplica registro sob escrita concorrente.
- **A7** — mantido como estava. Motivo: <por quê o achado não procede aqui>
```

Achado descartado também entra, com o motivo. Rastreabilidade vale nos dois sentidos.

Só então volte ao `SKILL.md` e siga pra fase 4.
