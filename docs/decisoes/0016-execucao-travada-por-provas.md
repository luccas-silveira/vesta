> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# ADR-0016 — A execução do spec-flow é travada por provas, não por instrução

Data: 2026-09-25. Status: em vigor. Aplica o ADR-0014 ao spec-flow.

## Contexto

O spec-flow terminava no plano. Daí em diante a qualidade dependia de instrução em prosa, e o
agente parava antes do fim, declarava pronto sem testar e repetia erros já corrigidos. O
Helix, da Shopify (https://shopify.engineering/helix), resolve o mesmo problema com etapas
pequenas e provas que a etapa precisa passar antes da seguinte.

Spec: `docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md`. Pesquisa:
`docs/vesta/research/2026-09-25-spec-flow-execucao-research.md`.

## A decisão

O spec-flow ganha a fase 5. Um hook de parada lê o estado da execução e devolve o agente ao
trabalho enquanto houver etapa sem prova. A prova de teste é rodada por um script, não
declarada pelo agente, e vale para um commit exato com a árvore limpa.

A fase 4 deixa de usar o `superpowers:writing-plans`: o formato de etapas e o fim da fase são
do spec-flow, e o texto do superpowers muda entre versões.

Limites: 8 tentativas vermelhas por prova travam a etapa; mais de 5 bloqueios seguidos sem
mudança liberam a parada e marcam a execução como interrompida. O Claude Code já corta
sozinho em 8 bloqueios seguidos, sem avisar o hook.

Os nomes são "etapa" e "prova", e não os do Helix, porque "checkpoint" e "gate" já tinham
outro sentido neste setup.

A execução pertence à sessão que rodou `iniciar`, `retomar` ou `adicionar`. Quem registra a
dona é um hook depois do Bash, que lê a sessão na própria entrada. A primeira versão deixava o
hook de parada adotar a primeira sessão que parasse, e a revisão final mostrou o defeito: outro
terminal aberto no mesmo projeto tomava a execução, e a sessão dona ficava sem trava.

## O que o hook não cobre

O hook de parada não dispara no Esc, em erro de API nem em limite de uso. Nesses casos a
sessão para e o estado fica dizendo que a execução está ativa. A saída é um aviso no começo
da sessão seguinte e o comando `/spec-flow-retomar`.

A guarda que cala a notificação do supacode durante a execução está no comando que o
supacode gerencia. Se ele reescrever o próprio hook, a guarda some; o teste do registro, que o
pre-commit roda sobre a cópia do backup, reprova quando isso acontecer.

## O que fica pendente

Partes 2 a 4 da spec: revisão adversária, prova visual com protótipo, arquivo de aprendizados.
Cada uma entra quando a parte 1 tiver rodado numa feature real.
