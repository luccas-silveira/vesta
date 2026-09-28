> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# ADR-0021 — A camada de interface da Vesta passa a ser a vesta-interface

Data: 2026-09-28. Status: em vigor. Reverte em parte o ADR-0018.

## Contexto

Pelo ADR-0018, a camada de interface da Vesta era a hallmark, que guiava o mockup e as etapas de
tela, mais o inspo, que trazia referências de sites reais. As duas cobriam o gosto, mas faltava o
resto: um sistema visual que ficasse no projeto, a verificação na página renderizada (prints, CSS
computado, console, desempenho) e componentes de verdade quando o projeto é React.

## A decisão

A hallmark sai da Vesta e entra a vesta-interface, skill em `~/Code/vesta-interface`. Ela funde
hallmark, taste-skill, impeccable (detector travado em 0.1.6), ui-ux-pro-max, shadcn (CLI travado
em 4.21.0), Chrome DevTools MCP, Playwright MCP e inspo num fluxo de cinco passos: entender o
pedido, referências, sistema visual, construção e verificação.

O inspo continua, agora no passo de referências da vesta-interface. A hallmark sai de
`~/.claude/skills` e fica congelada em `~/Code/ux-lab/vendor/hallmark`, como as outras fontes. O
mockup aprovado antes da execução e a trava no `vesta.py` do ADR-0018 não mudam.

O que a revisão do plano fixou:

- O `SKILL.md` tem um piso com as regras que aparecem em 3 ou mais fontes, e cada passo manda
  abrir a referência, porque o agente raramente abre referência de skill por conta própria.
- Os três botões do taste (variação, movimento, densidade) entram, com padrão por tipo de tela,
  guardados em `docs/design/sistema.md`.
- shadcn só pelo CLI travado, sem MCP: o MCP só devolve o comando de instalação, e na 4.21.0 o
  imprime quebrado.
- Chrome DevTools só para navegação, depuração e desempenho; clique e tamanho ficam com o
  Playwright.
- O detector examina a página renderizada, e todo alarme é corrigido ou refutado com prova.
- Playwright MCP com `--snapshot-mode none`, porque a árvore da página depois de cada ação é o
  maior custo.
- A rotação de macroestrutura vale só em Persuadir e Experiência, garantida por
  `ferramentas/rotacao.py`; num app, o menu deve se repetir.

## O que se perde

Ficam de fora da primeira versão, e não havia nenhum deles na hallmark:

- O modo live do impeccable, que edita a página aberta no navegador.
- A imagem gerada, que depende de API paga.
- Interface nativa iOS/Android.
- As regras de gráfico e das 22 stacks do ui-ux-pro-max; os dados seguem consultáveis pela busca.
