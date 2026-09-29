"""Etapa 8: o knobler-ask.sh sai da frente quando o painel da Vesta do projeto está aberto."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'skill', 'scripts'))
import test_vesta  # noqa: E402  (ComPainel, Knobler falso, Q, RESP, ESPERADO)

INSTALADO = os.path.expanduser('~/.claude/hooks/knobler-ask.sh')
TOOLING = os.path.expanduser('~/Code/claude-tooling/config/claude/hooks/knobler-ask.sh')
LINHA = ('python3 "$HOME/.claude/skills/vesta/scripts/vesta.py" aberto '
         '"$(printf \'%s\' "$INPUT" | jq -r \'.cwd // ""\')" && exit 0')


class Sempre(dict):
    """Estados do Knobler falso: o id do pedido é gerado pelo script, então vale para qualquer id."""

    def __init__(self, estado):
        super().__init__()
        self.estado = estado

    def get(self, k, d=None):
        return self.estado


def ler(caminho):
    with open(caminho) as f:
        return f.read()


class Contrato(unittest.TestCase):
    def setUp(self):
        for c in (INSTALADO, TOOLING):
            if not os.path.exists(c):
                self.skipTest(f'{c} não existe nesta máquina')

    def test_linha_antes_do_primeiro_curl(self):
        for c in (INSTALADO, TOOLING):
            linhas = [l.strip() for l in ler(c).splitlines()]
            self.assertTrue(LINHA in linhas, f'{c} não tem a linha do painel aberto')
            i = linhas.index(LINHA)
            entrada = linhas.index('INPUT="$(cat)"')
            curl = next(n for n, l in enumerate(linhas) if not l.startswith('#') and 'curl ' in l)
            self.assertLess(entrada, i, f'{c}: a linha usa $INPUT, vem depois de INPUT="$(cat)"')
            self.assertLess(i, curl, f'{c}: a linha vem antes do primeiro curl')

    def test_os_dois_arquivos_sao_iguais(self):
        self.assertEqual(ler(INSTALADO), ler(TOOLING))


class Hook(test_vesta.ComPainel):
    """Roda o knobler-ask.sh instalado com HOME temporário cuja skill vesta aponta para skill/."""

    def setUp(self):
        if not os.path.exists(INSTALADO):
            self.skipTest(f'{INSTALADO} não existe nesta máquina')
        for prog in ('jq', 'curl'):
            if not shutil.which(prog):
                self.skipTest(f'{prog} não está no PATH')
        super().setUp()
        casa = tempfile.TemporaryDirectory()
        self.addCleanup(casa.cleanup)
        os.makedirs(os.path.join(casa.name, '.claude', 'skills'))
        os.symlink(os.path.join(RAIZ, 'skill'), os.path.join(casa.name, '.claude', 'skills', 'vesta'))
        self.knobler = test_vesta.Knobler()
        self.addCleanup(self.knobler.fechar)
        self.knobler.estados = Sempre({'cancelled': True})  # hook errado não fica em polling
        self.env = {**test_vesta.ENV, 'HOME': casa.name, 'KNOBLER_PORT': str(self.knobler.porta)}

    def rodar(self):
        entrada = json.dumps({'session_id': 's1', 'cwd': self.r, 'hook_event_name': 'PreToolUse',
                              'tool_name': 'AskUserQuestion',
                              'tool_input': {'questions': test_vesta.Q}})
        # cwd do processo fora do projeto: o hook tem de usar o .cwd do JSON
        p = subprocess.run(['bash', INSTALADO], input=entrada, cwd=self.fora.name, env=self.env,
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_painel_aberto_nada_chega_ao_knobler(self):
        self.servir()
        self.estado()
        saida = self.rodar()
        self.assertEqual(self.knobler.pedidos, [])
        self.assertEqual(saida, '')

    def test_painel_fechado_pergunta_vai_ao_knobler(self):
        self.knobler.estados = Sempre({'answered': True, 'answers': test_vesta.RESP})
        saida = self.rodar()
        asks = self.knobler.posts('/ask')
        self.assertEqual(len(asks), 1)
        self.assertEqual(asks[0]['questions'], test_vesta.Q)
        self.assertEqual(asks[0]['source'], os.path.basename(self.r))
        self.assertEqual(json.loads(saida)['hookSpecificOutput']['updatedInput']['answers'],
                         test_vesta.ESPERADO)


if __name__ == '__main__':
    unittest.main()
