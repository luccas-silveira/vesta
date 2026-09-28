"""Testes do instalador: install.sh ligando skill e comandos em CLAUDE_HOME."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(RAIZ, 'install.sh')
SKILL = os.path.realpath(os.path.join(RAIZ, 'skill'))
COMANDOS = ['vesta-retomar.md', 'vesta-pausar.md', 'vesta-painel.md']
HOOK_VESTA = 'python3 "/x/skill/scripts/vesta.py" hook-parada || true'
SUPACODE = '/x/supacode-managed-hook stop'
SILENCIAR = 'python3 "/x/skill/scripts/vesta.py" silenciar || true'


def hook(cmd):
    return [{'hooks': [{'type': 'command', 'command': cmd}]}]


class Instalador(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, 'home', '.claude')
        os.makedirs(self.home)
        self.claude_json({'mcpServers': {'inspo': {'command': 'x'}}})
        for s in ('grill-me', 'vesta-interface'):
            self.escrever(os.path.join('skills', s, 'SKILL.md'), 'x')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def p(self, *partes):
        return os.path.join(self.home, *partes)

    def escrever(self, rel, texto):
        os.makedirs(os.path.dirname(self.p(rel)), exist_ok=True)
        with open(self.p(rel), 'w') as f:
            f.write(texto)

    def claude_json(self, dados):
        with open(os.path.join(self.tmp, 'home', '.claude.json'), 'w') as f:
            json.dump(dados, f)

    def settings(self, hooks):
        self.escrever('settings.json', json.dumps({'hooks': hooks}, indent=2))

    def rodar(self):
        r = subprocess.run(['bash', INSTALL], env={**os.environ, 'CLAUDE_HOME': self.home},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout + r.stderr

    def avisos(self, saida):
        return [l for l in saida.splitlines() if l.startswith('aviso:')]

    def guardados(self, pasta):
        return [n for n in os.listdir(self.p(pasta)) if '.antes-da-vesta-' in n]

    def assertLigado(self):
        self.assertTrue(os.path.islink(self.p('skills', 'vesta')))
        self.assertEqual(os.path.realpath(self.p('skills', 'vesta')), SKILL)
        for c in COMANDOS:
            self.assertTrue(os.path.islink(self.p('commands', c)), c)
            self.assertEqual(os.path.realpath(self.p('commands', c)),
                             os.path.realpath(os.path.join(RAIZ, 'commands', c)))

    # links
    def test_primeira_instalacao_em_pasta_vazia_cria_links_e_pastas(self):
        shutil.rmtree(self.p('skills'))  # nem skills nem commands existem
        self.rodar()
        self.assertLigado()

    def test_segunda_execucao_nao_muda_nada(self):
        self.rodar()
        self.rodar()
        self.assertLigado()
        self.assertEqual(self.guardados('skills') + self.guardados('commands'), [])

    def test_pasta_vesta_de_verdade_e_guardada_intacta(self):
        self.escrever('skills/vesta/SKILL.md', 'antiga')
        saida = self.rodar()
        self.assertLigado()
        g = self.guardados('skills')
        self.assertEqual(len(g), 1)
        self.assertRegex(g[0], r'^vesta\.antes-da-vesta-\d{14}$')
        with open(self.p('skills', g[0], 'SKILL.md')) as f:
            self.assertEqual(f.read(), 'antiga')
        self.assertIn(g[0], saida)

    def test_comando_arquivo_comum_e_guardado_intacto(self):
        self.escrever('commands/vesta-pausar.md', 'meu')
        saida = self.rodar()
        self.assertLigado()
        g = self.guardados('commands')
        self.assertEqual(len(g), 1)
        self.assertRegex(g[0], r'^vesta-pausar\.md\.antes-da-vesta-\d{14}$')
        with open(self.p('commands', g[0])) as f:
            self.assertEqual(f.read(), 'meu')
        self.assertIn(g[0], saida)

    def test_link_para_outro_lugar_e_redirecionado_sem_copia(self):
        outro = os.path.join(self.tmp, 'outro')
        os.makedirs(outro)
        os.symlink(outro, self.p('skills', 'vesta'))
        self.rodar()
        self.assertLigado()
        self.assertEqual(self.guardados('skills'), [])
        self.assertTrue(os.path.isdir(outro))

    # skills irmãs
    def test_sem_grill_me_avisa(self):
        shutil.rmtree(self.p('skills', 'grill-me'))
        a = self.avisos(self.rodar())
        self.assertTrue(any('grill-me' in l for l in a), a)
        self.assertFalse(any('vesta-interface' in l for l in a), a)

    def test_sem_vesta_interface_avisa(self):
        shutil.rmtree(self.p('skills', 'vesta-interface'))
        a = self.avisos(self.rodar())
        self.assertTrue(any('skill vesta-interface ausente' in l for l in a), a)
        self.assertFalse(any('grill-me' in l for l in a), a)

    def test_sem_hallmark_nao_avisa(self):
        self.assertFalse(os.path.exists(self.p('skills', 'hallmark')))
        a = self.avisos(self.rodar())
        self.assertFalse(any('hallmark' in l.lower() for l in a), a)

    def test_tudo_presente_nenhum_aviso(self):
        self.assertEqual(self.avisos(self.rodar()), [])

    # inspo
    def test_sem_inspo_avisa(self):
        self.claude_json({'mcpServers': {'outro': {}}})
        self.assertTrue(any('inspo' in l for l in self.avisos(self.rodar())))

    def test_sem_claude_json_avisa_sem_erro(self):
        os.remove(os.path.join(self.tmp, 'home', '.claude.json'))
        self.assertTrue(any('inspo' in l for l in self.avisos(self.rodar())))
        self.assertLigado()

    def test_claude_json_ilegivel_vira_aviso(self):
        with open(os.path.join(self.tmp, 'home', '.claude.json'), 'w') as f:
            f.write('{nao e json')
        self.assertTrue(self.avisos(self.rodar()))
        self.assertLigado()

    # settings.json
    def test_hook_da_vesta_no_settings_avisa_e_nao_edita(self):
        self.settings({'Stop': hook(HOOK_VESTA)})
        with open(self.p('settings.json'), 'rb') as f:
            antes = f.read()
        a = self.avisos(self.rodar())
        self.assertTrue(any('settings.json' in l and 'duas vezes' in l for l in a), a)
        with open(self.p('settings.json'), 'rb') as f:
            self.assertEqual(f.read(), antes)

    def test_supacode_sem_guarda_avisa(self):
        self.settings({'Stop': hook(SUPACODE)})
        a = self.avisos(self.rodar())
        self.assertTrue(any('supacode' in l for l in a), a)

    def test_supacode_com_guarda_nao_avisa(self):
        self.settings({'Stop': hook(SUPACODE) + hook(SILENCIAR)})
        self.assertEqual(self.avisos(self.rodar()), [])

    def test_settings_sem_supacode_nao_avisa(self):
        self.settings({'Stop': hook('echo oi')})
        self.assertEqual(self.avisos(self.rodar()), [])

    def test_settings_ilegivel_vira_aviso_sem_erro(self):
        self.escrever('settings.json', '{quebrado')
        self.assertTrue(self.avisos(self.rodar()))
        self.assertLigado()

    # saída
    def test_saida_final_fala_dos_hooks_do_plugin(self):
        ultima = self.rodar().strip().splitlines()[-1]
        self.assertIn('plugin', ultima)
        self.assertIn('sessão nova', ultima)


if __name__ == '__main__':
    unittest.main()
