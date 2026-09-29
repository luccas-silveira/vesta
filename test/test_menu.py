"""Etapa 7: toda pergunta da Vesta ao usuário vai por menu (AskUserQuestion).

Cada ponto de pergunta (A11 do dossiê de 2026-09-28) é ancorado num trecho do arquivo:
seção pelo título e, dentro dela, o parágrafo ou item de lista que traz a palavra-chave.
Esse trecho precisa citar o menu (`AskUserQuestion` ou "menu").
"""
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(RAIZ, 'skill')
ARQUIVOS = ['SKILL.md', 'spec.md', 'grill.md', 'mockup.md', 'plano.md', 'execucao.md']

MENU = r'askuserquestion|\bmenus?\b'
TODA_PERGUNTA = (r'\b(toda|todas as|cada|qualquer) (pergunta|decisão|escolha)'
                 r'|\bperguntas? (ao|para o|feitas? ao) usuário')
RECOMENDADA_PRIMEIRO = (r'recomend[^.]*\b(em primeiro|primeira|primeiro lugar|no topo|à frente)'
                        r'|\b(em primeiro|primeira|primeiro lugar|no topo)\b[^.]*recomend')
LIVRE = (r'(resposta|texto) livre[^.]*\baceit|\baceit[^.]*(resposta|texto) livre'
         r'|"outro"[^.]*\baceit|\baceit[^.]*"outro"')
PROIBIDAS = ['pare até o sim explícito', 'espere o sim', 'peça ao usuário que revise']


def bruto(nome):
    with open(os.path.join(SKILL, nome)) as f:
        return f.read()


def texto(nome):
    return bruto(nome).lower()


def paragrafos(t):
    return [p for p in re.split(r'\n\s*\n', t) if p.strip()]


def trechos(t):
    """Parágrafos, com cada item de lista (numerada ou com hífen) como trecho próprio."""
    out = []
    for p in paragrafos(t):
        out += [x for x in re.split(r'\n(?=\s*(?:\d+\.|[-*])\s)', p) if x.strip()]
    return out


def secao(nome, titulo):
    """Corpo da seção ##/### cujo título contém `titulo`, até o próximo ##/###."""
    for bloco in re.split(r'^#{2,3} ', texto(nome), flags=re.M)[1:]:
        if titulo in bloco.split('\n', 1)[0]:
            return bloco.split('\n', 1)[1] if '\n' in bloco else ''
    return ''


def preambulo(nome):
    return re.split(r'^## ', texto(nome), flags=re.M)[0]


def cita_menu(t):
    return re.search(MENU, t) is not None


class Ancora(unittest.TestCase):
    def ancorado(self, corpo, chave, onde, excluir=None):
        """Algum trecho de `corpo` que casa `chave` (e não `excluir`) cita o menu."""
        self.assertTrue(corpo, f'{onde}: seção não encontrada')
        ts = [t for t in trechos(corpo) if re.search(chave, t)
              and not (excluir and re.search(excluir, t))]
        self.assertTrue(ts, f'{onde}: trecho com /{chave}/ não encontrado')
        self.assertTrue(any(cita_menu(t) for t in ts),
                        f'{onde}: o trecho com /{chave}/ não cita o menu (AskUserQuestion)')

    def parada(self, corpo, onde, decisao, excluir=None):
        """A mensagem de cinco linhas continua; o menu está nela ou no trecho logo depois."""
        ts = trechos(corpo)
        i = next((k for k, t in enumerate(ts) if 'cinco linhas' in t), None)
        self.assertIsNotNone(i, f'{onde}: a mensagem de cinco linhas sumiu')
        vizinhos = [t for t in ts[i:i + 2] if not (excluir and re.search(excluir, t))]
        self.assertTrue(any(cita_menu(t) and re.search(decisao, t) for t in vizinhos),
                        f'{onde}: a decisão da parada não vira menu logo depois da mensagem')


