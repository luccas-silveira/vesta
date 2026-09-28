"""Testes do texto de skill/mockup.md: barra de conteúdo, duas direções, autoverificação."""
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKUP = os.path.join(RAIZ, 'skill', 'mockup.md')


def texto():
    with open(MOCKUP) as f:
        return f.read().lower()


def paragrafos():
    return [p for p in re.split(r'\n\s*\n', texto()) if p.strip()]


def secao(titulo):
    """Corpo da seção ## cujo título contém `titulo`, até a próxima ##."""
    for bloco in re.split(r'^## ', texto(), flags=re.M)[1:]:
        if titulo in bloco.split('\n', 1)[0]:
            return bloco
    return ''


def com(*termos):
    """Parágrafos que contêm algum dos termos."""
    return [p for p in paragrafos() if any(re.search(t, p) for t in termos)]


class TestBarraDeConteudo(unittest.TestCase):
    def test_lista_telas_estados_interacoes(self):
        ps = [p for p in com(r'\blista') if 'tela' in p and 'estado' in p and 'intera' in p]
        self.assertTrue(ps, 'falta a lista de toda tela, estado e interação da spec')

    def test_proibe_lorem_e_placeholder(self):
        ps = com(r'lorem')
        self.assertTrue(ps, 'falta proibir lorem ipsum')
        self.assertTrue(any('placeholder' in p for p in ps + com('placeholder')),
                        'falta proibir placeholder')
        self.assertTrue(any(re.search(r'proib|nunca|\bnão\b|\bnada de\b|\bsem\b', p) for p in ps),
                        'lorem citado sem proibição')

    def test_dado_realista_do_dominio(self):
        ps = com(r'realista')
        self.assertTrue(any(re.search(r'nome|valor|data', p) for p in ps),
                        'falta dado de exemplo realista (nomes, valores, datas)')


class TestDuasDirecoes(unittest.TestCase):
    def test_duas_direcoes_de_referencias_diferentes(self):
        ps = com(r'(duas|2)\s+dire[çc]')
        self.assertTrue(ps, 'falta a regra das duas direções visuais')
        self.assertTrue(any('inspo' in p or 'refer' in p for p in ps),
                        'as direções não partem de referências do inspo')

    def test_usuario_escolhe_e_resto_so_na_escolhida(self):
        ps = [p for p in com(r'dire[çc]') if re.search(r'escolh', p)]
        self.assertTrue(ps, 'falta o usuário escolher uma direção')
        self.assertTrue(any(re.search(r'demais telas|outras telas|restante', p) for p in ps),
                        'falta completar as demais telas só na direção escolhida')

    def test_excecao_tela_existente_uma_direcao(self):
        ps = [p for p in com(r'já existe') if re.search(r'dire[çc]', p)]
        self.assertTrue(ps, 'tela existente não é declarada exceção às duas direções')


class TestAutoverificacao(unittest.TestCase):
    def test_screenshot_celular_e_desktop_via_playwright(self):
        ps = com(r'screenshot|\bprints?\b|captura')
        junto = ' '.join(ps)
        for termo in ('playwright', 'celular', 'desktop'):
            self.assertIn(termo, junto, f'autoverificação sem {termo}')

    def test_confere_conteudo_referencias_e_wireframe(self):
        junto = ' '.join(com(r'screenshot|\bprints?\b|captura|autoverifica'))
        self.assertIn('wireframe', junto, 'falta o critério anti-wireframe')
        self.assertRegex(junto, r'inspo|refer', 'falta conferir o nível das referências')
        self.assertRegex(junto, r'lista|conteúdo', 'falta conferir a lista de conteúdo')

    def test_corrige_e_refaz_prints_antes_de_mostrar(self):
        ps = com(r'screenshot|\bprints?\b|captura')
        self.assertTrue(any(re.search(r'refa[zç]|de novo|novamente', p) and 'antes' in p for p in ps),
                        'falta corrigir e refazer os prints antes de mostrar')


class TestParada(unittest.TestCase):
    def test_parada_cita_diferenca_das_direcoes(self):
        self.assertRegex(secao('parada'), r'dire[çc]', 'parada sem a diferença entre as direções')

    def test_parada_cita_o_que_autoverificacao_corrigiu(self):
        self.assertRegex(secao('parada'), r'autoverifica|corrig',
                         'parada sem o que a autoverificação corrigiu')


if __name__ == '__main__':
    unittest.main()
