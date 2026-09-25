"""Testes da documentação: README.md e docs/*.md."""
import glob
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(RAIZ, 'README.md')

LINK = re.compile(r'\[[^\]]*\]\(([^)#\s]+)')
CRASE = re.compile(r'`([^`\s]+)`')
CERCA = re.compile(r'^```.*?^```', re.S | re.M)
EXCLUIDO_INICIO = ('~', '/', 'http', '$', '.claude/')
EXTENSOES = ('.md', '.py', '.sh', '.json')


def arquivos_de_documentacao():
    """README e o primeiro nível de docs/. Etapas seguintes acrescentam aqui."""
    return [README] + sorted(glob.glob(os.path.join(RAIZ, 'docs', '*.md')))


def ler(caminho):
    with open(caminho) as f:
        return f.read()


def ignorado(alvo):
    return alvo.startswith(EXCLUIDO_INICIO) or '<' in alvo or '*' in alvo or 'docs/vesta/' in alvo


def caminhos(texto):
    """Devolve [(tipo, alvo)] fora de blocos cercados; tipo é 'link' ou 'crase'."""
    texto = CERCA.sub('', texto)
    achados = [('link', a) for a in LINK.findall(texto) if not ignorado(a)]
    achados += [('crase', a) for a in CRASE.findall(texto)
                if ('/' in a or a.endswith(EXTENSOES)) and not ignorado(a)]
    return achados


def inexistentes(arquivo, texto=None):
    texto = ler(arquivo) if texto is None else texto
    base = {'link': os.path.dirname(arquivo), 'crase': RAIZ}
    return [a for tipo, a in caminhos(texto) if not os.path.exists(os.path.join(base[tipo], a))]


def secao(texto, titulo):
    inicio = texto.index(titulo + '\n')
    fim = texto.find('\n## ', inicio + 1)
    return texto[inicio:fim if fim != -1 else len(texto)]


class Extracao(unittest.TestCase):
    EXEMPLO = (
        'Veja [plano](docs/exemplo/plano.md) e [nada](nao-existe.md#x).\n'
        'Script `skill/scripts/vesta.py`, falta `sumiu.py`, palavra `solta`.\n'
        '```\n[dentro](cercado-link.md) `cercado/crase.md`\n```\n'
        '`~/Code/vesta` `/Users/x` `http://a/b` `$HOME/x` `.claude/vesta/x.json` '
        '`docs/<nome>.md` `skill/*.md` `docs/vesta/spec.md` [web](https://a.b/c)\n'
    )

    def test_link_e_crase_inexistentes_sao_detectados(self):
        falta = inexistentes(os.path.join(RAIZ, 'README.md'), self.EXEMPLO)
        self.assertEqual(sorted(falta), ['nao-existe.md', 'sumiu.py'])

    def test_bloco_cercado_e_ignorado(self):
        alvos = [a for _, a in caminhos(self.EXEMPLO)]
        self.assertNotIn('cercado-link.md', alvos)
        self.assertNotIn('cercado/crase.md', alvos)

    def test_exclusoes_respeitadas(self):
        alvos = [a for _, a in caminhos(self.EXEMPLO)]
        self.assertEqual(sorted(alvos), sorted([
            'docs/exemplo/plano.md', 'nao-existe.md', 'skill/scripts/vesta.py', 'sumiu.py']))


class Readme(unittest.TestCase):
    def setUp(self):
        self.texto = ler(README)

    def test_titulos_na_ordem(self):
        titulos = ['## O que a Vesta resolve', '## Como o fluxo anda',
                   '## Exemplo de ponta a ponta', '## Instalação', '## Uso']
        linhas = self.texto.splitlines()
        posicoes = [linhas.index(t) for t in titulos]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_fluxo_tem_mermaid(self):
        self.assertIn('```mermaid', secao(self.texto, '## Como o fluxo anda'))

    def test_fluxo_cita_fases_e_caminhos(self):
        s = secao(self.texto, '## Como o fluxo anda')
        for nome in ['Spec', 'Pesquisa', 'Grill', 'Mockup e plano', 'Execução',
                     'sondagem', 'pequeno', 'estrutural']:
            self.assertIn(nome, s)


class Caminhos(unittest.TestCase):
    def test_caminhos_citados_existem(self):
        for arquivo in arquivos_de_documentacao():
            with self.subTest(arquivo=os.path.relpath(arquivo, RAIZ)):
                self.assertEqual(inexistentes(arquivo), [])

    def test_sem_caminho_absoluto_de_usuario(self):
        for arquivo in arquivos_de_documentacao():
            with self.subTest(arquivo=os.path.relpath(arquivo, RAIZ)):
                self.assertNotIn('/Users/', ler(arquivo))


if __name__ == '__main__':
    unittest.main()
