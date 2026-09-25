# Fase 2 — Pesquisa

Munição pro grill. Sem isso o grill interroga no vácuo.

Não anuncie a entrada nesta fase. A troca de fase não é notícia — o usuário vê as
ferramentas rodando. Você só volta a escrever quando o dossiê estiver pronto.

## Dispare as duas frentes EM PARALELO

Numa mensagem só, múltiplas tool calls. Interna e externa não dependem uma da outra.

### Interna — até 3 agentes `Explore`

Um foco por agente. Dê a cada um o texto da spec e peça `file:line` em todo achado.

1. **Reuso** — o que já existe no repo que a spec propõe reescrever? Helper, util, tipo,
   padrão estabelecido. A spec inventa algo que está três arquivos ao lado?
2. **Documentação e glossário** — `CONTEXT.md`, `CONTEXT-MAP.md`, `docs/adr/`, `README`.
   Decisão já documentada que a spec contradiz. Termo que a spec usa com sentido diferente
   do glossário do projeto.
3. **Blast radius** — quem chama o que a spec vai mexer. Onde isso quebra. Como o projeto
   testa código desse tipo.

Repo pequeno ou escopo isolado: um agente só. Não force três.

### Externa — 1 `web-search-agent`, background

Peça:

- **Prior art** — como esse problema já é resolvido. Feature nativa da plataforma, função
  da stdlib, ou dependência já instalada que dispensa o código da spec.
- **Armadilha conhecida** — o que dá errado na abordagem que a spec escolheu. Postmortem,
  issue, thread de gente que tentou.
- **Doc oficial** — de toda ferramenta/API/serviço nomeado na spec. Confirmar que a spec
  assume comportamento real, não comportamento imaginado. Rate limit, formato de payload,
  campo que não existe.

### Referências visuais — inspo, quando a spec tem frontend

Chame o `recommend` do MCP inspo com o brief da spec. Cada referência que servir vira achado,
com a URL do site como fonte e o que ela ensina para esta tela: estrutura, tipografia, paleta.
Essas referências alimentam o mockup da fase 4.

Sem ferramenta externa e sem incerteza técnica na spec: pule a frente externa e diga isso
no dossiê. Não invente busca pra parecer completo.

## Dossiê

Escreva em `docs/vesta/research/YYYY-MM-DD-<topico>-research.md`.

Cada achado é acionável, não resumo. Achado sem fonte não entra.

```markdown
# Pesquisa — <tópico>

Spec: `docs/vesta/specs/YYYY-MM-DD-<topico>-design.md`

## Achados

### A1 — <o fato, uma frase>
- Fonte: `src/foo/bar.ts:42`   (ou URL)
- Contradiz a spec: sim | não | parcial
- Pergunta que levanta: <a pergunta que o grill vai fazer, escrita em consequência para
  o usuário — o que ele ganha, perde ou arrisca — não em nome de função ou biblioteca>

### A2 — ...
```

## Fila de pontos quentes

Feche o dossiê com isto:

```markdown
## Fila do grill

Ordenada por dependência — decisão que trava outras vem primeiro.

1. A3 — <pergunta> (trava A5, A7)
2. A5 — <pergunta>
3. ...
```

Entra na fila todo achado com `Contradiz: sim` ou `parcial`.

Achado que só confirma a spec fica no dossiê como registro, fora da fila.

**Fila vazia é resultado válido.** Diga explicitamente: "Nenhum achado contradiz a spec."
Não fabrique tensão. O grill roda mesmo assim, curto, sobre os galhos que a spec deixou
em aberto por conta própria.
