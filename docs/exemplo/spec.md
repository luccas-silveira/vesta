# Repositório próprio da Vesta

Data: 2026-09-25. Caminho: estrutural.

## Objetivo

Um repositório só da Vesta, com tudo que faz parte dela, e principalmente um lugar onde alguém
entra, lê e entende o que ela é, como funciona e do que depende.

Leitor: alguém que usa Claude Code mas nunca viu a Vesta. A explicação pode falar em skill e
hook sem definir; precisa mostrar o que a Vesta faz de diferente e por quê.

Sucesso: esse leitor sai do README sabendo o que a Vesta resolve, como o fluxo anda e onde ele
aprova; e em `docs/` acha como a trava funciona por dentro. A Vesta continua funcionando igual
em todos os projetos depois da troca.

## Decisões tomadas

- O repositório é a fonte dos arquivos. `~/.claude/skills/vesta` e os dois comandos viram
  links simbólicos para ele. Descartado: repositório como cópia (a explicação descreveria uma
  versão que já não roda).
- A pasta `skill/` é um plugin carregado da pasta de skills (`.claude-plugin/plugin.json`), e os
  3 hooks da Vesta moram em `skill/hooks/hooks.json`. O caminho continua
  `~/.claude/skills/vesta`. Os 3 registros saem do `~/.claude/settings.json`, senão rodam duas
  vezes. Os comandos ficam como links em `~/.claude/commands/`, sem o prefixo do plugin.
- A guarda que silencia o aviso do supacode durante a execução (`vesta.py silenciar`, embutida
  no hook Stop do supacode) fica no `~/.claude/settings.json`, mantida à mão. É integração
  opcional, explicada em `dependencias.md`.
- Local em `~/Code/vesta`; no GitHub `luccas-silveira/vesta`, privado. Abrir ao público depois
  exige revisar a documentação sem caminhos da máquina.
- Instalar numa máquina nova é secundário ao papel de explicação.

## Estrutura

```
vesta/
  README.md
  install.sh
  skill/        SKILL.md, spec.md, research.md, grill.md, mockup.md, plano.md, execucao.md,
                scripts/vesta.py, scripts/test_vesta.py,
                .claude-plugin/plugin.json, hooks/hooks.json
  commands/     vesta-retomar.md, vesta-pausar.md
  docs/
    como-funciona.md
    dependencias.md
    limites.md
    decisoes/   ADR-0016, 0017, 0018, e spec, pesquisa e plano da execução travada
    exemplo/    spec, pesquisa, plano e mockup de demonstração
  hooks/        pre-commit que roda os testes
```

## O README

Três perguntas, nesta ordem:

1. O que a Vesta é e que problema resolve. Sem ela, o agente pula para o código, interroga sem
   ter pesquisado, declara pronto sem teste, para no meio da execução, e a tela só é vista depois
   de construída. Cada fase aparece ligada ao problema que ela resolve.
2. Como o fluxo anda. Diagrama com os três caminhos (sondagem, pequeno, estrutural), as cinco
   fases e as paradas de aprovação. Uma seção curta por fase: entrada, saída, onde para.
3. Exemplo real de ponta a ponta: a criação deste repositório, com trechos da spec, do dossiê,
   das decisões do grill, do plano e dos commits das etapas. Os artefatos moram em
   `docs/exemplo/`. Como ele não tem tela, o README descreve em poucas linhas o caminho com
   mockup, e `docs/exemplo/mockup/` guarda um mockup pequeno de demonstração, marcado como tal.

No fim: instalação (clonar, `install.sh`) e uso (`/vesta`, `/vesta-retomar`, `/vesta-pausar`).

## docs/

- `como-funciona.md`: o estado em `.claude/vesta/`, as três provas (vermelho, teste, concluir)
  e o que cada uma confere, a trava de parada e os 3 hooks, a sessão dona, os limites (8 provas
  vermelhas no total da etapa, que só zeram no `retomar`; 5 paradas bloqueadas sem progresso,
  e a sexta libera e interrompe), a trava do mockup.
- `dependencias.md`: grill-me, hallmark, inspo; o conflito com o superpowers e a regra do
  `~/.claude/CLAUDE.md` que resolve; Python só com biblioteca padrão; git.
- `limites.md`: o que nunca foi observado e o que a trava não pega.

README e `docs/` são escritos do zero a partir dos arquivos que rodam hoje. Os documentos
antigos (ADRs 0016 a 0018, spec, pesquisa e plano da execução travada, este com 1560 linhas e os
nomes antigos) entram em `docs/decisoes/` sem reescrever o texto, cada um com uma linha no topo:
"Registro histórico; o funcionamento atual está em `como-funciona.md`."

Tudo em português.

## O install.sh

