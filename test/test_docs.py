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


AVISO = '> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).'
DECISOES = os.path.join(RAIZ, 'docs', 'decisoes')
ORIGINAIS = os.path.expanduser('~/Code/claude-tooling')
# Ordem de data = ordem em que o original entrou no git do claude-tooling (git log --diff-filter=A):
# 0016 às 12:17; 0017, spec, pesquisa e plano no mesmo commit das 14:27 (empate: ordem do plano);
# 0018 às 15:58. O README de docs/decisoes/ lista os links nesta ordem.
HISTORIA = [
    ('0016-execucao-travada-por-provas.md', 'docs/decisions/0016-execucao-travada-por-provas.md'),
    ('0017-vesta.md', 'docs/decisions/0017-vesta.md'),
    ('2026-09-25-execucao-travada-spec.md', 'docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md'),
    ('2026-09-25-execucao-travada-pesquisa.md', 'docs/vesta/research/2026-09-25-spec-flow-execucao-research.md'),
    ('2026-09-25-execucao-travada-plano.md', 'docs/vesta/plans/2026-09-25-spec-flow-execucao-parte-1.md'),
    ('0018-mockup-e-frontend-na-vesta.md', 'docs/decisions/0018-mockup-e-frontend-na-vesta.md'),
]
MOCKUP = os.path.join(RAIZ, 'docs', 'exemplo', 'mockup', 'index.html')
EXTERNO = re.compile(
    r'(?:src|href)\s*=\s*["\']?\s*((?:https?:)?//[^"\'\s>]+)'
    r'|url\(\s*["\']?((?:https?:)?//[^"\')\s]+)'
    r'|@import\s+(?:url\()?\s*["\']?((?:https?:)?//[^"\')\s;]+)', re.I)
PERMITIDOS = ('fonts.googleapis.com', 'fonts.gstatic.com')


def bytes_de(caminho):
    with open(caminho, 'rb') as f:
        return f.read()


def texto_visivel(html):
    corpo = re.search(r'<body[^>]*>(.*)</body>', html, re.S | re.I)
    corpo = corpo.group(1) if corpo else ''
    corpo = re.sub(r'<(script|style)\b.*?</\1\s*>', ' ', corpo, flags=re.S | re.I)
    corpo = re.sub(r'<!--.*?-->', ' ', corpo, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', corpo)


def externos(html):
    for m in EXTERNO.finditer(html):
        alvo = next(g for g in m.groups() if g)
        host = re.sub(r'^(?:https?:)?//', '', alvo).split('/')[0].lower()
        if host not in PERMITIDOS:
            yield alvo


class DocsEtapa5(unittest.TestCase):
    def test_seis_arquivos_existem(self):
        for nome, _ in HISTORIA:
            with self.subTest(arquivo=nome):
                self.assertTrue(os.path.isfile(os.path.join(DECISOES, nome)))

    def test_primeira_linha_e_o_aviso(self):
        arquivos = [a for a in glob.glob(os.path.join(DECISOES, '*.md')) if os.path.basename(a) != 'README.md']
        self.assertGreaterEqual(len(arquivos), len(HISTORIA))
        for arquivo in arquivos:
            with self.subTest(arquivo=os.path.basename(arquivo)):
                self.assertEqual(ler(arquivo).split('\n', 1)[0], AVISO)

    def test_resto_igual_ao_original(self):
        if not os.path.isdir(ORIGINAIS):
            self.skipTest('~/Code/claude-tooling ausente')
        prefixo = (AVISO + '\n\n').encode()
        for nome, origem in HISTORIA:
            with self.subTest(arquivo=nome):
                if not os.path.exists(os.path.join(ORIGINAIS, origem)):
                    continue  # o original saiu do claude-tooling na etapa 6
                copia = bytes_de(os.path.join(DECISOES, nome))
                self.assertTrue(copia.startswith(prefixo))
                self.assertEqual(copia[len(prefixo):], bytes_de(os.path.join(ORIGINAIS, origem)))

    def test_readme_das_decisoes_lista_em_ordem(self):
        linhas = [l for l in ler(os.path.join(DECISOES, 'README.md')).splitlines() if LINK.search(l)]
        alvos = [LINK.findall(l) for l in linhas]
        self.assertTrue(all(len(a) == 1 for a in alvos), 'um link por linha')
        self.assertEqual([a[0] for a in alvos], [nome for nome, _ in HISTORIA])

    def test_mockup_diz_demonstracao(self):
        self.assertIn('demonstração', texto_visivel(ler(MOCKUP)))

    def test_mockup_sem_recurso_externo(self):
        self.assertEqual(list(externos(ler(MOCKUP))), [])

    def test_detectores_do_mockup(self):
        html = ('<link href="https://fonts.googleapis.com/css2?x"><img src="//cdn.x.com/a.png">'
                '<style>@import "http://y.com/b.css";a{background:url(https://z.com/c.png)}</style>')
        self.assertEqual(list(externos(html)), ['//cdn.x.com/a.png', 'http://y.com/b.css', 'https://z.com/c.png'])
        oculto = '<body><script>"demonstração"</script><p title="demonstração"></p></body>'
        self.assertNotIn('demonstração', texto_visivel(oculto))

    def test_readme_liga_decisoes_e_mockup(self):
        links = LINK.findall(ler(README))
        for rel in ['docs/decisoes/README.md', 'docs/exemplo/mockup/index.html']:
            with self.subTest(arquivo=rel):
                self.assertIn(rel, links)


if __name__ == '__main__':
    unittest.main()
