"""Testes do painel.py, etapa 1: dados da execução e das features.

Formatos escolhidos aqui (o plano deixou em aberto):
- feature: {"topico", "data", "spec", "research", "plano", "mockup", "grill"}; caminhos
  relativos à raiz do projeto (ex.: "docs/vesta/specs/2026-01-02-abc-design.md"), mockup é a
  pasta ("docs/vesta/mockups/2026-01-02-abc"); passo ausente é None.
- tempos: dict id da etapa -> minutos (float) ou None.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
for _k in [k for k in os.environ if k.startswith('GIT_')]:
    del os.environ[_k]

import painel  # noqa: E402
import vesta  # noqa: E402


def etapa(id_, status='pendente', tentativas=0, vermelho=None, commit=None, resultado=None):
    return {'id': id_, 'titulo': f't{id_}', 'tela': False, 'status': status,
            'provas': {'teste': {'vermelho': vermelho, 'resultado': resultado, 'commit': commit,
                                 'tentativas': tentativas}}}


def estado(etapas, espera=None, motivo=None, plano='docs/vesta/plans/2026-01-02-abc.md'):
    return {'versao': 1, 'plano': plano, 'teste': 'true', 'tela': [], 'mockup': None,
            'sessao': None, 'espera': espera, 'motivo': motivo,
            'bloqueios': {'seguidos': 0, 'assinatura': ''}, 'etapas': etapas}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = os.path.realpath(self.tmp.name)
        for args in (['init', '-q'], ['config', 'user.email', 't@t'], ['config', 'user.name', 't'],
                     ['commit', '-q', '--allow-empty', '-m', 'raiz']):
            subprocess.run(['git', *args], cwd=self.r, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def arquivo(self, rel, conteudo=''):
        p = os.path.join(self.r, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(conteudo)
        return p

    def commit_em(self, segundos):
        env = dict(os.environ, GIT_COMMITTER_DATE=f'{segundos} +0000',
                   GIT_AUTHOR_DATE=f'{segundos} +0000')
        subprocess.run(['git', 'commit', '-q', '--allow-empty', '-m', str(segundos)],
                       cwd=self.r, env=env, check=True)
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.r, capture_output=True,
                              text=True, check=True).stdout.strip()

    def gravar(self, e):
        vesta.gravar(self.r, e)


class Momento(unittest.TestCase):
    def test_sem_estado_e_vazio(self):
        self.assertEqual(painel.momento(None),
                         {'tipo': 'vazio', 'texto': 'Nenhuma execução neste projeto'})

    def test_esperando_plano(self):
        m = painel.momento(estado([etapa('1')], espera='plano'))
        self.assertEqual(m, {'tipo': 'plano', 'texto': 'Esperando aprovação do plano'})

    def test_pausada_cita_posicao_da_primeira_pendente_e_motivo(self):
        e = estado([etapa('a', 'feita'), etapa('b'), etapa('c')], espera='interrompida',
                   motivo='usuário pediu')
        self.assertEqual(painel.momento(e),
                         {'tipo': 'pausada', 'texto': 'Pausada na etapa 2 — usuário pediu'})

    def test_travada_cita_posicao_e_tentativas(self):
        n = vesta.LIMITE_TENTATIVAS
        e = estado([etapa('a', 'feita'), etapa('b', 'feita'), etapa('c', 'travada', tentativas=n)])
        self.assertEqual(painel.momento(e), {
            'tipo': 'travada', 'texto': f'Travada na etapa 3 depois de {n} tentativas'})

    def test_travada_vence_pendente(self):
        e = estado([etapa('a', 'travada', tentativas=vesta.LIMITE_TENTATIVAS), etapa('b')])
        self.assertEqual(painel.momento(e)['tipo'], 'travada')

    def test_concluida_conta_etapas(self):
        e = estado([etapa('a', 'feita'), etapa('b', 'feita'), etapa('c', 'feita')])
        self.assertEqual(painel.momento(e),
                         {'tipo': 'concluida', 'texto': 'Concluída — 3 de 3 etapas com prova'})

    def test_rodando_na_posicao_da_primeira_pendente(self):
        e = estado([etapa('x', 'feita'), etapa('y', 'feita'), etapa('z'), etapa('w')])
        self.assertEqual(painel.momento(e),
                         {'tipo': 'rodando', 'texto': 'Rodando na etapa 3 de 4'})


class Features(Base):
    def test_agrupa_os_passos_por_data_e_topico(self):
        self.arquivo('docs/vesta/specs/2026-01-02-abc-design.md', '# abc\n')
        self.arquivo('docs/vesta/research/2026-01-02-abc-research.md')
        self.arquivo('docs/vesta/plans/2026-01-02-abc.md')
        self.arquivo('docs/vesta/mockups/2026-01-02-abc/index.html')
        self.assertEqual(painel.features(self.r), [{
            'topico': 'abc', 'data': '2026-01-02',
            'spec': 'docs/vesta/specs/2026-01-02-abc-design.md',
            'research': 'docs/vesta/research/2026-01-02-abc-research.md',
            'plano': 'docs/vesta/plans/2026-01-02-abc.md',
            'mockup': 'docs/vesta/mockups/2026-01-02-abc',
            'grill': False}])

    def test_passo_sem_arquivo_e_none(self):
        self.arquivo('docs/vesta/plans/2026-01-02-abc.md')
        f, = painel.features(self.r)
        self.assertEqual((f['spec'], f['research'], f['mockup'], f['grill']),
                         (None, None, None, False))
        self.assertEqual(f['plano'], 'docs/vesta/plans/2026-01-02-abc.md')

    def test_grill_so_com_a_linha_exata_na_spec(self):
        self.arquivo('docs/vesta/specs/2026-01-02-sim-design.md', '# x\n\n## Decisões do grill\n- a\n')
        self.arquivo('docs/vesta/specs/2026-01-02-nao-design.md', '# x\nfalta o ## Decisões do grill aqui\n')
        g = {f['topico']: f['grill'] for f in painel.features(self.r)}
        self.assertEqual(g, {'sim': True, 'nao': False})

    def test_ordem_data_decrescente_depois_topico(self):
        for n in ('2026-01-01-zeta', '2026-03-01-beta', '2026-03-01-alfa', '2026-02-01-meio'):
            self.arquivo(f'docs/vesta/plans/{n}.md')
        self.assertEqual([(f['data'], f['topico']) for f in painel.features(self.r)], [
            ('2026-03-01', 'alfa'), ('2026-03-01', 'beta'), ('2026-02-01', 'meio'),
            ('2026-01-01', 'zeta')])

    def test_mesmo_topico_em_datas_diferentes_sao_features_diferentes(self):
        self.arquivo('docs/vesta/plans/2026-01-02-abc.md')
        self.arquivo('docs/vesta/specs/2026-01-05-abc-design.md')
        self.assertEqual(len(painel.features(self.r)), 2)

    def test_sem_docs_vesta_e_lista_vazia(self):
        self.assertEqual(painel.features(self.r), [])

    def test_nome_fora_do_padrao_e_ignorado(self):
        self.arquivo('docs/vesta/plans/README.md')
        self.arquivo('docs/vesta/specs/rascunho-design.md')
        self.arquivo('docs/vesta/plans/2026-01-02-abc.md')
        self.assertEqual([f['topico'] for f in painel.features(self.r)], ['abc'])


class FeatureDoPlano(Base):
    def setUp(self):
        super().setUp()
        self.arquivo('docs/vesta/plans/2026-01-02-abc.md')
        self.arquivo('docs/vesta/plans/2026-01-03-def.md')
        self.fs = painel.features(self.r)

    def test_acha_pelo_caminho_do_plano(self):
        f = painel.feature_do_plano(self.fs, 'docs/vesta/plans/2026-01-02-abc.md')
        self.assertEqual(f['topico'], 'abc')

    def test_chat_e_none(self):
        self.assertIsNone(painel.feature_do_plano(self.fs, 'chat'))

    def test_caminho_desconhecido_e_none(self):
        self.assertIsNone(painel.feature_do_plano(self.fs, 'docs/vesta/plans/2026-09-09-xyz.md'))


class TempoEtapas(Base):
    def test_minutos_entre_vermelho_e_prova_verde(self):
        v = self.commit_em(1_700_000_000)
        c = self.commit_em(1_700_000_000 + 90 * 60)
        e = estado([etapa('a', 'feita', vermelho=v, commit=c, resultado='verde'),
                    etapa('b', vermelho=v), etapa('c')])
        t = painel.tempo_etapas(self.r, e)
        self.assertEqual(t['a'], 90)
        self.assertIsNone(t['b'])
        self.assertIsNone(t['c'])

    def test_prova_vermelha_nao_conta(self):
        v = self.commit_em(1_700_000_000)
        c = self.commit_em(1_700_000_600)
        e = estado([etapa('a', vermelho=v, commit=c, resultado='vermelho')])
        self.assertIsNone(painel.tempo_etapas(self.r, e)['a'])


class DocSeguro(Base):
    def setUp(self):
        super().setUp()
        self.ok = self.arquivo('docs/vesta/specs/2026-01-02-abc-design.md')
        self.fora = self.arquivo('segredo.txt', 'x')

    def test_arquivo_dentro_devolve_absoluto(self):
        self.assertEqual(painel.doc_seguro(self.r, 'docs/vesta/specs/2026-01-02-abc-design.md'),
                         self.ok)

    def test_ponto_ponto_e_none(self):
        self.assertIsNone(painel.doc_seguro(self.r, 'docs/vesta/../../segredo.txt'))

    def test_absoluto_e_none(self):
        self.assertIsNone(painel.doc_seguro(self.r, self.fora))
        self.assertIsNone(painel.doc_seguro(self.r, self.ok))

    def test_link_para_fora_e_none(self):
        os.symlink(self.fora, os.path.join(self.r, 'docs/vesta/specs/link.md'))
        self.assertIsNone(painel.doc_seguro(self.r, 'docs/vesta/specs/link.md'))

    def test_inexistente_e_none(self):
        self.assertIsNone(painel.doc_seguro(self.r, 'docs/vesta/specs/nao-existe.md'))

    def test_pasta_e_none(self):
        self.assertIsNone(painel.doc_seguro(self.r, 'docs/vesta/specs'))

    def test_prefixo_parecido_fora_e_none(self):
        self.arquivo('docs/vesta-x/a.md')
        self.assertIsNone(painel.doc_seguro(self.r, 'docs/vesta-x/a.md'))


class Dados(Base):
    def test_sem_execucao(self):
        self.arquivo('docs/vesta/plans/2026-01-01-velho.md')
        self.arquivo('docs/vesta/plans/2026-02-01-novo.md')
        d = painel.dados(self.r)
        self.assertEqual(d['projeto'], os.path.basename(self.r))
        self.assertEqual(d['momento']['tipo'], 'vazio')
        self.assertIsNone(d['estado'])
        self.assertIsNone(d['erro'])
        self.assertEqual(len(d['features']), 2)
        self.assertEqual(d['atual']['topico'], 'novo')
        self.assertEqual(d['tempos'], {})

    def test_com_execucao_atual_e_a_feature_do_plano(self):
        self.arquivo('docs/vesta/plans/2026-01-01-velho.md')
        self.arquivo('docs/vesta/plans/2026-02-01-novo.md')
        e = estado([etapa('1')], plano='docs/vesta/plans/2026-01-01-velho.md')
        self.gravar(e)
        d = painel.dados(self.r)
        self.assertEqual(d['estado'], e)
        self.assertEqual(d['momento']['tipo'], 'rodando')
        self.assertEqual(d['atual']['topico'], 'velho')
        self.assertEqual(d['tempos'], {'1': None})

    def test_plano_de_chat_cai_na_mais_recente(self):
        self.arquivo('docs/vesta/plans/2026-02-01-novo.md')
        self.gravar(estado([etapa('1')], plano='chat'))
        self.assertEqual(painel.dados(self.r)['atual']['topico'], 'novo')

    def test_sem_features_atual_e_none(self):
        self.assertIsNone(painel.dados(self.r)['atual'])

    def test_estado_ilegivel_nao_levanta(self):
        self.arquivo('.claude/vesta/estado.json', '{quebrado')
        d = painel.dados(self.r)
        self.assertEqual(d['momento'], {'tipo': 'ilegivel', 'texto': 'Estado ilegível'})
        self.assertIsInstance(d['erro'], str)
        self.assertTrue(d['erro'])
        self.assertIsNone(d['estado'])

    def test_estado_fora_do_formato_tambem_e_ilegivel(self):
        self.arquivo('.claude/vesta/estado.json', json.dumps({'etapas': []}))
        self.assertEqual(painel.dados(self.r)['momento']['tipo'], 'ilegivel')


if __name__ == '__main__':
    unittest.main()
