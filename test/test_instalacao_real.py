"""Confere a instalação real da Vesta nesta máquina: links para o repositório e sem hooks duplicados."""
import glob
import json
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE = os.path.expanduser('~/.claude')
LINK_SKILL = os.path.join(CLAUDE, 'skills', 'vesta')
COMANDOS = ['vesta-retomar.md', 'vesta-pausar.md']


@unittest.skipUnless(os.path.lexists(LINK_SKILL), 'máquina sem a Vesta em ~/.claude/skills/vesta')
class InstalacaoReal(unittest.TestCase):
    def test_skill_e_link_para_pasta_skill(self):
        self.assertTrue(os.path.islink(LINK_SKILL))
        self.assertEqual(os.path.realpath(LINK_SKILL), os.path.realpath(os.path.join(RAIZ, 'skill')))

    def test_comandos_sao_links_para_commands(self):
        for nome in COMANDOS:
            with self.subTest(nome=nome):
                link = os.path.join(CLAUDE, 'commands', nome)
                self.assertTrue(os.path.islink(link))
                self.assertEqual(os.path.realpath(link),
                                 os.path.realpath(os.path.join(RAIZ, 'commands', nome)))

    def test_settings_sem_hooks_da_vesta(self):
        with open(os.path.join(CLAUDE, 'settings.json')) as f:
            hooks = json.load(f).get('hooks', {})
        comandos = [h.get('command', '') for entradas in hooks.values()
                    for e in entradas for h in e.get('hooks', [])]
        self.assertEqual([c for c in comandos if 'vesta.py" hook-' in c], [])

    def test_sem_copias_antes_da_vesta(self):
        sobras = (glob.glob(os.path.join(CLAUDE, 'skills', 'vesta.antes-da-vesta-*'))
                  + glob.glob(os.path.join(CLAUDE, 'commands', 'vesta-*.antes-da-vesta-*')))
        self.assertEqual(sobras, [])


if __name__ == '__main__':
    unittest.main()
