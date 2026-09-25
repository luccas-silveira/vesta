# Fase 4a — Mockup

Não anuncie a entrada nesta fase. Você volta a escrever quando o mockup estiver aberto no
navegador, esperando aprovação.

Roda sempre que a spec cria ou muda algo visível: página, tela, componente, estilo, e-mail,
formulário. Sem nada visível, pule direto para o `plano.md`. Na dúvida, faça o mockup.

Entrada: a spec revisada e o dossiê. Saída: um HTML aprovado e commitado em
`docs/vesta/mockups/YYYY-MM-DD-<feature>/index.html`.

## Design: hallmark e inspo

Leia `~/.claude/skills/hallmark/SKILL.md` e siga o fluxo de design dela.

As referências vêm do inspo. Use as que estão no dossiê. Pesquisa pulada ou dossiê sem
referência visual: chame agora o `recommend` do MCP inspo com o brief da spec.

O texto é o da spec. Faltando texto, pergunte: a hallmark não inventa copy, e o mockup com
texto de mentira esconde problema de layout.

Tela que já existe e está mudando: o mockup reproduz a tela atual com a mudança aplicada, no
estilo que o projeto já tem. Não é hora de redesenhar o que a spec não pediu.

## O arquivo

Um HTML só, autocontido: CSS e JS dentro dele, fontes do Google Fonts, sem build. Os estados
que a spec descreve (vazio, erro, carregando) entram como seções ou alternâncias na mesma
página. Precisa abrir em tela de celular sem rolagem lateral.

Commite o mockup e abra: `open docs/vesta/mockups/<pasta>/index.html`.

## Parada do mockup

Três linhas: o que o mockup mostra, a escolha de design que mais pesa, o caminho do arquivo.
Pare até o sim explícito.

Mudança pedida: edite, commite, abra de novo e espere.

Aprovado: leia `plano.md` e siga. O caminho do mockup vai no cabeçalho do plano e no
`criar`: sem ele, a execução de plano com tela não começa.
