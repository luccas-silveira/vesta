# Dependências

- **grill-me**: skill usada na fase 3 (Grill) para interrogar a spec.
- **vesta-interface** e **inspo**: design, verificação e referências visuais na fase 4 e nas
  etapas com tela.
- **superpowers**: conflita com a Vesta. O superpowers manda usar `brainstorming`,
  `writing-plans` e `executing-plans`; a regra no `~/.claude/CLAUDE.md` proíbe essas três
  dentro do fluxo, porque a Vesta já cobre essas fases.
- **supacode** (opcional): o hook Stop do supacode notifica a cada parada. Para não notificar
  quando a Vesta vai bloquear a parada, o comando dele é embrulhado pela guarda
  (`vesta.py guarda` gera o trecho, que chama `vesta.py silenciar`). Isso é mantido à mão no
  settings.json do Claude Code, e o `install.sh` avisa se o hook do supacode estiver sem a guarda.
- **Python 3**, só biblioteca padrão.
- **git**, obrigatório: cada etapa termina num commit, e as provas valem para um commit.
