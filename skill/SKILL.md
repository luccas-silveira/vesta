---
name: vesta
description: Fluxo padrão para qualquer trabalho criativo — feature nova, componente, funcionalidade, mudança de comportamento. Encadeia spec → pesquisa (codebase + web) → grill com dossiê → mockup aprovado quando há tela → plano em etapas → execução travada por provas. Use ANTES de escrever qualquer código. Dispara em "/vesta", "vamos construir X", "quero criar X", "adiciona X", ou qualquer pedido de feature nova.
---

# Vesta

Ideia crua vira feature pronta passando por cinco fases. Nenhuma pula.

Anuncie uma vez, no começo: "Usando a Vesta: spec, pesquisa, grill, mockup, plano, execução."

Depois disso, nunca mais fale de fase. Não anuncie entrada, saída, conclusão nem próximo
passo — o usuário vê as ferramentas rodando e não precisa de legenda. Entre uma fase e
outra você não escreve nada; volta a escrever quando tiver pergunta para ele ou resultado
na mão.

A fase 1 substitui o `superpowers:brainstorming`: não invoque aquela skill, nem o
`writing-plans` nem o `executing-plans` do superpowers, dentro deste fluxo.

## Fases

| # | Fase | O que roda | Artefato |
|---|---|---|---|
| 1 | Spec | `spec.md` (nesta pasta) | `docs/vesta/specs/YYYY-MM-DD-<topico>-design.md` |
| 2 | Pesquisa | `research.md` (nesta pasta) | `docs/vesta/research/YYYY-MM-DD-<topico>-research.md` |
| 3 | Grill | `grill.md` (nesta pasta) | spec revisada in-place + seção `## Decisões do grill` |
| 4 | Mockup e plano | `mockup.md` se houver tela, depois `plano.md` | mockup em `docs/vesta/mockups/`, plano em `docs/vesta/plans/YYYY-MM-DD-<feature>.md` + estado criado |
| 5 | Execução | `execucao.md` (nesta pasta) | um commit por etapa, todas provadas |

Crie um todo por fase, na ordem, antes de começar.

## Regras de fase

- Não avance de fase sem o artefato da fase anterior existir em disco. Confira.
- Fases 2 e 3 só pulam se o usuário pedir explicitamente ("pula a pesquisa", "vai direto
  pro plano"), ou no caminho pequeno da fase 1. Registre o pulo numa linha no fim da spec, quando houver
  spec.
- Spec decomposta em sub-projetos: cada sub-projeto roda o ciclo inteiro sozinho.
  Não pesquise/grille os quatro de uma vez.
- Todas as fases: leia o `.md` correspondente nesta pasta na hora de entrar na fase, não antes.
- Frontend na Vesta usa o inspo (referências reais) e a hallmark (design).
- Tudo que tem tela passa por mockup aprovado antes da execução, inclusive no caminho pequeno.
  A única exceção é não ter nada visível. O script recusa iniciar plano com tela sem mockup
  commitado.

## Fase 1 — Spec

Leia `spec.md` nesta pasta e siga. Ele classifica o pedido: sondagem termina numa
recomendação, pedido pequeno vai direto à fase 5 com uma etapa, estrutural segue para a fase 2
com a spec aprovada.

## Fase 2 — Pesquisa

Leia `research.md` nesta pasta e siga.

Entrada: a spec da fase 1. Saída: dossiê de achados + fila de pontos quentes.

## Fase 3 — Grill

Leia `grill.md` nesta pasta e siga.

Entrada: spec + dossiê. Saída: spec corrigida, cada decisão rastreada ao achado que a
motivou.

## Fase 4 — Mockup e plano

A spec cria ou muda algo visível: leia `mockup.md` nesta pasta e siga. Termina quando o
usuário aprova o mockup.

Depois, ou direto quando não há tela, leia `plano.md` e siga, sobre a spec **revisada**, não a
original. Termina na parada 1: o usuário aprova o plano.

## Fase 5 — Execução

Depois da aprovação, leia `execucao.md` nesta pasta e siga. Um hook não deixa você parar
enquanto houver etapa sem prova. Termina na parada 2: o usuário testa a feature.

## Retomada

Execução interrompida (Esc, limite de uso, erro de API, /clear): o aviso aparece no começo da
próxima sessão do projeto. `/vesta-retomar` passa a execução para a sessão atual;
`/vesta-pausar` para de propósito, mantendo o estado.

## As mensagens das paradas

Cinco linhas cada. Parada 1: o que o plano vai fazer, o que trava, o que decidir agora.
Parada 2: o que ficou pronto, o que travou, como testar.

Não repita o que está nos arquivos. Cite só o caminho que o usuário abre em seguida.

Não liste estado que não mudou: working tree sujo de antes, commits que já existiam,
pendência de handoff anterior. Se algo disso for bloqueante, é uma linha na parte do
"o que trava"; se não for, fica fora.

Correção de achado errado descoberta no caminho entra, sempre — em uma frase, dizendo o
que muda para o usuário, não o número do achado.
