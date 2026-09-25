# Fase 5 — Execução

Não anuncie a entrada nesta fase. Entre as duas paradas você não escreve nada para o usuário:
ele não está olhando, e o hook não deixa você parar antes do fim.

Toda prova passa pelo script, sempre chamado pelo caminho completo, `python3 ~/.claude/skills/vesta/scripts/vesta.py`: cada
chamada de Bash é um shell novo, e é esse caminho no comando que liga a trava a esta sessão.
Você nunca edita o estado à mão.

## Começo

1. `python3 ~/.claude/skills/vesta/scripts/vesta.py iniciar`. A trava liga na próxima vez que você tentar parar.
2. Leia o plano inteiro uma vez.

## Cada etapa, na ordem do plano

1. **Escritor de teste.** Subagente novo, em primeiro plano, com o pedido abaixo.
2. Commit só dos arquivos que o escritor listou: `git add <arquivos> && git commit -m "test(etapa N): <título>"`.
   Nunca `git add -A`: varreria mudanças que não são da etapa.
3. `python3 ~/.claude/skills/vesta/scripts/vesta.py prova vermelho N`. A prova pode recusar por quatro motivos:
   - os testes já passam: devolva ao escritor com a saída, commite a correção e repita;
   - a falha não cita os arquivos de teste novos, ou o comando de teste não roda: o problema é o
     comando do plano, não a etapa. Rode `python3 ~/.claude/skills/vesta/scripts/vesta.py pausar comando de teste`
     e vá à parada 2 com a saída;
   - árvore suja: commite o que é da etapa; artefato gerado pelo teste vai para o `.gitignore`;
   - o último commit não tem arquivo: o escritor não criou teste; devolva a ele.
4. **Implementador.** Outro subagente novo, em primeiro plano, com o pedido abaixo.
5. Commit só dos arquivos que o implementador listou: `git add <arquivos> && git commit -m "feat(etapa N): <título>"`.
6. `python3 ~/.claude/skills/vesta/scripts/vesta.py prova teste N`. Vermelho: retome o mesmo implementador com a saída e volte ao
   passo 5. O script conta as tentativas e trava a etapa na oitava.
7. Verde: `python3 ~/.claude/skills/vesta/scripts/vesta.py concluir N`.

As tentativas acontecem dentro do mesmo turno: não pare entre uma e outra.

O comando de teste gera arquivo (relatório, cobertura, log) e a prova seguinte recusa por
árvore suja: acrescente esse arquivo ao `.gitignore` do projeto, num commit próprio.

Implementador respondeu BLOCKED porque um teste está errado: devolva ao escritor com o motivo,
commite o teste corrigido e rode de novo `prova vermelho N` antes de retomar o implementador.

Subagentes sempre em primeiro plano, nunca em segundo.

Etapa travada: vá à parada 2.

### Pedido ao escritor de teste

```
Você escreve os testes da etapa {N} de um plano. Não escreva código de produção e não rode commit.

Etapa, copiada do plano:
{texto integral da etapa}

Comando de teste do projeto: {comando}

Regras:
- Ache os testes que já existem no projeto e siga o padrão deles.
- Cada caso de "O que prova a etapa" vira pelo menos um teste. Teste o que quem usa vê, não a implementação.
- Os testes precisam falhar agora, porque o código ainda não existe. Falha por import ou símbolo ausente conta.
- Para cada teste, pense numa implementação errada plausível e confira que o teste a reprova. Teste que passaria com ela não prova nada.

Responda com os arquivos de teste criados e, para cada teste, uma linha dizendo o que ele verifica.
```

### Pedido ao implementador

```
Você implementa a etapa {N} de um plano. Os testes já existem e estão falhando.

Etapa, copiada do plano:
{texto integral da etapa}

Arquivos de teste da etapa: {lista}
Comando de teste do projeto: {comando}

Regras:
- Não altere os testes. Se um teste parecer errado, pare e responda BLOCKED com o motivo.
- Faça o mínimo que deixa os testes verdes, no padrão do código ao redor.
- Rode o comando de teste antes de responder.
- Não rode commit e não abra subagentes.
{só em etapa com Tela: sim}
- Antes de escrever código de tela, leia ~/.claude/skills/hallmark/SKILL.md e siga.
- O mockup aprovado em {caminho do mockup} é a referência: a tela sai igual a ele.

Responda com o status (DONE ou BLOCKED) e os arquivos mudados.
```

## Parada 2

Depois de concluir a última etapa, ou quando uma travar, escreva ao usuário em cinco linhas: o
que ficou pronto, o que travou e por quê (a linha decisiva da última saída), como testar a
feature.

Etapa travada e o usuário quer insistir: `/vesta-retomar`, que destrava a etapa e zera as
tentativas. `adicionar` recusa enquanto houver etapa travada.

Ajuste pedido: acrescente as etapas no plano, commite, e registre:

```bash
python3 ~/.claude/skills/vesta/scripts/vesta.py adicionar <<'JSON'
[{"id": "<próximo id>", "titulo": "<ajuste>", "tela": false}]
JSON
```

Ajuste que traz a primeira tela a um plano sem tela: faça antes o mockup (`mockup.md`), commite, e
registre com a forma objeto, `{"mockup": "<caminho>", "etapas": [...]}`. Sem mockup, `adicionar`
recusa etapa de tela.

Depois volte ao ciclo de etapa.

Usuário aprovou a feature: `python3 ~/.claude/skills/vesta/scripts/vesta.py fechar`.
