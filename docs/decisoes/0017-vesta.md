> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# ADR-0017 — O spec-flow vira Vesta e deixa de depender do superpowers

Data: 2026-09-25. Status: em vigor. Continua o ADR-0016.

## Contexto

Depois da fase 5, o fluxo ficou com três nomes na cabeça de quem usa: `spec-flow` na skill,
superpowers na fase 1 (o `brainstorming`) e Helix na origem da execução travada. A fase 1
era a última dependência do plugin: o texto dele muda entre versões, e o override que o
`spec-flow` mantinha já tinha ficado defasado uma vez (achado A6 da pesquisa de 2026-09-25).

## A decisão

O fluxo inteiro se chama Vesta: skill `vesta`, comandos `/vesta-retomar` e `/vesta-pausar`,
script `scripts/vesta.py`, estado em `.claude/vesta/` de cada projeto, documentos em
`docs/vesta/`.

A fase 1 virou roteiro próprio, `spec.md`, adaptado do `brainstorming` do superpowers (MIT,
Jesse Vincent), com crédito no arquivo. O companheiro visual ficou de fora, porque depende de
scripts do plugin. Os caminhos passaram a se chamar sondagem, pequeno e estrutural.

O superpowers continua instalado. Como ele se declara obrigatório antes de trabalho criativo,
o `~/.claude/CLAUDE.md` proíbe chamar o `brainstorming`, o `writing-plans` e o
`executing-plans` dele dentro do fluxo.

O Helix fica só como origem, no ADR-0016 e na spec da fase 5.

## Como a troca foi feita

Os registros de hook ganharam `|| true` antes de qualquer mudança de caminho: um script
sumido fazia o Python sair com código 2, que no hook de parada significa bloquear, e toda
sessão aberta ficaria impedida de terminar. O teste de registro passou a exigir esse final.

A skill nova foi criada ao lado da antiga, os testes rodaram, os registros foram trocados e
conferidos com entrada de exemplo, e só então a antiga foi apagada. Nenhum projeto tinha
execução em andamento.

## O que fica pendente

A prova real numa feature, agora com o nome novo, e a primeira observação de a fase 1 própria
disparar sem o superpowers competir com ela.
