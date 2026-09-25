# Limites conhecidos

- Uma etapa visível marcada como sem tela escapa da trava do mockup.
- O script sabe que o mockup está commitado, não que foi aprovado.
- A fase 1 nunca foi observada disparando sozinha a partir de um pedido cru.
- `/skills` pode não listar a Vesta por ela ser instalada como link
  (https://github.com/anthropics/claude-code/issues/14836), embora ela funcione.
- App desktop e extensão de IDE não foram testados.
- O Claude Code às vezes regrava o settings.json com uma cópia antiga
  (https://github.com/anthropics/claude-code/issues/93742), o que apagaria a guarda do supacode.
