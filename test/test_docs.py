"""Testes da documentação: README.md e docs/*.md."""
import ast
import glob
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(RAIZ, 'README.md')
VESTA = os.path.join(RAIZ, 'skill', 'scripts', 'vesta.py')
NOVOS = ['docs/como-funciona.md', 'docs/dependencias.md', 'docs/limites.md']

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


def constante(nome):
    return re.search(rf'^{nome}\s*=\s*(\d+)', ler(VESTA), re.M).group(1)


def comandos():
    for no in ast.parse(ler(VESTA)).body:
        if isinstance(no, ast.Assign) and any(getattr(t, 'id', None) == 'COMANDOS' for t in no.targets):
            return [k.value for k in no.value.keys]


class DocsEtapa4(unittest.TestCase):
    def texto(self, rel):
        return ler(os.path.join(RAIZ, rel))

    def test_arquivos_novos_existem(self):
        for rel in NOVOS:
            with self.subTest(arquivo=rel):
                self.assertTrue(os.path.isfile(os.path.join(RAIZ, rel)))

    def test_readme_liga_os_tres(self):
        links = LINK.findall(ler(README))
        for rel in NOVOS:
            with self.subTest(arquivo=rel):
                self.assertIn(rel, links)

    def test_como_funciona_cita_limites_do_codigo(self):
        texto = self.texto('docs/como-funciona.md')
        for nome in ['LIMITE_TENTATIVAS', 'LIMITE_BLOQUEIOS']:
            with self.subTest(constante=nome):
                self.assertRegex(texto, rf'(?<!\d){constante(nome)}(?!\d)')

    def test_como_funciona_cita_cada_subcomando(self):
        texto = self.texto('docs/como-funciona.md')
        nomes = comandos() + ['silenciar']
        self.assertGreater(len(nomes), 1)
        for nome in nomes:
            with self.subTest(comando=nome):
                self.assertIn(f'`{nome}`', texto)

    def test_dependencias_cita_ferramentas(self):
        texto = self.texto('docs/dependencias.md')
        for nome in ['grill-me', 'hallmark', 'inspo', 'superpowers', 'supacode']:
            with self.subTest(nome=nome):
                self.assertIn(nome, texto)

    def test_regras_de_caminho_cobrem_novos(self):
        cobertos = [os.path.relpath(a, RAIZ) for a in arquivos_de_documentacao()]
        for rel in NOVOS:
            with self.subTest(arquivo=rel):
                self.assertIn(rel, cobertos)


if __name__ == '__main__':
    unittest.main()
