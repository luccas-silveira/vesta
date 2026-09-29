"""Testes do empacotamento da Vesta como plugin: plugin.json e hooks.json."""
import json
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(RAIZ, 'skill')
SCRIPT_NO_HOOK = '"${CLAUDE_PLUGIN_ROOT}/scripts/vesta.py"'


def ler(*partes):
    with open(os.path.join(SKILL, *partes)) as f:
        return json.load(f)


class Plugin(unittest.TestCase):
    def test_plugin_json_tem_nome_vesta(self):
        self.assertEqual(ler('.claude-plugin', 'plugin.json')['name'], 'vesta')


class Hooks(unittest.TestCase):
    def setUp(self):
        self.h = ler('hooks', 'hooks.json')['hooks']

    def comandos(self, evento=None):
        eventos = [evento] if evento else list(self.h)
        return [x['command'] for ev in eventos for g in self.h.get(ev, []) for x in g['hooks']]

    def test_exatamente_quatro_hooks_da_vesta(self):
        self.assertEqual(sorted(self.h), ['PostToolUse', 'PreToolUse', 'SessionStart', 'Stop'])
        self.assertEqual(len(self.comandos()), 4)
        self.assertNotIn('silenciar', ' '.join(self.comandos()))

    def test_adocao_no_post_tool_use_de_bash(self):
        grupos = self.h['PostToolUse']
        self.assertEqual([g.get('matcher') for g in grupos], ['Bash'])
        self.assertIn('vesta.py" hook-adocao', self.comandos('PostToolUse')[0])

    def test_menu_no_pre_tool_use_de_ask_user_question_com_prazo_de_uma_hora(self):
        grupos = self.h['PreToolUse']
        self.assertEqual([g.get('matcher') for g in grupos], ['AskUserQuestion'])
        [x] = grupos[0]['hooks']
        self.assertEqual(x['command'], f'python3 {SCRIPT_NO_HOOK} hook-menu || true')
        self.assertEqual(x['timeout'], 3660)  # o hook desiste aos 3600 s

    def test_inicio_no_session_start(self):
        self.assertIn('vesta.py" hook-inicio', self.comandos('SessionStart')[0])

    def test_parada_no_stop(self):
        self.assertIn('vesta.py" hook-parada', self.comandos('Stop')[0])

    def test_todo_comando_termina_em_or_true(self):
        for c in self.comandos():
            self.assertTrue(c.endswith('|| true'), c)  # script sumido nunca vira bloqueio

    def test_comandos_chamam_o_script_do_plugin_que_existe(self):
        for c in self.comandos():
            self.assertIn(SCRIPT_NO_HOOK, c)
        self.assertTrue(os.path.isfile(os.path.join(SKILL, 'scripts', 'vesta.py')))


if __name__ == '__main__':
    unittest.main()
