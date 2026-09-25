> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# ADR-0018 — Frontend na Vesta passa por inspo, hallmark e mockup aprovado

Data: 2026-09-25. Status: em vigor. Continua o ADR-0017.

## Contexto

A Vesta levava uma feature com tela da spec à execução sem que o usuário visse a tela antes. O
plano descrevia o visual em texto, e a primeira vez que alguém olhava era na parada 2, quando o
código já estava pronto e commitado. Nesse ponto, errar a direção de design custa refazer as
etapas de tela.

No mesmo dia entraram duas ferramentas do mesmo autor (Nutlope): a hallmark, uma skill de
design contra os padrões genéricos de interface gerada, e o inspo, um MCP hospedado com 2.320
páginas de 832 sites reais para consulta.

## A decisão

Todo trabalho com algo visível passa por um mockup aprovado antes da execução, inclusive no
caminho pequeno. A única exceção é não ter tela. A sondagem também fica sem mockup, porque não
constrói nada que fica.

O mockup é um HTML autocontido commitado em `docs/vesta/mockups/`, aberto no navegador. Ele
entra na fase 4, que passou a se chamar "Mockup e plano" (roteiro em `mockup.md`), antes do
plano, para que o plano seja escrito sobre a tela aprovada. As fases não foram renumeradas:
isso mexeria em `execucao.md`, `spec.md` e nas mensagens das paradas sem ganho.

O inspo entra na pesquisa, como frente de referências visuais, e no mockup quando a pesquisa foi
pulada. A hallmark guia o mockup e o implementador das etapas de tela.

Dentro da Vesta, a hallmark substitui o impeccable. As duas disparam nos mesmos pedidos e dariam
regras diferentes para a mesma tela. O impeccable continua instalado para uso fora do fluxo.

## Por que trava no script

O "sempre" do mockup não depende de o modelo lembrar. O `vesta.py iniciar` recusa começar
quando o plano tem etapa de tela, ou pastas de tela declaradas, e o estado não aponta para um
mockup rastreado no git. O `adicionar` aplica a mesma regra às etapas novas e aceita
`{"mockup": ..., "etapas": [...]}` para o ajuste que traz a primeira tela a um plano sem tela.

O script não sabe se o usuário aprovou: sabe só que existe um mockup commitado. A aprovação
continua sendo a parada do mockup. O limite aceito é que uma etapa visível marcada como sem tela
escapa da trava.

## O que fica pendente

Ver o fluxo inteiro disparar numa feature real com tela. As ferramentas do inspo só aparecem nas
sessões abertas depois da instalação.
