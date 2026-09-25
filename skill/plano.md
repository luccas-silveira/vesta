# Fase 4 — Plano

Não anuncie a entrada nesta fase. Você volta a escrever quando o plano estiver pronto para a
parada 1.

Entrada: a spec revisada pelo grill. Saída: o plano em
`docs/vesta/plans/YYYY-MM-DD-<feature>.md`, commitado, e o estado da execução criado,
esperando aprovação.

## O plano é uma lista de etapas

Etapa é o menor pedaço que carrega a própria prova e que um revisor poderia rejeitar sozinho.
Ordem: da mais simples à mais complexa. Cada uma se apoia na anterior, e uma decisão errada
aparece cedo, quando ainda é barata.

Projeto sem comando de teste que rode: a etapa 0 monta o mínimo para rodar testes.

Para cada etapa, escreva:

- **Título**, uma linha.
- **Tela:** sim quando a etapa cria ou muda algo visível; não, caso contrário. Sim: diga qual
  parte do mockup a etapa implementa.
- **Arquivos:** caminhos exatos a criar e a mudar.
- **O que prova a etapa:** os casos de teste, do ponto de vista de quem usa, com os casos de
  borda. Escreva o que cada teste verifica, não o código do teste: quem escreve o teste é um
  subagente que lê isto.
- **Como fazer:** o suficiente para um implementador sem contexto do projeto — nomes, formatos,
  o padrão existente a seguir, com `arquivo:linha`.

Proibido no plano: "a definir", "tratar erros adequadamente", "como na etapa N". Repita o que
for preciso: cada subagente lê só a etapa dele.

## Cabeçalho do plano

- Objetivo, uma frase.
- Caminho da spec.
- Comando de teste do projeto, exato, rodando da raiz. É o que a prova de teste executa; ele
  precisa sair com código diferente de zero quando algum teste falha, e a saída da falha
  precisa citar o nome do arquivo de teste: a prova confere isso. Use o modo detalhado do
  executor quando ele não cita (`--reporter spec`, `-v`). Sem pipe no fim (`| tee` troca o
  código de saída pelo do `tee`).
- Pastas de tela: as pastas cujos arquivos contam como visíveis (componentes, estilos,
  templates). Projeto sem tela: nenhuma.
- Mockup: o caminho do mockup aprovado, ou "nenhum: sem tela".

## Crie o estado

Commite o plano. Depois:

```bash
python3 ~/.claude/skills/vesta/scripts/vesta.py criar <<'JSON'
{"plano": "docs/vesta/plans/<arquivo>.md",
 "teste": "<comando de teste>",
 "tela": ["<pasta>"],
 "mockup": "docs/vesta/mockups/<pasta>/index.html",
 "etapas": [{"id": "1", "titulo": "<título>", "tela": false}]}
JSON
```

Uma entrada em `etapas` por etapa do plano, com os mesmos ids. `mockup` fica fora só quando
não há tela; com tela e sem mockup commitado, `iniciar` recusa. O estado nasce esperando
aprovação: a trava ainda não age.

## Parada 1

Mensagem ao usuário, cinco linhas: o que o plano vai fazer, quantas etapas, o que trava, o
que decidir agora, o caminho do plano. Não repita o que está nos arquivos.

Árvore com mudanças que não são do plano: diga na parada 1. A execução não começa com elas, e
só o usuário decide entre commit e stash.

Aprovado: leia `execucao.md` e siga.

Mudança pedida: edite o plano, commite, e recrie o estado (`fechar`, depois `criar`).
