"""Etapa 11: skill/, commands/, README.md e install.sh não citam hallmark; a Vesta aponta a vesta-interface."""
import os
import subprocess
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# docs/ fica de fora: decisões, exemplo e mockups são registro histórico
ALVOS = ['skill', 'commands', 'README.md', 'install.sh']
LER_VI = '~/.claude/skills/vesta-interface/SKILL.md'


def rastreados():
    saida = subprocess.run(['git', 'ls-files', '--', *ALVOS], cwd=RAIZ,
                           capture_output=True, text=True, check=True).stdout
    return saida.split()


def ler(rel):
    with open(os.path.join(RAIZ, rel)) as f:
        return f.read()


class TestSemHallmark(unittest.TestCase):
    def test_alvos_rastreados_existem(self):
        arquivos = rastreados()
        for rel in ('README.md', 'install.sh', 'skill/scripts/painel.html'):
            self.assertIn(rel, arquivos)
        self.assertTrue(any(a.startswith('commands/') for a in arquivos))

    def test_nenhum_arquivo_cita_hallmark(self):
        citam = []
        for rel in rastreados():
            with open(os.path.join(RAIZ, rel), 'rb') as f:
                dados = f.read()
            if b'\0' in dados:
                continue
            if 'hallmark' in dados.decode('utf-8', 'replace').lower():
                citam.append(rel)
        self.assertEqual(citam, [])


class TestApontaVestaInterface(unittest.TestCase):
    def test_skill_md_diz_que_frontend_usa_vesta_interface(self):
        linhas = [l for l in ler('skill/SKILL.md').splitlines() if 'frontend' in l.lower()]
        self.assertTrue(any('vesta-interface' in l for l in linhas),
                        'skill/SKILL.md não diz que o frontend usa a vesta-interface')

    def test_execucao_manda_etapa_com_tela_ler_vesta_interface(self):
        texto = ler('skill/execucao.md')
        self.assertIn('{só em etapa com Tela: sim}', texto)
        trecho = texto.split('{só em etapa com Tela: sim}', 1)[1].split('\n\n', 1)[0]
        self.assertIn(LER_VI, trecho, 'prompt de etapa com tela não manda ler a vesta-interface')

    def test_research_chama_inspo_nas_referencias_visuais(self):
        texto = ler('skill/research.md')
        self.assertRegex(texto, r'### Referências visuais — inspo')
        self.assertIn('`recommend` do MCP inspo', texto)

    def test_readme_cita_vesta_interface_no_mockup_e_no_instalador(self):
        texto = ler('README.md')
        mockup = texto.split('### Mockup e plano', 1)[1].split('\n\n', 2)[1]
        self.assertIn('vesta-interface', mockup, 'README não diz que o mockup sai da vesta-interface')
        avisos = [p for p in texto.split('\n\n') if 'só avisa' in p]
        self.assertTrue(any('vesta-interface' in p for p in avisos),
                        'README não diz que o install.sh avisa quando falta a vesta-interface')


if __name__ == '__main__':
    unittest.main()