Cria os links de `~/.claude/skills/vesta` e dos dois comandos. Não mexe no
`~/.claude/settings.json`: os hooks vêm do plugin. Se o hook do supacode existe sem a guarda,
avisa; não edita. Confere se grill-me,
hallmark e inspo estão instalados e avisa o que falta; não instala nenhum deles. Aceita a pasta
de destino por variável de ambiente, para ser testado numa `~/.claude` de mentira.

## Mudanças no claude-tooling

Saem para o repositório novo: ADRs 0016, 0017 e 0018; spec, pesquisa e plano de
`spec-flow-execucao`. Ficam as specs de outras features feitas com a Vesta (painel, espelho). O
índice em `docs/README.md` passa a apontar para o repositório novo, e `docs/reference/vesta.md`
vira só um ponteiro para ele.
O pre-commit deixa de rodar os testes da Vesta. O `backup/sync.sh` passa a guardar o link; numa máquina
nova, o repositório da Vesta é clonado e o `install.sh` rodado à mão.

O claude-kit fica fora deste trabalho: a execução dele está parada na etapa 7. Pendência anotada
para quando ela for retomada: incluir `~/Code/vesta` em `fontes.json` (repositórios), para o
espelho clonar a Vesta e recriar o link em vez de copiar a pasta.

## A troca

Na ordem da renomeação para Vesta (ADR-0017):

1. Conferir que nenhum projeto tem execução da Vesta ativa. As interrompidas (claude-kit,
   Financeiro_ZOI) ficam como estão: o estado mora no projeto.
2. Repositório nasce com a cópia dos arquivos; testes passam lá.
3. `~/.claude/skills/vesta` e os comandos viram links.
4. Os 3 registros saem do `~/.claude/settings.json`; `claude plugin list` mostra a Vesta
   carregada; os 3 hooks rodam com entrada de exemplo e terminam sem erro.
5. Só então a cópia antiga sai.
6. O aviso de execução interrompida continua aparecendo no claude-kit e no Financeiro_ZOI.

Os hooks terminam com `|| true`: caminho quebrado no meio da troca não trava sessão.

## Testes

- O teste de registro dos hooks passa a ler `hooks/hooks.json` do próprio repositório: os 3
  hooks presentes, todos terminando em `|| true`.
- `install.sh` rodado duas vezes numa `~/.claude` de mentira: a segunda não duplica link nem falha.
- `install.sh` sem grill-me instalado: avisa a falta e termina sem erro.
- `install.sh` com hook do supacode sem a guarda: avisa. O teste atual da guarda
  (`test_notificacao_do_supacode_com_guarda`) sai da suíte da Vesta.
- Todo caminho de arquivo citado em `README.md` e `docs/` existe no repositório.
- Prova final, manual: sessão nova em outro projeto, `/vesta` responde, `/vesta-retomar` e
  `/vesta-pausar` aparecem.

## Decisões do grill

- **A1** — hooks passam para `skill/hooks/hooks.json`, com a pasta da skill carregada como plugin
  da pasta de skills. Motivo: o caminho `~/.claude/skills/vesta` não muda, e o settings.json é
  regravado pelo próprio Claude Code com cópia antiga (A2), o que desligaria a trava sem aviso.
- **A2** — resolvido pelo A1.
- **A3** — a guarda do supacode fica no settings.json, mantida à mão; o `install.sh` só avisa se
  faltar. Motivo: é um pedaço do hook de outra ferramenta, que o plugin não carrega.
- **A4** — o exemplo passa a ser a criação deste repositório, mais um mockup de demonstração.
  Motivo: o espelho parou na etapa 7, não mostra prova vermelha e cita clientes e caminhos.
- **A5** — claude-kit fora deste trabalho; inclusão em `fontes.json` anotada como pendência.
  Motivo: a execução dele está parada na etapa 7 e um commit no meio atrapalha a retomada.
- **A6** — a troca acontece com as duas execuções interrompidas. Motivo: interrompida não é
  ativa, e o estado mora no projeto, não na pasta da skill.
- **A7** — explicação escrita do zero a partir dos arquivos vivos; documentos antigos, inclusive o
  plano de 1560 linhas, vão como história com aviso no topo.
- **A8, A9** — mantidos: a spec já previa o teste lendo outro arquivo e o pre-commit sem a Vesta;
  com o A1, o teste lê o `hooks.json` commitado.
- **A10, A11, A12** — confirmam a spec: skill e comando por link carregam, o caminho informado é
  o do link, e os comandos ficam fora do plugin para não ganhar prefixo.
- **Sem achado** — a última etapa cria o repositório privado no GitHub e envia os arquivos, e
  só roda depois do sim do usuário: publicar sai da máquina.
- **A13** — `como-funciona.md` usa os limites como o código conta, sem pergunta ao usuário.
