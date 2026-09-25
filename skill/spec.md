# Fase 1 — Spec

Adaptado do `brainstorming` do superpowers (Jesse Vincent, licença MIT,
https://github.com/obra/superpowers).

A saída desta fase é um entendimento que o usuário reconhece e corrige, ancorado no que ele
quer alcançar. Nada de código, estrutura de projeto ou dependência instalada antes da
aprovação que o caminho escolhido exige.

## Classifique antes da primeira pergunta

Diga a classificação em voz alta, numa frase, para o usuário poder corrigir.

- **Sondagem** — pergunta de viabilidade ("dá para…", "é possível…"). A saída é uma
  resposta, não código que fica. Apresente em duas ou três frases a pergunta e o que você vai
  testar, espere o sim, descubra do jeito mais barato que ainda seja correto e responda com
  uma recomendação. O que você construir para descobrir é descartável e é chamado assim.
- **Pequeno** — mudança pequena num fluxo que já existe neste repositório: uma opção nova, um
  endpoint, um conserto num arquivo. Pequeno mede o repositório, não a sua familiaridade com
  o tipo de coisa: sem fluxo existente para mudar, não é pequeno.
- **Estrutural** — projeto novo, subsistema novo, mudança no jeito como as partes se
  encaixam ou numa interface de que outros dependem.

Na dúvida entre dois, fique com o mais pesado. A classificação só sobe: complexidade que
aparece no meio do caminho faz parar, dizer e subir de caminho. Nunca desce.

## Entenda a intenção

1. Descubra o resultado pretendido, para quem é e o que conta como sucesso. Faltando isso,
   faça uma pergunta sobre propósito antes de propor qualquer coisa.
2. Escreva de volta o que entendeu: resultado, restrições, critério de sucesso. Separe o que
   ele disse do que você supôs. Incorpore a correção antes de seguir.
3. Leve esse entendimento para o design e confira cada escolha contra ele.

Olhe o projeto antes de perguntar: arquivos, documentação, commits recentes. Pedido com
vários subsistemas independentes: aponte na hora e ajude a quebrar em partes; cada parte roda
o ciclo inteiro sozinha.

Uma pergunta por mensagem. Múltipla escolha quando der.

## Caminho pequeno

Perguntas que importam, design curto no chat (abordagem, arquivos, como testar), e PARE até
o sim explícito. A mudança tem algo visível: faça também o mockup (`mockup.md` nesta pasta),
e o sim aprova os dois juntos. Apresentar o design e começar na mesma mensagem é pular a aprovação.

Com o sim, pule as fases 2, 3 e 4, crie o estado com uma etapa só e entre na fase 5. O
design aprovado conta como parada 1 e é o texto da etapa. Projeto sem comando de teste:
acrescente antes a etapa `0`, que monta o mínimo para rodar testes.

```bash
python3 ~/.claude/skills/vesta/scripts/vesta.py criar <<'JSON'
{"plano": "chat", "teste": "<comando de teste>", "tela": [],
 "etapas": [{"id": "1", "titulo": "<o pedido>", "tela": false}]}
JSON
```

Com tela: `"tela": true` na etapa e `"mockup": "<caminho do mockup commitado>"` no JSON.

## Caminho estrutural

1. Perguntas, uma de cada vez, até entender propósito, restrições e sucesso.
2. Duas ou três abordagens com prós e contras. Comece pela recomendada e diga por quê. Corte
   de todas o que não é necessário.
3. Design em seções, cada uma do tamanho da sua complexidade: arquitetura, componentes, fluxo
   de dados, erros, testes. Pergunte depois de cada seção se está certo.
4. Unidades pequenas, cada uma com um propósito, uma interface clara e testável sozinha. Em
   código existente, siga o padrão que está lá; melhore só o que atrapalha este trabalho.
5. Escreva a spec em `docs/vesta/specs/YYYY-MM-DD-<topico>-design.md` e commite.
6. Releia com olhos frescos e conserte na hora: nada de "a definir", nenhuma seção
   contradizendo outra, escopo que cabe num plano, nenhum requisito com duas leituras.
7. Peça ao usuário que revise o arquivo. Mudança pedida: ajuste, releia, peça de novo.

Com a spec aprovada, a fase 1 acabou: volte ao `SKILL.md` e entre na fase 2.
