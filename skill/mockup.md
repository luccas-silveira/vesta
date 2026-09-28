# Fase 4a — Mockup

Não anuncie a entrada nesta fase. Você volta a escrever quando o mockup estiver aberto no
navegador, esperando aprovação.

Roda sempre que a spec cria ou muda algo visível: página, tela, componente, estilo, e-mail,
formulário. Sem nada visível, pule direto para o `plano.md`. Na dúvida, faça o mockup.

Entrada: a spec revisada e o dossiê. Saída: um mockup aprovado e commitado, com a página em
`docs/vesta/mockups/YYYY-MM-DD-<feature>/index.html`.

## Conteúdo antes do desenho

Antes de desenhar, escreva a lista de toda tela, estado e interação que a spec descreve. O
mockup cobre todos os itens da lista, sem exceção.

Nada de lorem ipsum nem placeholder como "Título aqui". Use dado de exemplo realista do
domínio do projeto: nomes, valores e datas que um usuário de verdade veria.

## Design: vesta-interface

Leia `~/.claude/skills/vesta-interface/SKILL.md` e siga o fluxo dela, os cinco passos. Esta
fase acrescenta só o que está abaixo.

As referências vêm do inspo. Use as que estão no dossiê. Pesquisa pulada ou dossiê sem
referência visual: chame agora o `recommend` do MCP inspo com o brief da spec.

Ofereça ao usuário a bifurcação da vesta-interface: com questionário (perguntas de design no
chat, uma por vez, com a sua recomendação) ou direto (você deduz as respostas e mostra junto do
mockup). Padrão: tela nova com questionário, tela que já existe direto.

O texto é o da spec. Faltando texto, pergunte: a vesta-interface não inventa copy, e o mockup
com texto de mentira esconde problema de layout.

Tela que já existe e está mudando: o mockup reproduz a tela atual com a mudança aplicada, no
estilo que o projeto já tem. Não é hora de redesenhar o que a spec não pediu.

Tela nova: desenhe duas direções visuais para a tela principal, cada uma partindo de uma
referência diferente do inspo; uma delas pode vir de `catalogo/direcoes/` da vesta-interface. As
duas vão como seções ou abas no mesmo mockup. O usuário escolhe uma na aprovação, e só então
você completa as demais telas na direção escolhida. Tela que já existe e está mudando fica fora
disso: uma direção só, no estilo atual.

## O arquivo

Projeto React: o mockup é React, numa rota de mockup própria do app (ex.:
`app/mockup/<feature>/page.tsx`), servida pelo dev server; a página de registro
`docs/vesta/mockups/<data>-<feature>/index.html` é curta e traz os prints de celular e de
desktop da última rodada e o link da rota.

Projeto sem React: `docs/vesta/mockups/<data>-<feature>/index.html` é o próprio mockup, um HTML
autocontido: CSS e JS dentro dele, fontes do Google Fonts, sem build. Os estados que a spec
descreve (vazio, erro, carregando) entram como seções ou alternâncias. Precisa abrir em tela
de celular sem rolagem lateral.

## Autoverificação

Antes de mostrar, rode a verificação de `referencias/verificacao.md` da vesta-interface, no
máximo 3 rodadas, com os prints de celular e de desktop guardados na pasta do mockup. Além do que
ela confere, olhe nos prints: a lista de conteúdo está toda coberta e nada tem cara de wireframe
(caixas cinza, sem hierarquia). Falhou alguma, corrija na rodada seguinte.

Commite o mockup e abra: `open docs/vesta/mockups/<pasta>/index.html`.

## Parada do mockup

Cinco linhas: o que o mockup mostra, a escolha de design que mais pesa, a diferença entre as
duas direções, o que a autoverificação corrigiu, o caminho da página (e a rota, no React).
Pare até o sim explícito.

Mudança pedida: edite, commite, abra de novo e espere.

Aprovado: leia `plano.md` e siga. O caminho do mockup vai no cabeçalho do plano e no
`criar`: sem ele, a execução de plano com tela não começa.
