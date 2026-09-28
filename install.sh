#!/bin/bash
# Instalador da Vesta: liga skill e comandos em CLAUDE_HOME e avisa do que falta.
set -eu
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
REPO="$(cd "$(dirname "$0")" && pwd -P)"

ligar() {
  destino=$1 alvo=$2
  if [ -L "$destino" ]; then
    [ "$(readlink "$destino")" = "$alvo" ] && return 0
    ln -sfn "$alvo" "$destino"
  elif [ -e "$destino" ]; then
    copia="$destino.antes-da-vesta-$(date +%Y%m%d%H%M%S)"
    mv "$destino" "$copia"
    echo "guardado: $(basename "$copia")"
    ln -s "$alvo" "$destino"
  else
    ln -s "$alvo" "$destino"
  fi
}

mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/commands"
ligar "$CLAUDE_HOME/skills/vesta" "$REPO/skill"
for c in vesta-retomar.md vesta-pausar.md vesta-painel.md; do
  ligar "$CLAUDE_HOME/commands/$c" "$REPO/commands/$c"
done

for s in grill-me vesta-interface; do
  [ -f "$CLAUDE_HOME/skills/$s/SKILL.md" ] || echo "aviso: skill $s ausente em $CLAUDE_HOME/skills/$s"
done

CLAUDE_HOME="$CLAUDE_HOME" python3 - <<'PY' || true
import json, os
home = os.environ['CLAUDE_HOME']

def ler(p):
    try:
        with open(p) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (ValueError, OSError) as e:
        print(f'aviso: {p} ilegível ({e})')
        return False

cj = ler(os.path.join(os.path.dirname(home), '.claude.json'))
if not (isinstance(cj, dict) and 'inspo' in (cj.get('mcpServers') or {})):
    print('aviso: MCP inspo não encontrado em mcpServers do .claude.json')

st = ler(os.path.join(home, 'settings.json'))
if isinstance(st, dict):
    hooks = st.get('hooks') or {}
    def cmds(ev):
        return [h.get('command', '') for g in hooks.get(ev) or [] for h in g.get('hooks') or []]
    todos = [c for ev in hooks for c in cmds(ev)]
    if any('vesta.py" hook-' in c for c in todos):
        print('aviso: settings.json tem hooks da Vesta; com o plugin eles rodariam duas vezes. Remova-os do settings.json')
    stop = cmds('Stop')
    if any('supacode-managed-hook' in c for c in stop) and not any('vesta.py" silenciar' in c for c in stop):
        print('aviso: hook Stop do supacode sem a guarda vesta.py silenciar no settings.json')
PY

echo "Pronto. Os hooks vêm do plugin e só carregam em sessão nova."