class TestRegraGeral(unittest.TestCase):
    """Cada arquivo diz a regra inteira num parágrafo: toda pergunta ao usuário pelo
    AskUserQuestion, recomendada primeiro marcada "(Recomendado)", resposta livre aceita."""

    def test_cada_arquivo_diz_a_regra(self):
        for nome in ARQUIVOS:
            with self.subTest(arquivo=nome):
                self.assertTrue('AskUserQuestion' in bruto(nome), 'falta o nome AskUserQuestion com a caixa certa')
                ps = [p for p in paragrafos(texto(nome))
                      if 'askuserquestion' in p and re.search(TODA_PERGUNTA, p)]
                self.assertTrue(ps, 'falta a regra: toda pergunta ao usuário vai pelo AskUserQuestion')
                ps = [p for p in ps if '(recomendado)' in p and re.search(RECOMENDADA_PRIMEIRO, p)]
                self.assertTrue(ps, 'a regra não diz recomendada em primeiro, marcada "(Recomendado)"')
                ps = [p for p in ps if re.search(LIVRE, p)
                      and not re.search(r'não aceit|sem (resposta|texto) livre', p)]
                self.assertTrue(ps, 'a regra não diz que a resposta livre é aceita')


class TestSemPerguntaSolta(unittest.TestCase):
    def test_frases_de_espera_so_com_menu_na_mesma_frase(self):
        for nome in ARQUIVOS:
            t = re.sub(r'\s+', ' ', texto(nome))
            for frase in re.split(r'(?<=[.!?])\s+', t):
                for proibida in PROIBIDAS:
                    if proibida in frase:
                        with self.subTest(arquivo=nome, frase=proibida):
                            self.assertTrue(cita_menu(frase), f'"{frase.strip()}" sem citar o menu')


class TestSpec(Ancora):
    def test_classificacao(self):
        self.ancorado(secao('spec.md', 'classifique'), r'classifica', 'spec.md ## Classifique',
                      excluir=r'sondagem')

    def test_confirmacao_da_sondagem(self):
        self.ancorado(secao('spec.md', 'classifique'), r'sondagem', 'spec.md ## Classifique, item Sondagem')

    def test_pergunta_de_proposito(self):
        self.ancorado(secao('spec.md', 'entenda'), r'propósito', 'spec.md ## Entenda a intenção, item 1')

    def test_confirmacao_do_entendimento(self):
        self.ancorado(secao('spec.md', 'entenda'), r'escreva de volta|o que entendeu',
                      'spec.md ## Entenda a intenção, item 2')

    def test_uma_pergunta_por_vez(self):
        self.ancorado(secao('spec.md', 'entenda'), r'uma pergunta por|múltipla escolha',
                      'spec.md ## Entenda a intenção, "Uma pergunta por mensagem"')

    def test_aprovacao_do_caminho_pequeno(self):
        self.ancorado(secao('spec.md', 'caminho pequeno'), r'design curto',
                      'spec.md ## Caminho pequeno, 1º parágrafo')

    def test_perguntas_do_estrutural(self):
        self.ancorado(secao('spec.md', 'caminho estrutural'), r'propósito',
                      'spec.md ## Caminho estrutural, item 1')

    def test_abordagens(self):
        self.ancorado(secao('spec.md', 'caminho estrutural'), r'abordage',
                      'spec.md ## Caminho estrutural, item 2')

    def test_cada_secao_do_design(self):
        self.ancorado(secao('spec.md', 'caminho estrutural'), r'cada seção|design em seç',
                      'spec.md ## Caminho estrutural, item 3')

    def test_revisao_da_spec(self):
        self.ancorado(secao('spec.md', 'caminho estrutural'), r'revis',
                      'spec.md ## Caminho estrutural, item 7')


