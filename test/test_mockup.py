"""Testes do texto de skill/mockup.md: barra de conteúdo, vesta-interface, questionário, direções, rota, verificação."""
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


class TestVestaInterface(unittest.TestCase):
    def test_manda_ler_skill_md_da_vesta_interface(self):
        self.assertIn('~/.claude/skills/vesta-interface/skill.md', texto(),
                      'mockup.md não manda ler ~/.claude/skills/vesta-interface/SKILL.md')

    def test_nao_cita_hallmark(self):
        self.assertNotIn('hallmark', texto())

    def test_bifurcacao_com_e_sem_questionario(self):
        ps = com(r'question[áa]rio')
        self.assertTrue(ps, 'falta a bifurcação do questionário')
        self.assertTrue(any(re.search(r'com question[áa]rio', p)
                            and re.search(r'sem question[áa]rio|\bdireto\b', p) for p in ps),
                        'falta oferecer os dois caminhos: com questionário e sem (direto)')


# etapa 15 da vesta-interface: o questionário vai pelo menu do AskUserQuestion, como no SKILL.md dela
UMA_POR_CHAMADA = (r'\buma (só )?pergunta (só )?(por|em cada|a cada|de cada) chamada'
                   r'|\bcada chamada\b[^.]*\b(uma (só )?pergunta|só uma pergunta)')
VARIAS_POR_CHAMADA = (r'\b(várias|varias|até \d+|até (duas|três|quatro)|mais de uma|\d+) perguntas'
                      r' (por|numa|em uma|na mesma|de uma vez na) chamada')
RECOMENDADA_PRIMEIRO = (r'recomend[^.]*\b(em primeiro|primeira|primeiro lugar|no topo|à frente)'
                        r'|\b(em primeiro|primeira|primeiro lugar|no topo)\b[^.]*recomend')


class TestQuestionarioPorMenu(unittest.TestCase):
    def questionario(self):
        ps = com(r'askuserquestion')
        self.assertTrue(ps, 'o questionário não cita a ferramenta AskUserQuestion')
        return ps

    def test_nome_da_ferramenta_com_a_caixa_certa(self):
        with open(MOCKUP) as f:
            self.assertIn('AskUserQuestion', f.read())

    def test_uma_pergunta_por_chamada(self):
        ps = self.questionario()
        self.assertTrue(any(re.search(UMA_POR_CHAMADA, p) for p in ps),
                        'falta dizer que cada chamada do AskUserQuestion leva uma pergunta só')
        self.assertFalse([p for p in paragrafos() if re.search(VARIAS_POR_CHAMADA, p)],
                         'o questionário junta várias perguntas numa chamada')

    def test_recomendada_em_primeiro_e_marcada_recomendado(self):
        ps = [p for p in self.questionario() if '(recomendado)' in p]
        self.assertTrue(ps, 'falta marcar a opção recomendada com "(Recomendado)"')
        self.assertTrue(any(re.search(RECOMENDADA_PRIMEIRO, p) for p in ps),
                        'a opção recomendada não vem em primeiro')

    def test_aceita_resposta_livre_outro(self):
        self.assertTrue([p for p in self.questionario() if re.search(r'\boutro\b', p) and 'livre' in p],
                        'falta aceitar a resposta livre ("Outro") do usuário')

    def test_perguntas_nao_sao_mais_no_chat(self):
        self.assertFalse([p for p in com(r'question[áa]rio|pergunt') if re.search(r'\bchat\b', p)],
                         'o questionário ainda manda perguntar no chat')


class TestDuasDirecoes(unittest.TestCase):
    def test_duas_direcoes_na_tela_nova_uma_do_catalogo(self):
        ps = com(r'(duas|2)\s+dire[çc]')
        self.assertTrue(ps, 'falta a regra das duas direções visuais')
        self.assertTrue(any('tela nova' in p for p in ps), 'as duas direções não são da tela nova')
        self.assertTrue(any('catalogo/direcoes/' in p for p in ps),
                        'falta dizer que uma direção pode vir de catalogo/direcoes/')

    def test_usuario_escolhe_e_resto_so_na_escolhida(self):
        ps = [p for p in com(r'dire[çc]') if re.search(r'escolh', p)]
        self.assertTrue(ps, 'falta o usuário escolher uma direção')
        self.assertTrue(any(re.search(r'demais telas|outras telas|restante', p) for p in ps),
                        'falta completar as demais telas só na direção escolhida')

    def test_excecao_tela_existente_uma_direcao(self):
        ps = [p for p in com(r'já existe') if re.search(r'dire[çc]', p)]
        self.assertTrue(ps, 'tela existente não é declarada exceção às duas direções')


class TestRotaReact(unittest.TestCase):
    def test_mockup_react_vive_em_rota_do_app(self):
        self.assertTrue([p for p in com(r'\brota') if 'react' in p],
                        'falta o mockup React numa rota do app')

    def test_pagina_de_registro_com_prints_e_link_da_rota(self):
        ps = [p for p in com(r'\brota') if 'docs/vesta/mockups/' in p and 'index.html' in p]
        self.assertTrue(ps, 'falta a página de registro em docs/vesta/mockups/<data>-<feature>/index.html')
        self.assertTrue(any(all(t in p for t in ('print', 'celular', 'desktop', 'link')) for p in ps),
                        'a página de registro não traz prints celular e desktop e o link da rota')


class TestAutoverificacao(unittest.TestCase):
    def test_segue_verificacao_da_vesta_interface(self):
        ps = com(r'referencias/verificacao\.md')
        self.assertTrue(ps, 'autoverificação não aponta referencias/verificacao.md')
        self.assertTrue(any('vesta-interface' in p for p in ps),
                        'referencias/verificacao.md citado sem dizer que é da vesta-interface')

    def test_prints_celular_e_desktop(self):
        junto = ' '.join(com(r'\bprints?\b|screenshot'))
        for termo in ('celular', 'desktop'):
            self.assertIn(termo, junto, f'autoverificação sem print de {termo}')

    def test_no_maximo_3_rodadas(self):
        self.assertRegex(texto(), r'\b(3|três) rodadas', 'falta o limite de 3 rodadas')


class TestParada(unittest.TestCase):
    def test_parada_cita_diferenca_das_direcoes(self):
        self.assertRegex(secao('parada'), r'dire[çc]', 'parada sem a diferença entre as direções')

    def test_parada_cita_o_que_autoverificacao_corrigiu(self):
        self.assertRegex(secao('parada'), r'autoverifica|corrig',
                         'parada sem o que a autoverificação corrigiu')


if __name__ == '__main__':
    unittest.main()
