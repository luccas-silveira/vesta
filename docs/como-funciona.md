# Como a Vesta funciona por dentro

A fase 5 (execução) é controlada por um script só com biblioteca padrão:
`skill/scripts/vesta.py`. O roteiro que o agente segue está em `skill/execucao.md`.

## O estado

Cada projeto guarda o estado da execução em `.claude/vesta/estado.json`. A pasta
`.claude/vesta/` tem um `.gitignore` que ignora a si mesmo, então gravar o estado nunca suja a
árvore do git. Só o arquivo de aprendizados vai para o git.

## Os subcomandos

- `criar`: lê o plano em JSON (comando de teste, etapas, telas, mockup) e cria o estado,
  esperando aprovação do plano. Recusa se não houver repositório git.
- `iniciar`: depois do sim ao plano, liga a execução. Exige árvore limpa e, se houver tela, o
  mockup commitado.
- `mostrar`: imprime o estado.
- `prova`: `prova vermelho <etapa>` ou `prova teste <etapa>` (detalhes abaixo).
- `concluir`: marca a etapa como feita, só com a prova de teste verde no commit atual.
- `pausar`: interrompe a execução guardando o motivo.
- `retomar`: destrava etapas travadas, zera contadores e passa a execução para a sessão atual.
- `adicionar`: acrescenta etapas a uma execução (por exemplo, um ajuste pedido na parada 2).
- `fechar`: apaga o estado.
- `guarda`: imprime o trecho de shell que embrulha o hook Stop de outra ferramenta.
- `silenciar`: usado por esse trecho; sai 0 só quando a parada atual vai ser bloqueada pela Vesta.

## O ciclo de uma etapa

1. Um escritor de testes escreve os testes da etapa e commita.
2. `prova vermelho <etapa>`: roda o comando de teste e recusa se os testes passarem (não provam
   nada), se o último commit estiver vazio, se a árvore estiver suja, ou se a falha não citar
   nenhum dos arquivos do último commit (sinal de executor ausente ou mal configurado).
3. Um implementador escreve o código e commita, sem mexer nos testes.
4. `prova teste <etapa>`: recusa se o vermelho não foi confirmado, se a árvore estiver suja ou
   se os arquivos de teste mudaram depois do vermelho (nesse caso o vermelho é anulado).
5. `concluir <etapa>`.

## Limites

Cada etapa aceita no máximo 8 provas de teste vermelhas no total (`LIMITE_TENTATIVAS`). Na
oitava ela fica travada, e só o `retomar` a destrava. A trava de parada bloqueia no máximo 5
paradas seguidas sem progresso (`LIMITE_BLOQUEIOS`); na seguinte, a execução é interrompida e
libera a sessão. Progresso é qualquer mudança no estado das etapas, no commit ou nos arquivos.

## Hooks

`skill/hooks/hooks.json` registra três hooks:

- **Stop** (`hook-parada`): enquanto houver etapa por provar, bloqueia o fim do turno e diz ao
  agente o que falta.
- **SessionStart** (`hook-inicio`): avisa de execução travada, interrompida, ligada a outra
  sessão ou de estado ilegível.
- **PostToolUse** do Bash (`hook-adocao`): quando um comando roda `vesta.py iniciar`, `retomar`
  ou `adicionar`, essa sessão vira a dona da execução. Só a sessão dona é travada; outra sessão
  no mesmo projeto para livremente.

Se um hook falhar por defeito próprio, ele não prende a sessão.

## A trava do mockup

`iniciar` e `adicionar` passam por `exigir_mockup`: se o plano ou alguma etapa tem tela, o
arquivo do mockup precisa estar commitado no git. Sem isso, a execução não começa (o mockup se
faz seguindo `skill/mockup.md`).