class TestGrill(Ancora):
    def test_primeira_mensagem_e_pergunta(self):
        self.ancorado(preambulo('grill.md'), r'pergunta', 'grill.md, abertura antes de ## O interrogatório')

    def test_cada_pergunta_com_recomendada(self):
        self.ancorado(secao('grill.md', 'interrogat'), r'recomendad', 'grill.md ## O interrogatório')

    def test_uma_de_cada_vez(self):
        self.ancorado(secao('grill.md', 'interrogat'), r'uma de cada vez', 'grill.md ## O interrogatório')

    def test_exemplo_certo_e_menu(self):
        corpo = secao('grill.md', 'fila é o dossiê')
        self.assertIn('certo:', corpo, 'grill.md ## A fila é o dossiê: o exemplo "Certo:" sumiu')
        depois = corpo.split('certo:', 1)[1]
        self.assertTrue(cita_menu(depois) and '(recomendado)' in depois,
                        'grill.md: o exemplo "Certo" não mostra a pergunta como menu com "(Recomendado)"')

    def test_fim_do_grill(self):
        self.ancorado(secao('grill.md', 'fim'), r'confirma', 'grill.md ## Fim')


class TestMockup(Ancora):
    def test_bifurcacao_oferecida_por_menu(self):
        corpo = secao('mockup.md', 'vesta-interface')
        oferta = (r'(ofere\w+|pergunt\w+)[^.:]*(askuserquestion|\bmenu\b)[^.]*bifurca'
                  r'|bifurca[^.:(]*(askuserquestion|\bmenu\b)')
        self.assertTrue(re.search(oferta, re.sub(r'\s+', ' ', corpo)),
                        'mockup.md ## Design: a escolha com/sem questionário não é oferecida por menu')

    def test_copy_faltando(self):
        self.ancorado(secao('mockup.md', 'vesta-interface'), r'faltando texto|inventa copy',
                      'mockup.md ## Design, parágrafo "Faltando texto"')

    def test_aprovacao_do_mockup(self):
        self.parada(secao('mockup.md', 'parada do mockup'), 'mockup.md ## Parada do mockup', r'aprov')

    def test_mudanca_pedida_no_mockup(self):
        self.ancorado(secao('mockup.md', 'parada do mockup'), r'mudança pedida',
                      'mockup.md ## Parada do mockup, "Mudança pedida"')


class TestPlano(Ancora):
    def test_parada_1(self):
        self.parada(secao('plano.md', 'parada 1'), 'plano.md ## Parada 1', r'aprov', excluir=r'stash')

    def test_commit_ou_stash(self):
        self.ancorado(secao('plano.md', 'parada 1'), r'stash', 'plano.md ## Parada 1, commit/stash')


class TestExecucao(Ancora):
    def test_parada_2(self):
        self.parada(secao('execucao.md', 'parada 2'), 'execucao.md ## Parada 2',
                    r'aprov|ajust|decis|decid|escolh')

    def test_ajuste(self):
        self.ancorado(secao('execucao.md', 'parada 2'), r'ajuste pedido', 'execucao.md ## Parada 2, "Ajuste pedido"')

    def test_fechamento(self):
        self.ancorado(secao('execucao.md', 'parada 2'), r'fechar', 'execucao.md ## Parada 2, fechamento')


class TestSkill(Ancora):
    def test_pergunta_entre_fases(self):
        self.ancorado(preambulo('SKILL.md'), r'pergunta', 'SKILL.md, abertura ("volta a escrever quando tiver pergunta")')

    def test_aprovacao_do_mockup(self):
        self.ancorado(secao('SKILL.md', 'fase 4'), r'aprova o mockup', 'SKILL.md ## Fase 4, mockup')

    def test_parada_1(self):
        self.ancorado(secao('SKILL.md', 'fase 4'), r'parada 1', 'SKILL.md ## Fase 4, parada 1')

    def test_parada_2(self):
        self.ancorado(secao('SKILL.md', 'fase 5'), r'parada 2', 'SKILL.md ## Fase 5, parada 2')

    def test_mensagens_das_paradas(self):
        self.parada(secao('SKILL.md', 'mensagens das paradas'), 'SKILL.md ## As mensagens das paradas',
                    r'aprov|decis|decid|escolh|parada')


if __name__ == '__main__':
    unittest.main()
