"""Etapa 6: skill/, commands/ e README.md não citam wayfinder; README aponta o painel."""
import os
import subprocess
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALVOS = ['skill', 'commands', 'README.md']


def rastreados():
    saida = subprocess.run(['git', 'ls-files', '--', *ALVOS], cwd=RAIZ,
                           capture_output=True, text=True, check=True).stdout
    return saida.split()


class TestSemWayfinder(unittest.TestCase):
    def test_alvos_rastreados_existem(self):
        arquivos = rastreados()
        self.assertIn('README.md', arquivos)
        self.assertTrue(any(a.startswith('skill/') for a in arquivos))

    def test_nenhum_arquivo_cita_wayfinder(self):
        citam = []
        for rel in rastreados():
            with open(os.path.join(RAIZ, rel), 'rb') as f:
                dados = f.read()
            if b'\0' in dados:
                continue
            if 'wayfinder' in dados.decode('utf-8', 'replace').lower():
                citam.append(rel)
        self.assertEqual(citam, [])

    def test_readme_cita_painel_py(self):
        with open(os.path.join(RAIZ, 'README.md')) as f:
            self.assertTrue('skill/scripts/painel.py' in f.read(), 'README não cita skill/scripts/painel.py')


if __name__ == '__main__':
    unittest.main()
