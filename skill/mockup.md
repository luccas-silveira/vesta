# Fase 4a — Mockup

Não anuncie a entrada nesta fase. Você volta a escrever quando o mockup estiver aberto no
navegador, esperando aprovação.

Roda sempre que a spec cria ou muda algo visível: página, tela, componente, estilo, e-mail,
formulário. Sem nada visível, pule direto para o `plano.md`. Na dúvida, faça o mockup.

Entrada: a spec revisada e o dossiê. Saída: um HTML aprovado e commitado em
`docs/vesta/mockups/YYYY-MM-DD-<feature>/index.html`.

## Conteúdo antes do desenho

Antes de desenhar, escreva a lista de toda tela, estado e interação que a spec descreve. O
mockup cobre todos os itens da lista, sem exceção.

Nada de lorem ipsum nem placeholder como "Título aqui". Use dado de exemplo realista do
domínio do projeto: nomes, valores e datas que um usuário de verdade veria.

## Design: hallmark e inspo

Leia `~/.claude/skills/hallmark/SKILL.md` e siga o fluxo de design dela.

As referências vêm do inspo. Use as que estão no dossiê. Pesquisa pulada ou dossiê sem
referência visual: chame agora o `recommend` do MCP inspo com o brief da spec.

O texto é o da spec. Faltando texto, pergunte: a hallmark não inventa copy, e o mockup com
texto de mentira esconde problema de layout.

Tela que já existe e está mudando: o mockup reproduz a tela atual com a mudança aplicada, no
estilo que o projeto já tem. Não é hora de redesenhar o que a spec não pediu.

Tela nova: desenhe duas direções visuais para a tela principal, cada uma partindo de uma
referência diferente do inspo. As duas vão como seções ou abas no mesmo HTML. O usuário
escolhe uma na aprovação, e só então você completa as demais telas na direção escolhida.
Tela que já existe e está mudando fica fora disso: uma direção só, no estilo atual.

## O arquivo

Um HTML só, autocontido: CSS e JS dentro dele, fontes do Google Fonts, sem build. Os estados
que a spec descreve (vazio, erro, carregando) entram como seções ou alternâncias na mesma
página. Precisa abrir em tela de celular sem rolagem lateral.

## Autoverificação

Antes de mostrar, tire screenshots em largura de celular e de desktop pelo MCP playwright e
olhe os prints. Confira três coisas: a lista de conteúdo está toda coberta, o nível visual
está à altura das referências do inspo, e nada tem cara de wireframe (caixas cinza, sem
hierarquia). Falhou alguma, corrija e refaça os prints antes de mostrar.

Commite o mockup e abra: `open docs/vesta/mockups/<pasta>/index.html`.

## Parada do mockup

Cinco linhas: o que o mockup mostra, a escolha de design que mais pesa, a diferença entre as
duas direções, o que a autoverificação corrigiu, o caminho do arquivo.
Pare até o sim explícito.

Mudança pedida: edite, commite, abra de novo e espere.

Aprovado: leia `plano.md` e siga. O caminho do mockup vai no cabeçalho do plano e no
`criar`: sem ele, a execução de plano com tela não começa.
