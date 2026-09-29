"""Testes do painel.py, etapa 1: dados da execução e das features.

Formatos escolhidos aqui (o plano deixou em aberto):
- feature: {"topico", "data", "spec", "research", "plano", "mockup", "grill"}; caminhos
  relativos à raiz do projeto (ex.: "docs/vesta/specs/2026-01-02-abc-design.md"), mockup é a
  pasta ("docs/vesta/mockups/2026-01-02-abc"); passo ausente é None.
- tempos: dict id da etapa -> minutos (float) ou None.
"""
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from unittest import mock

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

    def test_traz_o_caminho_com_home_abreviado(self):
        casa, nome = os.path.split(self.r)
        with mock.patch.dict(os.environ, {'HOME': casa}):
            d = painel.dados(self.r)
        self.assertIn('~/' + nome, d.values())
        self.assertNotIn(self.r, d.values())

    def test_caminho_fora_do_home_fica_inteiro(self):
        with mock.patch.dict(os.environ, {'HOME': '/nao/existe'}):
            self.assertIn(self.r, painel.dados(self.r).values())

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


# Etapa 2 — formatos escolhidos: "inicio"/"fim" são a string "timestamp" exata da primeira e da
# última linha do .jsonl que tem timestamp (qualquer type); "duracao_s" é int (segundos entre elas).
# "requests" é int; "entrada" segue a ordem de primeira aparição do requestId; "ferramentas" em
# empate de contagem vai por nome crescente.
def linha_assistant(rid, ts, i=0, cr=0, cc=0, o=0, ferramentas=()):
    return {'type': 'assistant', 'requestId': rid, 'timestamp': ts, 'message': {
        'usage': {'input_tokens': i, 'cache_read_input_tokens': cr,
                  'cache_creation_input_tokens': cc, 'output_tokens': o},
        'content': [{'type': 'tool_use', 'name': n, 'id': 'x', 'input': {}} for n in ferramentas]}}


class SessaoBase(Base):
    def setUp(self):
        super().setUp()
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        p = mock.patch.dict(os.environ, {'HOME': os.path.realpath(self.home.name)})
        p.start()
        self.addCleanup(p.stop)
        self.proj = os.path.join(os.path.realpath(self.home.name), '.claude', 'projects',
                                 re.sub(r'[^A-Za-z0-9]', '-', self.r))

    def jsonl(self, nome, linhas, mtime=None):
        os.makedirs(self.proj, exist_ok=True)
        p = os.path.join(self.proj, nome)
        with open(p, 'w') as f:
            for l in linhas:
                f.write((l if isinstance(l, str) else json.dumps(l)) + '\n')
        if mtime is not None:
            os.utime(p, (mtime, mtime))
        return p


class PastaSessoes(SessaoBase):
    def test_home_do_ambiente_e_raiz_com_tudo_que_nao_e_letra_ou_digito_trocado(self):
        h = os.path.realpath(self.home.name)
        self.assertEqual(painel.pasta_sessoes('/a/b.c/d_e'),
                         os.path.join(h, '.claude', 'projects', '-a-b-c-d-e'))


class Sessao(SessaoBase):
    def test_resumo_completo(self):
        self.jsonl('s.jsonl', [
            {'type': 'user', 'timestamp': '2026-01-01T10:00:00.000Z', 'message': {}},
            linha_assistant('r1', '2026-01-01T10:00:05.000Z', i=10, cr=100, cc=5, o=7,
                            ferramentas=['Read', 'mcp__graft__graft_find_code']),
            linha_assistant('r2', '2026-01-01T10:01:40.000Z', i=1, cr=200, cc=0, o=3,
                            ferramentas=['Read', 'Bash', 'Read']),
        ])
        self.assertEqual(painel.sessao(self.r), {
            'inicio': '2026-01-01T10:00:00.000Z', 'fim': '2026-01-01T10:01:40.000Z',
            'duracao_s': 100, 'requests': 2, 'entrada': [115, 201], 'saida': 10,
            'ferramentas': [['Read', 3], ['Bash', 1], ['graft_find_code', 1]],
            'contexto': 201, 'janela': 200000,
            'ritmo': [0, 0, 1] + [0] * 44 + [1]})

    def test_mesmo_request_id_conta_uma_request_com_o_ultimo_usage(self):
        self.jsonl('s.jsonl', [
            linha_assistant('r1', '2026-01-01T10:00:00Z', i=1, cr=10, o=2, ferramentas=['Read']),
            linha_assistant('r1', '2026-01-01T10:00:01Z', i=1, cr=10, o=9, ferramentas=['Read']),
            linha_assistant('r2', '2026-01-01T10:00:02Z', i=3, o=1),
        ])
        s = painel.sessao(self.r)
        self.assertEqual((s['requests'], s['entrada'], s['saida']), (2, [11, 3], 10))
        self.assertEqual(s['ferramentas'], [['Read', 2]])
        self.assertEqual(s['contexto'], 3)

    def test_janela_de_um_milhao_quando_passa_de_200k(self):
        self.jsonl('s.jsonl', [linha_assistant('r1', '2026-01-01T10:00:00Z', cr=200001),
                               linha_assistant('r2', '2026-01-01T10:00:01Z', i=5)])
        self.assertEqual(painel.sessao(self.r)['janela'], 1000000)

    def test_exatamente_200k_fica_em_200k(self):
        self.jsonl('s.jsonl', [linha_assistant('r1', '2026-01-01T10:00:00Z', cr=200000)])
        self.assertEqual(painel.sessao(self.r)['janela'], 200000)

    def test_ignora_sessao_do_sdk(self):
        pasta = painel.pasta_sessoes(self.r)
        os.makedirs(pasta, exist_ok=True)
        cli = os.path.join(pasta, 'a.jsonl'); sdk = os.path.join(pasta, 'b.jsonl')
        with open(cli, 'w') as f:
            f.write(json.dumps(dict(linha_assistant('r1', '2026-01-01T00:00:00Z', i=10), entrypoint='cli')) + '\n')
        with open(sdk, 'w') as f:
            f.write(json.dumps(dict(linha_assistant('r9', '2026-01-01T00:00:00Z', i=99), entrypoint='sdk-py')) + '\n')
        os.utime(cli, (1, 1)); os.utime(sdk, (2, 2))
        self.assertEqual(painel.sessao(self.r)['entrada'], [10])

    def test_le_o_jsonl_modificado_por_ultimo(self):
        self.jsonl('velho.jsonl', [linha_assistant('r', '2026-01-01T10:00:00Z', i=1)], 1_000)
        self.jsonl('novo.jsonl', [linha_assistant('r', '2026-01-02T10:00:00Z', i=2)], 2_000)
        self.jsonl('b.jsonl', [linha_assistant('r', '2026-01-03T10:00:00Z', i=3)], 1_500)
        self.assertEqual(painel.sessao(self.r)['entrada'], [2])

    def test_linha_que_nao_e_json_e_pulada(self):
        self.jsonl('s.jsonl', ['{quebrado', linha_assistant('r1', '2026-01-01T10:00:00Z', i=4), ''])
        self.assertEqual(painel.sessao(self.r)['entrada'], [4])

    def test_pasta_ausente_e_none(self):
        self.assertIsNone(painel.sessao(self.r))

    def test_sem_jsonl_e_none(self):
        os.makedirs(self.proj)
        with open(os.path.join(self.proj, 'x.txt'), 'w') as f:
            f.write(json.dumps(linha_assistant('r', '2026-01-01T10:00:00Z', i=1)))
        self.assertIsNone(painel.sessao(self.r))

    def test_sem_usage_e_none(self):
        self.jsonl('s.jsonl', [{'type': 'user', 'timestamp': '2026-01-01T10:00:00Z', 'message': {}},
                               '{quebrado'])
        self.assertIsNone(painel.sessao(self.r))


class DadosSessao(SessaoBase):
    def test_dados_traz_a_sessao(self):
        self.jsonl('s.jsonl', [linha_assistant('r1', '2026-01-01T10:00:00Z', i=7)])
        self.assertEqual(painel.dados(self.r)['sessao'], painel.sessao(self.r))
        self.assertEqual(painel.dados(self.r)['sessao']['entrada'], [7])

    def test_dados_sem_sessao_e_none(self):
        d = painel.dados(self.r)
        self.assertIn('sessao', d)
        self.assertIsNone(d['sessao'])


def porta_livre():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class ServidorBase(Base):
    PRAZOS = {}  # VESTA_PRAZO_* passados ao processo do servidor; vazio = prazos de verdade

    def setUp(self):
        super().setUp()
        self.arquivo('docs/vesta/specs/x.md', '# Spec X\ncorpo')
        self.porta = porta_livre()
        env = {k: v for k, v in os.environ.items() if not k.startswith('VESTA_PRAZO_')}
        env.update(self.PRAZOS)
        self.proc = subprocess.Popen([sys.executable, os.path.join(AQUI, 'painel.py'), 'servir',
                                      self.r, str(self.porta)], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(self.proc.wait)
        self.addCleanup(self.proc.kill)
        fim = time.time() + 5
        while True:
            try:
                socket.create_connection(('127.0.0.1', self.porta), timeout=0.2).close()
                break
            except OSError:
                if time.time() > fim or self.proc.poll() is not None:
                    self.fail('servidor não abriu a porta')
                time.sleep(0.05)

    def get(self, caminho):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{self.porta}{caminho}', timeout=5) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Content-Type', ''), e.read()


class Servidor(ServidorBase):
    def test_estado_devolve_dados_da_raiz(self):
        st, _, corpo = self.get('/estado')
        self.assertEqual(st, 200)
        d = json.loads(corpo)
        d.pop('perguntas', None)  # vem da memória do servidor, não de dados(r)
        self.assertEqual(d, json.loads(json.dumps(painel.dados(self.r))))

    def test_doc_devolve_texto_do_arquivo(self):
        st, _, corpo = self.get('/doc?caminho=docs/vesta/specs/x.md')
        self.assertEqual((st, corpo.decode()), (200, '# Spec X\ncorpo'))

    def test_doc_recusado_por_doc_seguro_e_404(self):
        segredo = os.path.join(os.path.dirname(self.r), 'segredo-painel.txt')
        for c in ('docs/vesta/../../segredo-painel.txt', urllib.parse.quote(segredo),
                  'docs/vesta/specs/nao-existe.md', 'docs/vesta/specs'):
            with self.subTest(c):
                self.assertEqual(self.get('/doc?caminho=' + c)[0], 404)

    def test_raiz_serve_painel_html(self):
        st, tipo, corpo = self.get('/')
        self.assertEqual(st, 200)
        self.assertTrue(tipo.startswith('text/html'), tipo)
        with open(os.path.join(AQUI, 'painel.html'), 'rb') as f:
            self.assertEqual(corpo, f.read())

    def _pagina(self):
        return self.get('/')[2].decode()

    def test_pagina_tem_os_oito_widgets_e_novos(self):
        h = self._pagina()
        for i in ('dias', 'seq-bar', 'radar', 'onda', 'odo', 'prov', 'rel', 'bat'):
            with self.subTest(i):
                self.assertIn('id="%s"' % i, h)
        self.assertIn('function novos', h)

    def test_render_chama_novos(self):
        # definição + pelo menos uma chamada (em render)
        self.assertGreaterEqual(self._pagina().count('novos('), 2)

    def test_pagina_usa_o_dia_de_hoje_e_nao_o_do_mockup(self):
        h = self._pagina()
        self.assertNotIn('2026-09-29T12:00:00', h)
        self.assertRegex(h, r'HOJE\s*=\s*new Date\(\)')

    def test_pagina_sem_dados_de_exemplo_do_mockup(self):
        h = self._pagina()
        self.assertNotIn('BASE.', h)
        self.assertNotIn('DOCS=', h)

    def test_widgets_na_coluna_certa(self):
        h = self._pagina()
        esq = h.index('id="pontos"')
        for i in ('dias', 'seq-bar', 'radar'):
            with self.subTest(i):
                self.assertGreater(h.index('id="%s"' % i), esq)
        dir_ = h.index('id="ferr"')
        for i in ('onda', 'odo', 'prov', 'rel', 'bat'):
            with self.subTest(i):
                self.assertGreater(h.index('id="%s"' % i), dir_)

    def test_widgets_tem_elemento_de_estado_vazio(self):
        h = self._pagina()
        for i in ('dias-v', 'seq-w-v', 'radar-v', 'rel-v', 'prov-w-v'):
            with self.subTest(i):
                self.assertIn('id="%s"' % i, h)

    def test_marked_js(self):
        st, _, corpo = self.get('/marked.js')
        self.assertEqual(st, 200)
        with open(os.path.join(AQUI, 'marked.js'), 'rb') as f:
            self.assertEqual(corpo, f.read())

    def test_doc_html_e_text_html_e_md_nao(self):
        self.arquivo('docs/vesta/mockups/m/index.html', '<p>oi</p>')
        st, tipo, corpo = self.get('/doc?caminho=docs/vesta/mockups/m/index.html')
        self.assertEqual((st, corpo), (200, b'<p>oi</p>'))
        self.assertTrue(tipo.startswith('text/html'), tipo)
        self.assertFalse(self.get('/doc?caminho=docs/vesta/specs/x.md')[1].startswith('text/html'))

    def test_outra_rota_e_404(self):
        for c in ('/nada', '/painel.py', '/painel.html/x', '/estado/x', '/../painel.py'):
            with self.subTest(c):
                self.assertEqual(self.get(c)[0], 404)

    def test_quem_identifica_a_raiz(self):
        st, _, corpo = self.get('/quem')
        self.assertEqual((st, corpo.decode().strip()), (200, f'vesta-painel {self.r}'))

    def test_escuta_so_em_127_0_0_1(self):
        ips = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
               if not ip.startswith('127.')]
        for ip in ips:
            with self.subTest(ip), self.assertRaises(OSError):
                socket.create_connection((ip, self.porta), timeout=0.5).close()

    def test_porta_ocupada_sai_com_zero_sem_erro(self):
        p = subprocess.run([sys.executable, os.path.join(AQUI, 'painel.py'), 'servir', self.r,
                            str(self.porta)], capture_output=True, text=True, timeout=5)
        self.assertEqual((p.returncode, p.stderr), (0, ''))
        self.assertEqual(self.get('/quem')[0], 200)


def matar_porta(n):
    """Mata quem escuta em tcp:n (o painel sobe em sessão própria, fora do alcance do teste)."""
    out = subprocess.run(['lsof', '-ti', f'tcp:{n}', '-sTCP:LISTEN'], capture_output=True,
                         text=True).stdout.split()
    for pid in out:
        subprocess.run(['kill', pid], capture_output=True)
    return out


def escuta(n):
    try:
        socket.create_connection(('127.0.0.1', n), timeout=0.3).close()
        return True
    except OSError:
        return False


class PainelBase(Base):
    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: [matar_porta(4700 + i) for i in range(100)
                                 if f'vesta-painel {self.r}' in quem(4700 + i)])

    def url(self, n):
        return f'http://localhost:{n}'


class Subir(PainelBase):
    def test_porta_estavel_e_na_faixa(self):
        self.assertEqual(painel.porta(self.r), painel.porta(self.r))
        ps = {painel.porta(f'/tmp/projeto-{i}') for i in range(50)}
        self.assertTrue(all(4700 <= p <= 4799 for p in ps), ps)
        self.assertGreater(len(ps), 5)  # deriva do caminho, não é constante

    def test_sem_vesta_nao_sobe(self):
        self.assertIsNone(painel.subir(self.r))
        self.assertNotIn(f'vesta-painel {self.r}', quem(painel.porta(self.r)))

    def test_forcar_sobe_sem_vesta_e_nao_cria_pasta(self):
        u = painel.subir(self.r, forcar=True)
        self.assertIsNotNone(u)
        self.assertEqual(quem(int(u.rsplit(':', 1)[1])), f'vesta-painel {self.r}')
        self.assertEqual(painel.achar(self.r), u)
        time.sleep(0.3)
        self.assertEqual(sorted(os.listdir(self.r)), ['.git'])

    def test_forcar_falso_continua_recusando(self):
        self.assertIsNone(painel.subir(self.r, forcar=False))
        self.assertEqual([i for i in range(100) if f'vesta-painel {self.r}' in quem(4700 + i)], [])

    def test_com_docs_vesta_sobe_e_responde_quem(self):
        self.arquivo('docs/vesta/specs/x.md', 'x')
        n = painel.porta(self.r)
        if escuta(n):
            self.skipTest(f'porta {n} já ocupada nesta máquina')
        self.assertEqual(painel.subir(self.r), self.url(n))
        self.assertEqual(quem(n), f'vesta-painel {self.r}')

    def test_so_claude_vesta_tambem_sobe(self):
        os.makedirs(os.path.join(self.r, '.claude', 'vesta'))
        u = painel.subir(self.r)
        self.assertIsNotNone(u)
        self.assertEqual(quem(int(u.rsplit(':', 1)[1])), f'vesta-painel {self.r}')

    def test_segunda_chamada_reusa_o_mesmo_processo(self):
        self.arquivo('docs/vesta/specs/x.md', 'x')
        u = painel.subir(self.r)
        n = int(u.rsplit(':', 1)[1])
        pids = subprocess.run(['lsof', '-ti', f'tcp:{n}', '-sTCP:LISTEN'], capture_output=True,
                              text=True).stdout.split()
        self.assertEqual(painel.subir(self.r), u)
        time.sleep(0.3)
        depois = subprocess.run(['lsof', '-ti', f'tcp:{n}', '-sTCP:LISTEN'], capture_output=True,
                                text=True).stdout.split()
        self.assertEqual(depois, pids)
        vivos = [i for i in range(100) if f'vesta-painel {self.r}' in quem(4700 + i)]
        self.assertEqual(len(vivos), 1)

    def test_porta_ocupada_por_outro_tenta_a_seguinte(self):
        self.arquivo('docs/vesta/specs/x.md', 'x')
        n = painel.porta(self.r)
        prox = 4700 + (n - 4700 + 1) % 100
        if escuta(n) or escuta(prox):
            self.skipTest('portas já ocupadas nesta máquina')
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', n))
        s.listen()
        self.addCleanup(s.close)
        self.assertEqual(painel.subir(self.r), self.url(prox))
        self.assertEqual(quem(prox), f'vesta-painel {self.r}')


def quem(n):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{n}/quem', timeout=0.5) as r:
            return r.read().decode().strip()
    except Exception:
        return ''


class HookInicioPainel(PainelBase):
    def test_sem_aviso_devolve_linha_do_painel(self):
        self.arquivo('docs/vesta/specs/x.md', 'x')
        out = vesta.hook_inicio({'cwd': self.r, 'session_id': 's1'})
        ctx = out['hookSpecificOutput']['additionalContext']
        m = re.search(r'Painel deste projeto: http://localhost:(\d+)', ctx)
        self.assertTrue(m, ctx)
        self.assertEqual(quem(int(m.group(1))), f'vesta-painel {self.r}')

    def test_com_aviso_linha_vai_junto(self):
        self.arquivo('.claude/vesta/estado.json',
                     json.dumps(dict(estado([etapa('1')]), sessao='outra')))
        out = vesta.hook_inicio({'cwd': self.r, 'session_id': 's1'})
        ctx = out['hookSpecificOutput']['additionalContext']
        self.assertIn('outra sessão', ctx)
        self.assertRegex(ctx, r'Painel deste projeto: http://localhost:\d+')

    def test_sem_vesta_continua_none(self):
        self.assertIsNone(vesta.hook_inicio({'cwd': self.r, 'session_id': 's1'}))

    def test_falha_do_painel_nao_derruba_o_aviso(self):
        self.arquivo('.claude/vesta/estado.json',
                     json.dumps(dict(estado([etapa('1')]), sessao='outra')))
        with mock.patch.object(painel, 'subir', side_effect=RuntimeError('x')):
            out = vesta.hook_inicio({'cwd': self.r, 'session_id': 's1'})
        self.assertIn('outra sessão', out['systemMessage'])
        self.assertNotIn('Painel deste projeto', out['hookSpecificOutput']['additionalContext'])

    def test_system_message_mostra_painel_do_projeto(self):
        self.arquivo('docs/vesta/specs/x.md', 'x')
        out = vesta.hook_inicio({'cwd': self.r, 'session_id': 's1'})
        nome = os.path.basename(self.r)
        m = re.search(rf'vesta: painel de {re.escape(nome)} em http://localhost:(\d+)', out['systemMessage'])
        self.assertTrue(m, out['systemMessage'])
        self.assertEqual(quem(int(m.group(1))), f'vesta-painel {self.r}')
        self.assertIn(f'http://localhost:{m.group(1)}', out['hookSpecificOutput']['additionalContext'])

    def test_com_aviso_system_message_tem_aviso_e_painel(self):
        self.arquivo('.claude/vesta/estado.json',
                     json.dumps(dict(estado([etapa('1')]), sessao='outra')))
        out = vesta.hook_inicio({'cwd': self.r, 'session_id': 's1'})
        msg = out['systemMessage']
        self.assertIn('outra sessão', msg)
        self.assertIn(f'painel de {os.path.basename(self.r)} em http://localhost:', msg)
        self.assertRegex(out['hookSpecificOutput']['additionalContext'], r'http://localhost:\d+')


class ComandoPainel(PainelBase):
    """`vesta.py painel` sobe, abre no navegador (`open`, falso no PATH) e imprime a url."""

    def setUp(self):
        super().setUp()
        self.bin = tempfile.TemporaryDirectory()
        self.addCleanup(self.bin.cleanup)
        self.registro = os.path.join(self.bin.name, 'abertos')
        falso = os.path.join(self.bin.name, 'open')
        with open(falso, 'w') as f:
            f.write(f'#!/bin/sh\necho "$@" >> {self.registro}\n')
        os.chmod(falso, 0o755)

    def rodar(self):
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
        env['PATH'] = self.bin.name + os.pathsep + env.get('PATH', '')
        return subprocess.run([sys.executable, os.path.join(AQUI, 'vesta.py'), 'painel'],
                              cwd=self.r, env=env, capture_output=True, text=True, timeout=30)

    def abertos(self):
        if not os.path.exists(self.registro):
            return []
        with open(self.registro) as f:
            return f.read().split()

    def test_sobe_abre_e_imprime_a_url(self):
        self.arquivo('docs/vesta/specs/x.md', 'x')
        p = self.rodar()
        self.assertEqual(p.returncode, 0, p.stderr)
        m = re.search(r'http://localhost:(\d+)', p.stdout)
        self.assertTrue(m, p.stdout)
        self.assertEqual(quem(int(m.group(1))), f'vesta-painel {self.r}')
        self.assertEqual(self.abertos(), [m.group(0)])

    def test_sem_vesta_falha_sem_abrir(self):
        p = self.rodar()
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(p.stderr.strip())
        self.assertNotIn('http://localhost', p.stdout)
        self.assertEqual(self.abertos(), [])


class Pagina(unittest.TestCase):
    TIPOS = ('rodando', 'plano', 'pausada', 'travada', 'concluida', 'vazio', 'ilegivel')

    def setUp(self):
        with open(os.path.join(AQUI, 'painel.html'), encoding='utf-8') as f:
            self.h = f.read()

    def test_pontos_de_montagem(self):
        for i in ('palavra', 'cheio', 'etapas', 'leitor', 'arco', 'pontos', 'colunas',
                  'ferr', 'aviso-sessao'):
            with self.subTest(i):
                self.assertRegex(self.h, rf'\bid\s*=\s*["\']?{re.escape(i)}["\'\s>]')

    def test_carrega_marked_e_busca_estado_a_cada_3s(self):
        self.assertRegex(self.h, r'<script[^>]*\bsrc\s*=\s*["\']?/marked\.js')
        self.assertRegex(self.h, r'fetch\(\s*["\'`]/estado')
        self.assertRegex(self.h, r'setInterval\([^;]*\b3000\b|setTimeout\([^;]*\b3000\b')

    def test_uma_regra_de_cor_por_tipo_de_momento(self):
        for t in self.TIPOS:
            with self.subTest(t):
                self.assertRegex(self.h, rf'\[data-estado\s*=\s*["\']?{t}["\']?\]')

    def test_js_atribui_o_tipo_ao_body(self):
        self.assertRegex(self.h, r'body\.dataset\.estado\s*=|body\.setAttribute\(\s*["\']data-estado')

    def test_nada_de_fora_alem_do_google_fonts(self):
        hosts = re.findall(r'(?:\b(?:src|href|action)\s*=\s*["\']?|url\(\s*["\']?|@import\s+["\']?'
                           r'|\b(?:fetch|import)\(\s*["\'`])(?:https?:)?//([^/"\'`\s)>]+)', self.h, re.I)
        for h in hosts:
            with self.subTest(h):
                self.assertIn(h.lower(), ('fonts.googleapis.com', 'fonts.gstatic.com'))

    def test_rotulo_projeto_acima_do_nome(self):
        self.assertRegex(self.h, r'class="micro">\s*projeto\s*</div>\s*<h1 id="projeto">')
        self.assertNotIn('painel de execução', self.h)

    def test_titulo_da_aba_comeca_pelo_projeto(self):
        self.assertRegex(self.h, r"document\.title\s*=\s*`\$\{D\.projeto\}[^`]*· Vesta`")
        self.assertNotRegex(self.h, r"document\.title\s*=\s*['\"`]Vesta")


# Rodada, etapa 1 — formatos escolhidos aqui (o plano deixou em aberto):
# - "inicio" é a hora da última invocação da skill vesta; "sessoes" traz o nome do .jsonl sem
#   extensão; fase sem marco não tem hora conferida; item de pergunta é conferido só pelas chaves
#   que o plano lista. Horas conferidas em America/Sao_Paulo (UTC-3), então 12:00Z vira 09:00.
# - Se a própria invocação entra na atividade ficou em aberto; os testes não dependem disso.
FASES = ['ativacao', 'spec', 'pesquisa', 'grill', 'mockup', 'plano', 'execucao', 'concluida']


def ts(minuto):
    return f'2026-01-01T12:{minuto:02d}:00.000Z'


def usar(id_, nome, entrada, minuto):
    return {'type': 'assistant', 'timestamp': ts(minuto), 'message': {
        'role': 'assistant', 'content': [{'type': 'tool_use', 'id': id_, 'name': nome, 'input': entrada}]}}


def ativar(minuto, id_='sk'):
    return usar(id_, 'Skill', {'skill': 'vesta'}, minuto)


def ler_md(nome, minuto, id_=None, pasta='/h/.claude/skills/vesta'):
    return usar(id_ or f'rd-{nome}-{minuto}', 'Read', {'file_path': f'{pasta}/{nome}.md'}, minuto)


def texto(t, minuto):
    return {'type': 'assistant', 'timestamp': ts(minuto),
            'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': t}]}}


def questao(q, header, rotulos, multi=False):
    return {'question': q, 'header': header, 'multiSelect': multi,
            'options': [{'label': r, 'description': ''} for r in rotulos]}


def perguntar(id_, questoes, minuto):
    return usar(id_, 'AskUserQuestion', {'questions': questoes}, minuto)


def responder(id_, questoes, respostas, minuto):
    return {'type': 'user', 'timestamp': ts(minuto), 'toolUseResult': {
        'questions': questoes, 'answers': respostas}, 'message': {'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': id_, 'content': 'ok'}]}}


class RodadaBase(SessaoBase):
    def setUp(self):
        super().setUp()
        self.addCleanup(time.tzset)
        p = mock.patch.dict(os.environ, {'TZ': 'America/Sao_Paulo'})
        p.start()
        self.addCleanup(p.stop)
        time.tzset()

    def rodada(self, linhas):
        self.jsonl('s1.jsonl', linhas)
        return painel.rodada(self.r)

    def estados(self, d):
        return {f['id'] if 'id' in f else n: f['estado'] for n, f in zip(FASES, d['fases'])}

    def respostas(self, linhas):
        p = os.path.join(self.home.name, '.claude', 'vesta', 'respostas.jsonl')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write('\n'.join(l if isinstance(l, str) else json.dumps(l) for l in linhas) + '\n')


class RodadaFormato(RodadaBase):
    def test_sem_registro_e_sem(self):
        self.assertEqual(painel.rodada(self.r)['formato'], 'sem')

    def test_registro_sem_invocacao_e_nenhuma(self):
        d = self.rodada([texto('oi', 0), ler_md('spec', 1),
                         usar('o', 'Skill', {'skill': 'vesta-interface'}, 2)])
        self.assertEqual(d['formato'], 'nenhuma')

    def test_content_fora_de_lista_e_desconhecido(self):
        d = self.rodada([
            {'type': 'assistant', 'timestamp': ts(0), 'message': {'content': 'Skill vesta'}},
            {'type': 'user', 'timestamp': ts(1), 'message': {'content': 'skills/vesta/spec.md'}},
            {'outra': 'coisa'}])
        self.assertEqual(d['formato'], 'desconhecido')
        self.assertFalse(d.get('fases'))
        self.assertFalse(d.get('historico'))
        self.assertFalse(d.get('atividade'))

    def test_com_invocacao_tem_formato_de_rodada_e_sessao(self):
        d = self.rodada([texto('antes', 0), ativar(3)])
        self.assertNotIn(d['formato'], ('sem', 'nenhuma', 'desconhecido'))
        self.assertEqual(d['sessoes'], ['s1'])
        self.assertEqual(d['inicio'], '09:03')

    def test_registro_do_sdk_nao_e_usado(self):
        cli = self.jsonl('a.jsonl', [dict(ativar(0), entrypoint='cli'), ler_md('grill', 1)], 1_000)
        self.jsonl('b.jsonl', [dict(texto('revisor', 0), entrypoint='sdk-py')], 2_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], [os.path.basename(cli)[:-6]])
        self.assertEqual(self.estados(d)['grill'], 'atual')

    def test_le_o_registro_mais_recente(self):
        self.jsonl('velho.jsonl', [ativar(0), ler_md('plano', 1)], 1_000)
        self.jsonl('novo.jsonl', [ativar(0), ler_md('spec', 1)], 2_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['novo'])
        self.assertEqual(self.estados(d)['spec'], 'atual')

    def test_linha_ilegivel_no_meio_e_pulada(self):
        q = [questao('Depois?', 'H', ['A'])]
        d = self.rodada([ativar(0), '{quebrado', ler_md('spec', 1), '[1, 2', perguntar('q', q, 2)])
        self.assertEqual(self.estados(d)['spec'], 'atual')
        self.assertEqual([h.get('pergunta') for h in d['historico']], ['Depois?'])

    def test_dados_traz_a_rodada(self):
        self.jsonl('s1.jsonl', [ativar(0), ler_md('spec', 1)])
        self.assertEqual(painel.dados(self.r)['rodada'], painel.rodada(self.r))
        self.jsonl('s1.jsonl', [texto('nada', 0)])
        self.assertEqual(painel.dados(self.r)['rodada']['formato'], 'nenhuma')


class RodadaFases(RodadaBase):
    def test_so_ativacao_e_atual_e_resto_pendente(self):
        d = self.rodada([ativar(0)])
        self.assertEqual([f['estado'] for f in d['fases']], ['atual'] + ['pendente'] * 7)
        self.assertEqual(d['fases'][0]['hora'], '09:00')
        self.assertEqual(len(d['fases']), 8)

    def test_fases_na_ordem_com_estado_e_hora(self):
        d = self.rodada([ativar(0)])
        for f in d['fases']:
            self.assertIn('estado', f)
            self.assertIn('hora', f)
        if 'id' in d['fases'][0]:
            self.assertEqual([f['id'] for f in d['fases']], FASES)

    def test_marcos_em_ordem_feita_ate_a_atual(self):
        d = self.rodada([ativar(0), ler_md('spec', 5), ler_md('research', 10),
                         ler_md('grill', 15), ler_md('mockup', 20)])
        self.assertEqual([f['estado'] for f in d['fases']],
                         ['feita', 'feita', 'feita', 'feita', 'atual', 'pendente', 'pendente', 'pendente'])
        self.assertEqual([f['hora'] for f in d['fases'][:5]],
                         ['09:00', '09:05', '09:10', '09:15', '09:20'])

    def test_fase_sem_marco_antes_da_atual_e_pulada(self):
        d = self.rodada([ativar(0), ler_md('spec', 1), ler_md('grill', 2)])
        self.assertEqual([f['estado'] for f in d['fases']],
                         ['feita', 'feita', 'pulada', 'atual', 'pendente', 'pendente', 'pendente', 'pendente'])

    def test_marco_por_bash_e_pelo_caminho_do_repositorio(self):
        d = self.rodada([ativar(0), usar('b', 'Bash', {'command': 'cat ~/.claude/skills/vesta/research.md'}, 1),
                         usar('c', 'Bash', {'command': 'sed -n 1,40p /u/Code/vesta/skill/plano.md'}, 2)])
        self.assertEqual([f['estado'] for f in d['fases']],
                         ['feita', 'pulada', 'feita', 'pulada', 'pulada', 'atual', 'pendente', 'pendente'])
        self.assertEqual(d['fases'][2]['hora'], '09:01')

    def test_read_pelo_caminho_do_repositorio(self):
        d = self.rodada([ativar(0), ler_md('execucao', 1, pasta='/u/Code/vesta/skill')])
        self.assertEqual(self.estados(d)['execucao'], 'atual')

    def test_marco_em_outra_ferramenta_nao_conta(self):
        d = self.rodada([ativar(0), usar('g', 'Grep', {'pattern': 'x', 'path': '/h/.claude/skills/vesta/spec.md'}, 1),
                         usar('e', 'Edit', {'file_path': '/h/.claude/skills/vesta/grill.md'}, 2)])
        self.assertEqual(self.estados(d)['ativacao'], 'atual')

    def test_execucao_por_vesta_py_criar_e_iniciar(self):
        for sub in ('criar', 'iniciar'):
            with self.subTest(sub=sub):
                d = self.rodada([ativar(0), ler_md('spec', 1),
                                 usar('v', 'Bash', {'command': f'python3 ~/.claude/skills/vesta/scripts/vesta.py {sub} plano.md'}, 7)])
                self.assertEqual([f['estado'] for f in d['fases']],
                                 ['feita', 'feita', 'pulada', 'pulada', 'pulada', 'pulada', 'atual', 'pendente'])
                self.assertEqual(d['fases'][6]['hora'], '09:07')

    def test_vesta_interface_nao_conta_como_fase(self):
        d = self.rodada([ativar(0), ler_md('spec', 1),
                         ler_md('mockup', 2, pasta='/h/.claude/skills/vesta-interface'),
                         usar('b', 'Bash', {'command': 'cat ~/.claude/skills/vesta-interface/plano.md'}, 3)])
        self.assertEqual([f['estado'] for f in d['fases']],
                         ['feita', 'atual'] + ['pendente'] * 6)

    def test_concluida_quando_execucao_encerrada(self):
        self.gravar(estado([etapa(1, 'feita'), etapa(2, 'feita')]))
        d = self.rodada([ativar(0), ler_md('execucao', 1)])
        self.assertEqual(self.estados(d)['concluida'], 'atual')
        self.assertEqual(self.estados(d)['execucao'], 'feita')

    def test_execucao_aberta_nao_conclui(self):
        self.gravar(estado([etapa(1, 'feita'), etapa(2)]))
        d = self.rodada([ativar(0), ler_md('execucao', 1)])
        self.assertEqual(self.estados(d)['execucao'], 'atual')
        self.assertEqual(self.estados(d)['concluida'], 'pendente')

    def test_so_conta_depois_da_ultima_invocacao(self):
        q = [questao('Velha?', 'V', ['A'])]
        d = self.rodada([ativar(0, 'sk1'), ler_md('plano', 1), texto('velho', 2), perguntar('qv', q, 3),
                         responder('qv', q, {'Velha?': 'A'}, 3),
                         usar('rv', 'Read', {'file_path': '/x/velho.py'}, 4),
                         ativar(10, 'sk2'), ler_md('spec', 11)])
        self.assertEqual([f['estado'] for f in d['fases']], ['feita', 'atual'] + ['pendente'] * 6)
        self.assertEqual(d['inicio'], '09:10')
        self.assertEqual(d['historico'], [])
        self.assertNotIn('/x/velho.py', [a['alvo'] for a in d['atividade']])
        self.assertNotIn('Velha?', [a['alvo'] for a in d['atividade']])


class RodadaHistorico(RodadaBase):
    Q1 = [questao('Qual cor?', 'Cor', ['Azul', 'Verde'])]
    Q2 = [questao('Quais telas?', 'Telas', ['Lista', 'Detalhe', 'Busca'], multi=True),
          questao('Qual nome?', 'Nome', ['Vesta', 'Painel'])]
    Q3 = [questao('Pode seguir?', 'Seguir', ['Sim', 'Não'])]

    def registro(self):
        return self.rodada([
            texto('antes da rodada', 0), ativar(1), texto('Começando a spec.', 2),
            perguntar('q1', self.Q1, 3), responder('q1', self.Q1, {'Qual cor?': 'Azul'}, 3),
            perguntar('q2', self.Q2, 4),
            responder('q2', self.Q2, {'Quais telas?': 'Lista, Busca', 'Qual nome?': 'Outro nome, Vesta'}, 4),
            texto('Anotado.', 5), perguntar('q3', self.Q3, 6)])

    def test_historico_em_ordem_com_mensagens_e_questoes(self):
        self.respostas([{'tool_use_id': 'q1', 'onde': 'painel'}, '{quebrado',
                        {'tool_use_id': 'q2', 'onde': 'knobler'}])
        h = self.registro()['historico']
        esperado = [
            {'tipo': 'mensagem', 'texto': 'Começando a spec.', 'hora': '09:02'},
            {'header': 'Cor', 'pergunta': 'Qual cor?', 'multipla': False, 'resposta': 'Azul',
             'livre': False, 'onde': 'painel', 'hora': '09:03'},
            {'header': 'Telas', 'pergunta': 'Quais telas?', 'multipla': True,
             'resposta': 'Lista, Busca', 'livre': False, 'onde': 'knobler', 'hora': '09:04'},
            {'header': 'Nome', 'pergunta': 'Qual nome?', 'multipla': False,
             'resposta': 'Outro nome, Vesta', 'livre': True, 'onde': 'knobler', 'hora': '09:04'},
            {'tipo': 'mensagem', 'texto': 'Anotado.', 'hora': '09:05'},
            {'header': 'Seguir', 'pergunta': 'Pode seguir?', 'multipla': False, 'resposta': None,
             'onde': 'terminal', 'hora': '09:06'},
        ]
        self.assertEqual(len(h), len(esperado))
        for item, esp in zip(h, esperado):
            self.assertEqual({k: item.get(k, '<ausente>') for k in esp}, esp)

    def test_sem_respostas_jsonl_tudo_e_terminal(self):
        h = self.registro()['historico']
        self.assertEqual([x['onde'] for x in h if 'pergunta' in x], ['terminal'] * 4)

    def test_resposta_livre_de_questao_unica(self):
        q = [questao('Qual cor?', 'Cor', ['Azul', 'Verde'])]
        h = self.rodada([ativar(0), perguntar('q', q, 1),
                         responder('q', q, {'Qual cor?': 'Um azul mais escuro'}, 1)])['historico']
        self.assertEqual((h[0]['resposta'], h[0]['livre']), ('Um azul mais escuro', True))

    def test_juncao_de_rotulos_nao_e_livre_e_rotulo_parcial_e(self):
        q = [questao('Quais?', 'Q', ['A', 'B', 'C'], multi=True)]
        for resp, livre in (('A, C', False), ('C, A, B', False), ('A,C', True), ('A, D', True)):
            with self.subTest(resp=resp):
                h = self.rodada([ativar(0), perguntar('q', q, 1),
                                 responder('q', q, {'Quais?': resp}, 1)])['historico']
                self.assertEqual(h[0]['livre'], livre)


class RodadaAtividade(RodadaBase):
    def test_alvo_por_ferramenta_do_mais_recente_ao_mais_antigo(self):
        cmd = 'echo ' + 'x' * 200 + '\nsegunda linha'
        usos = [('Read', {'file_path': '/a/r.py'}, '/a/r.py'),
                ('Edit', {'file_path': '/a/e.py', 'old_string': 'a', 'new_string': 'b'}, '/a/e.py'),
                ('Write', {'file_path': '/a/w.py', 'content': 'z'}, '/a/w.py'),
                ('Bash', {'command': cmd, 'description': 'd'}, cmd[:120]),
                ('Grep', {'pattern': 'def x', 'path': '/a'}, 'def x'),
                ('Glob', {'pattern': '**/*.py'}, '**/*.py'),
                ('WebFetch', {'url': 'https://ex.com', 'prompt': 'p'}, 'https://ex.com'),
                ('WebSearch', {'query': 'kokoro tts'}, 'kokoro tts'),
                ('Agent', {'description': 'Acha testes', 'prompt': 'p'}, 'Acha testes'),
                ('Skill', {'skill': 'vesta-interface'}, 'vesta-interface'),
                ('AskUserQuestion', {'questions': [questao('Primeira?', 'P', ['a']),
                                                   questao('Segunda?', 'S', ['b'])]}, 'Primeira?'),
                ('mcp__graft__graft_find_code', {'query': 'x'}, None),
                ('TodoWrite', {'todos': []}, '')]
        d = self.rodada([ativar(0)] + [usar(f'u{i}', n, e, i + 1) for i, (n, e, _) in enumerate(usos)])
        topo = d['atividade'][:len(usos)]
        esperado = [(re.sub(r'^mcp__.+?__', '', n), a) for n, _, a in reversed(usos)]
        self.assertEqual([x['ferramenta'] for x in topo], [f for f, _ in esperado])
        for x, (f, a) in zip(topo, esperado):
            if a is not None:
                self.assertEqual(x['alvo'], a, f)
        self.assertEqual(topo[0]['hora'], f'09:{len(usos):02d}')
        self.assertEqual(topo[-1]['hora'], '09:01')
        self.assertIn(d['n_atividade'], (len(usos), len(usos) + 1))

    def test_limite_de_200_com_total(self):
        linhas = [ativar(0)] + [usar(f'b{i}', 'Bash', {'command': f'cmd {i}'}, 1) for i in range(250)]
        d = self.rodada(linhas)
        self.assertEqual(len(d['atividade']), 200)
        self.assertEqual(d['atividade'][0]['alvo'], 'cmd 249')
        self.assertEqual(d['atividade'][199]['alvo'], 'cmd 50')
        self.assertIn(d['n_atividade'], (250, 251))


SPEC = 'docs/vesta/specs/2026-01-01-abc-design.md'


def cita(id_, minuto, rel=SPEC, nome='Read'):
    return usar(id_, nome, {'file_path': '/u/Code/vesta-wt/' + rel}, minuto)


# Etapa 2. Escolhas dos testes: "ordem de tempo" das sessões é a do primeiro timestamp; as horas
# de mtime ficam longe o bastante da meia-noite para valer tanto na local quanto na UTC.
class RodadaCostura(RodadaBase):
    def setUp(self):
        super().setUp()
        self.arquivo(SPEC, '# spec\n')
        self.outra = os.path.join(os.path.realpath(self.home.name), '.claude', 'projects',
                                  '-u-Code-vesta-wt')
        self.meia = datetime(2026, 1, 1).timestamp()  # meia-noite local da data da spec

    def em(self, pasta, nome, linhas, mtime):
        os.makedirs(pasta, exist_ok=True)
        p = os.path.join(pasta, nome + '.jsonl')
        with open(p, 'w') as f:
            for l in linhas:
                f.write(json.dumps(l) + '\n')
        os.utime(p, (mtime, mtime))
        return p

    def textos(self, d):
        return [h['texto'] for h in d['historico'] if h.get('tipo') == 'mensagem']

    def test_duas_pastas_viram_uma_rodada_intercalada(self):
        # a outra pasta é modificada por último, mas começou antes: a ordem é a do tempo
        self.em(self.outra, 'a', [ativar(0), texto('a1', 1), ler_md('spec', 2),
                                  cita('wa', 3, nome='Write'), texto('a2', 6),
                                  usar('ra', 'Read', {'file_path': '/a/x.py'}, 9)],
                self.meia + 50_000)
        self.em(self.proj, 'b', [cita('rb', 4), texto('b1', 5), texto('b2', 7), ler_md('grill', 8)],
                self.meia + 40_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['a', 'b'])
        self.assertEqual(d['inicio'], '09:00')
        self.assertEqual(self.textos(d), ['a1', 'b1', 'a2', 'b2'])
        self.assertEqual([x['hora'] for x in d['atividade'][:5]],
                         ['09:09', '09:08', '09:04', '09:03', '09:02'])
        self.assertEqual([f['estado'] for f in d['fases']],
                         ['feita', 'feita', 'pulada', 'atual', 'pendente', 'pendente', 'pendente', 'pendente'])
        self.assertEqual((d['fases'][1]['hora'], d['fases'][3]['hora']), ('09:02', '09:08'))

    def test_comeca_na_ultima_invocacao_da_sessao_mais_antiga(self):
        self.em(self.outra, 'a', [ativar(0, 'sk1'), texto('rodada velha', 1), ativar(2, 'sk2'),
                                  cita('wa', 3, nome='Write'), ler_md('spec', 3), texto('a', 4)],
                self.meia + 40_000)
        self.em(self.proj, 'b', [ativar(10, 'sk3'), cita('rb', 11), texto('b', 12)],
                self.meia + 50_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['a', 'b'])
        self.assertEqual(d['inicio'], '09:02')
        self.assertEqual(self.textos(d), ['a', 'b'])
        self.assertEqual(self.estados(d)['spec'], 'atual')

    def test_sessao_que_nao_cita_a_spec_fica_fora_mesmo_na_pasta_do_projeto(self):
        self.em(self.outra, 'a', [ativar(0), cita('wa', 1, nome='Write'), texto('a', 2)],
                self.meia + 40_000)
        self.em(self.proj, 'c', [ativar(3), texto('c', 4), ler_md('plano', 5)], self.meia + 45_000)
        self.em(self.proj, 'b', [cita('rb', 6), texto('b', 7)], self.meia + 50_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['a', 'b'])
        self.assertEqual(self.textos(d), ['a', 'b'])
        self.assertEqual(self.estados(d)['plano'], 'pendente')

    def test_registro_modificado_antes_da_data_da_spec_fica_fora_sem_ser_lido(self):
        velho = self.em(self.outra, 'd', [ativar(0), cita('wd', 1, nome='Write'), texto('d', 2)],
                        self.meia - 6 * 3600)
        self.em(self.outra, 'e', [ativar(3), cita('we', 4, nome='Write'), texto('e', 5)],
                self.meia + 6 * 3600)
        self.em(self.proj, 'b', [cita('rb', 6), texto('b', 7)], self.meia + 50_000)
        abertos, real = [], open

        def abrir(p, *a, **k):
            if isinstance(p, str):
                abertos.append(os.path.realpath(p))
            return real(p, *a, **k)

        with mock.patch('builtins.open', abrir):
            d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['e', 'b'])
        self.assertEqual(self.textos(d), ['e', 'b'])
        self.assertNotIn(os.path.realpath(velho), abertos)

    def test_sem_spec_so_a_sessao_atual(self):
        os.remove(os.path.join(self.r, SPEC))
        self.arquivo('docs/vesta/research/2026-01-01-abc-research.md', '# pesquisa\n')
        self.em(self.outra, 'a', [ativar(0), cita('wa', 1, nome='Write'), texto('a', 2)],
                self.meia + 40_000)
        self.em(self.proj, 'c', [ativar(3), cita('rc', 4), texto('c', 5)], self.meia + 45_000)
        self.em(self.proj, 'b', [ativar(6), texto('b', 7)], self.meia + 50_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['b'])
        self.assertEqual(d['inicio'], '09:06')
        self.assertEqual(self.textos(d), ['b'])

    def test_sessao_atual_entra_mesmo_sem_citar_a_spec(self):
        self.em(self.outra, 'a', [ativar(0), cita('wa', 1, nome='Write'), texto('a', 2)],
                self.meia + 40_000)
        self.em(self.proj, 'b', [texto('b', 3), ler_md('research', 4)], self.meia + 50_000)
        d = painel.rodada(self.r)
        self.assertEqual(d['sessoes'], ['a', 'b'])
        self.assertEqual(self.textos(d), ['a', 'b'])
        self.assertEqual(self.estados(d)['pesquisa'], 'atual')

    def test_feature_do_plano_vence_a_mais_recente(self):
        velha = 'docs/vesta/specs/2026-01-01-velha-design.md'
        nova = 'docs/vesta/specs/2026-01-02-nova-design.md'
        self.arquivo(velha, '# velha\n')
        self.arquivo(nova, '# nova\n')
        self.arquivo('docs/vesta/plans/2026-01-01-velha.md', '# plano\n')
        dia = self.meia + 5 * 86_400
        self.em(self.outra, 'v', [ativar(0), cita('wv', 1, velha, 'Write'), texto('v', 2)], dia)
        self.em(self.outra, 'n', [ativar(0), cita('wn', 1, nova, 'Write'), texto('n', 2)], dia + 10)
        self.em(self.proj, 'b', [texto('b', 3)], dia + 20)
        with self.subTest('sem execução: a feature mais recente'):
            self.assertEqual(painel.rodada(self.r)['sessoes'], ['n', 'b'])
        self.gravar(estado([etapa('1')], plano='docs/vesta/plans/2026-01-01-velha.md'))
        with self.subTest('com execução: a feature do plano'):
            self.assertEqual(painel.rodada(self.r)['sessoes'], ['v', 'b'])


# Prazos curtos para o teste não dormir 10/15/5 s. O servidor lê VESTA_PRAZO_ABERTO,
# VESTA_PRAZO_ABANDONO e VESTA_PRAZO_OUTRO (segundos, float) do ambiente; sem elas, 10, 15 e 5.
# Valores distintos entre si: trocar um prazo pelo outro reprova algum teste.
ABERTO, ABANDONO, OUTRO = 0.5, 1.2, 0.8
Q = [{'question': 'Qual cor?', 'header': 'Cor', 'multiSelect': False,
      'options': [{'label': 'azul', 'description': ''}, {'label': 'verde', 'description': ''}]}]


class PrazosPadrao(unittest.TestCase):
    def test_prazos_padrao_sao_10_15_e_5(self):
        self.assertEqual((painel.PRAZO_ABERTO, painel.PRAZO_ABANDONO, painel.PRAZO_OUTRO),
                         (10, 15, 5))


class PonteBase(ServidorBase):
    PRAZOS = {'VESTA_PRAZO_ABERTO': str(ABERTO), 'VESTA_PRAZO_ABANDONO': str(ABANDONO),
              'VESTA_PRAZO_OUTRO': str(OUTRO)}

    def post(self, caminho, corpo):
        dado = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
        req = urllib.request.Request(f'http://127.0.0.1:{self.porta}{caminho}', data=dado,
                                     method='POST', headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def json(self, caminho):
        st, _, corpo = self.get(caminho)
        return json.loads(corpo)

    def aberto(self):
        return self.json('/aberto')

    def perguntas(self):
        return self.json('/estado')['perguntas']

    def pergunta(self, id_):
        return self.json(f'/pergunta/{id_}')

    def perguntar(self, id_, questions=Q, knobler=False):
        st, corpo = self.post('/pergunta', {'id': id_, 'questions': questions, 'knobler': knobler})
        self.assertEqual(st, 200, corpo)


class Aberto(PonteBase):
    def test_falso_antes_de_qualquer_estado(self):
        self.assertEqual(self.aberto(), {'aberto': False})

    def test_verdadeiro_logo_depois_do_estado(self):
        self.get('/estado')
        self.assertEqual(self.aberto(), {'aberto': True})

    def test_falso_passado_o_prazo_mesmo_consultando_aberto(self):
        self.get('/estado')
        fim = time.time() + ABERTO + 0.3
        while time.time() < fim:  # /aberto não conta como página aberta
            self.aberto()
            time.sleep(0.1)
        self.assertEqual(self.aberto(), {'aberto': False})
        self.get('/estado')
        self.assertEqual(self.aberto(), {'aberto': True})


class AbertoPrazoReal(ServidorBase):
    def test_sem_variavel_segue_aberto_depois_do_prazo_curto(self):
        self.get('/estado')
        time.sleep(ABERTO + 0.3)
        st, _, corpo = self.get('/aberto')
        self.assertEqual((st, json.loads(corpo)), (200, {'aberto': True}))


class Fila(PonteBase):
    def test_estado_sem_perguntas_traz_lista_vazia(self):
        self.assertEqual(self.perguntas(), [])

    def test_pendentes_em_ordem_de_chegada_com_os_campos(self):
        outra = [{'question': 'E o tamanho?', 'header': 'Tam', 'multiSelect': True,
                  'options': [{'label': 'P', 'description': ''}]}]
        self.perguntar('z', Q, True)
        self.perguntar('a', outra, False)
        self.perguntar('m', Q, False)
        self.assertEqual(self.perguntas(), [
            {'id': 'z', 'questions': Q, 'knobler': True, 'estado': 'pendente'},
            {'id': 'a', 'questions': outra, 'knobler': False, 'estado': 'pendente'},
            {'id': 'm', 'questions': Q, 'knobler': False, 'estado': 'pendente'}])

    def test_postagens_simultaneas_nao_perdem_pergunta(self):
        n = 30
        barreira = threading.Barrier(n)
        erros = []

        def postar(i):
            barreira.wait()
            st, corpo = self.post('/pergunta', {'id': f'p{i}', 'questions': Q, 'knobler': False})
            if st != 200:
                erros.append((i, st, corpo))

        ts = [threading.Thread(target=postar, args=(i,)) for i in range(n)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(erros, [])
        ids = [p['id'] for p in self.perguntas()]
        self.assertEqual(sorted(ids), sorted(f'p{i}' for i in range(n)))
        self.assertEqual(len(ids), n)

    def test_corpo_invalido_e_400_e_nada_entra(self):
        for corpo in (b'nao e json', b'', b'[]', b'{}', {'questions': Q, 'knobler': False},
                      {'id': 'x', 'knobler': False}):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.post('/pergunta', corpo)[0], 400)
        self.assertEqual(self.perguntas(), [])


class Resposta(PonteBase):
    ANS = {'Qual cor?': {'labels': ['azul'], 'text': ''}}

    def test_pendente_ate_responder(self):
        self.perguntar('q1')
        self.get('/estado')
        self.assertEqual(self.pergunta('q1'), {'estado': 'pendente'})

    def test_responder_devolve_respostas_e_tira_da_fila(self):
        self.perguntar('q1')
        self.perguntar('q2')
        st, _ = self.post('/resposta/q1', {'answers': self.ANS})
        self.assertEqual(st, 200)
        self.assertEqual(self.pergunta('q1'), {'estado': 'respondida', 'answers': self.ANS})
        self.assertEqual([p['id'] for p in self.perguntas()], ['q2'])

    def test_desconhecida(self):
        self.assertEqual(self.pergunta('nunca'), {'estado': 'desconhecida'})

    def test_responder_de_novo_e_409_e_vale_a_primeira(self):
        self.perguntar('q1')
        self.post('/resposta/q1', {'answers': self.ANS})
        outra = {'Qual cor?': {'labels': ['verde'], 'text': 'x'}}
        self.assertEqual(self.post('/resposta/q1', {'answers': outra})[0], 409)
        self.assertEqual(self.pergunta('q1'), {'estado': 'respondida', 'answers': self.ANS})

    def test_corpo_invalido_e_400_e_segue_pendente(self):
        self.perguntar('q1')
        for corpo in (b'nao e json', b'', b'[]', b'{}', {'respostas': self.ANS}):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.post('/resposta/q1', corpo)[0], 400)
        self.get('/estado')
        self.assertEqual(self.pergunta('q1'), {'estado': 'pendente'})
        self.assertEqual([p['id'] for p in self.perguntas()], ['q1'])

    def test_abandonada_sem_estado_pelo_prazo_de_abandono(self):
        self.perguntar('q1')
        self.get('/estado')
        time.sleep(ABERTO + 0.3)  # já fechado (prazo de aberto), mas ainda não abandonado
        self.assertEqual(self.pergunta('q1'), {'estado': 'pendente'})
        fim = time.time() + ABANDONO
        while time.time() < fim:  # consultar /pergunta não conta como página aberta
            self.pergunta('q1')
            time.sleep(0.1)
        self.assertEqual(self.pergunta('q1'), {'estado': 'abandonada'})

    def test_respondida_nao_vira_abandonada(self):
        self.perguntar('q1')
        self.get('/estado')
        self.post('/resposta/q1', {'answers': self.ANS})
        time.sleep(ABANDONO + 0.3)
        self.assertEqual(self.pergunta('q1'), {'estado': 'respondida', 'answers': self.ANS})


class Encerrar(PonteBase):
    ANS = {'Qual cor?': {'labels': [], 'text': 'roxo'}}

    def test_fica_como_outro_pelo_prazo_e_depois_sai(self):
        self.perguntar('q1')
        self.perguntar('q2')
        st, _ = self.post('/pergunta/q1/encerrar', {'motivo': 'knobler'})
        self.assertEqual(st, 200)
        self.assertEqual(self.pergunta('q1'), {'estado': 'encerrada'})
        ps = {p['id']: p['estado'] for p in self.perguntas()}
        self.assertEqual(ps, {'q1': 'outro', 'q2': 'pendente'})
        time.sleep(ABERTO + 0.1)  # antes do prazo de "outro"
        self.assertIn('q1', [p['id'] for p in self.perguntas()])
        time.sleep(0.4)  # ~1.0 s: passou de OUTRO (0.8), antes de ABANDONO (1.2)
        self.assertEqual([p['id'] for p in self.perguntas()], ['q2'])
        self.assertEqual(self.pergunta('q1'), {'estado': 'encerrada'})

    def test_responder_encerrada_e_409_e_nada_muda(self):
        self.perguntar('q1')
        self.post('/pergunta/q1/encerrar', {'motivo': 'knobler'})
        self.assertEqual(self.post('/resposta/q1', {'answers': self.ANS})[0], 409)
        self.assertEqual(self.pergunta('q1'), {'estado': 'encerrada'})
        self.assertEqual([(p['id'], p['estado']) for p in self.perguntas()], [('q1', 'outro')])

    def test_corpo_invalido_e_400_e_segue_pendente(self):
        self.perguntar('q1')
        for corpo in (b'nao e json', b'', b'[]', b'{}'):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.post('/pergunta/q1/encerrar', corpo)[0], 400)
        self.get('/estado')
        self.assertEqual(self.pergunta('q1'), {'estado': 'pendente'})


class Achar(PainelBase):
    def setUp(self):
        super().setUp()
        self.arquivo('docs/vesta/specs/x.md', 'x')
        self.n = painel.porta(self.r)
        self.prox = [4700 + (self.n - 4700 + i) % 100 for i in range(1, 3)]

    def servir(self, raiz, n):
        p = subprocess.Popen([sys.executable, os.path.join(AQUI, 'painel.py'), 'servir', raiz,
                              str(n)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(p.wait)
        self.addCleanup(p.kill)
        fim = time.time() + 5
        while not escuta(n):
            if time.time() > fim:
                self.fail('servidor não abriu a porta')
            time.sleep(0.05)

    def ocupar(self, n):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', n))
        s.listen()
        self.addCleanup(s.close)

    def test_sem_servidor_e_none_e_nao_sobe(self):
        if escuta(self.n):
            self.skipTest(f'porta {self.n} já ocupada nesta máquina')
        self.assertIsNone(painel.achar(self.r))
        time.sleep(0.3)
        self.assertFalse(escuta(self.n))
        self.assertEqual([i for i in range(100) if f'vesta-painel {self.r}' in quem(4700 + i)], [])

    def test_acha_o_servidor_no_ar(self):
        u = painel.subir(self.r)
        self.assertIsNotNone(u)
        self.assertEqual(painel.achar(self.r), u)

    def test_pula_porta_ocupada_por_outro(self):
        if escuta(self.n) or escuta(self.prox[0]):
            self.skipTest('portas já ocupadas nesta máquina')
        self.ocupar(self.n)
        self.servir(self.r, self.prox[0])
        self.assertEqual(painel.achar(self.r), self.url(self.prox[0]))

    def test_para_na_primeira_porta_livre(self):
        if any(escuta(n) for n in [self.n, *self.prox]):
            self.skipTest('portas já ocupadas nesta máquina')
        self.ocupar(self.n)
        self.servir(self.r, self.prox[1])  # depois de uma porta livre: não é achado
        self.assertIsNone(painel.achar(self.r))

    def test_painel_de_outra_raiz_nao_conta(self):
        if escuta(self.n) or escuta(self.prox[0]):
            self.skipTest('portas já ocupadas nesta máquina')
        outra = tempfile.TemporaryDirectory()
        self.addCleanup(outra.cleanup)
        self.servir(os.path.realpath(outra.name), self.n)
        self.assertIsNone(painel.achar(self.r))


# Etapa 6 — tela da rodada. Nomes das fases como o mockup mostra (NOMES em
# docs/vesta/mockups/2026-09-28-rodada-no-painel/index.html).
NOMES = {'ativacao': 'Ativação', 'spec': 'Spec', 'pesquisa': 'Pesquisa', 'grill': 'Grill',
         'mockup': 'Mockup', 'plano': 'Plano', 'execucao': 'Execução'}
MARCO_DA_FASE = {'spec': 'spec', 'pesquisa': 'research', 'grill': 'grill', 'mockup': 'mockup',
                 'plano': 'plano', 'execucao': 'execucao'}


class MomentoFase(RodadaBase):
    def test_sem_execucao_com_rodada_ativa_e_a_fase_atual(self):
        for n, fase in enumerate(FASES[:7], 1):
            with self.subTest(fase):
                linhas = [ativar(0)] + ([ler_md(MARCO_DA_FASE[fase], 1)] if n > 1 else [])
                self.jsonl('s1.jsonl', linhas)
                self.assertEqual(painel.dados(self.r)['momento'],
                                 {'tipo': 'fase', 'fase': NOMES[fase], 'texto': f'Fase {n} de 8'})

    def test_fase_pulada_conta_pela_posicao_da_atual(self):
        self.jsonl('s1.jsonl', [ativar(0), ler_md('spec', 1), ler_md('mockup', 2)])
        self.assertEqual(painel.dados(self.r)['momento'],
                         {'tipo': 'fase', 'fase': 'Mockup', 'texto': 'Fase 5 de 8'})

    def test_com_execucao_o_momento_e_o_de_hoje(self):
        e = estado([etapa('1', 'feita'), etapa('2')])
        self.gravar(e)
        self.jsonl('s1.jsonl', [ativar(0), ler_md('execucao', 1)])
        self.assertEqual(painel.dados(self.r)['momento'], painel.momento(e))
        self.assertEqual(painel.dados(self.r)['momento']['tipo'], 'rodando')

    def test_sem_rodada_ativa_continua_vazio(self):
        for linhas in ([texto('oi', 0)], ['{quebrado'], None):
            with self.subTest(linhas):
                if linhas is not None:
                    self.jsonl('s1.jsonl', linhas)
                self.assertEqual(painel.dados(self.r)['momento']['tipo'], 'vazio')


IDS_RODADA = ('pergunta', 'p-opcoes', 'p-livre', 'p-enviar', 'rodada', 'fases', 'hist', 'ativ',
              'rodada-aviso')


class PaginaRodada(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(AQUI, 'painel.html'), encoding='utf-8') as f:
            self.h = f.read()

    def test_ids_do_mockup(self):
        for i in IDS_RODADA:
            with self.subTest(i):
                self.assertRegex(self.h, rf'\bid\s*=\s*["\']?{re.escape(i)}["\'\s>]')

    def test_cores_novas_no_root(self):
        root = re.search(r':root\s*\{([^}]*)\}', self.h)
        self.assertIsNotNone(root)
        for nome, valor in (('verde', '#ff4d00'), ('ciano', '#ff4d00'), ('coral', 'oklch(0.93 0 0)')):
            with self.subTest(nome):
                self.assertRegex(root[1], rf'--{nome}\s*:\s*{re.escape(valor)}\s*(;|$)')

    def test_sem_as_cores_antigas(self):
        for c in ('#5fd08a', '#5cc8e0', '#f07a62'):
            with self.subTest(c):
                self.assertNotIn(c, self.h.lower())

    def test_avisos_da_rodada(self):
        for t in ('Sem registro de sessão · a rodada aparece quando a Vesta for ativada neste projeto',
                  'Registro em formato desconhecido', 'Nenhuma rodada nesta sessão'):
            with self.subTest(t):
                self.assertIn(t, self.h)

    def envio(self):
        m = re.search(r'fetch\(\s*[`\'"]/resposta/', self.h)
        self.assertIsNotNone(m, 'nenhum fetch para /resposta/')
        ini = max(self.h.rfind('onsubmit', 0, m.start()),
                  self.h.rfind("addEventListener('submit'", 0, m.start()),
                  self.h.rfind('addEventListener("submit"', 0, m.start()))
        self.assertGreater(ini, -1, 'o fetch de /resposta/ não está no envio do formulário')
        return self.h[ini:m.start()], self.h[m.start():m.start() + 400]

    def test_envio_faz_post_em_resposta_com_o_id(self):
        _, chamada = self.envio()
        self.assertRegex(chamada, r'^fetch\(\s*(`/resposta/\$\{|[\'"]/resposta/[\'"]\s*\+)')
        self.assertRegex(chamada, r'method\s*:\s*[\'"`]POST[\'"`]')

    def test_envio_manda_labels_marcados_e_text_do_campo(self):
        antes, chamada = self.envio()
        trecho = antes + chamada
        self.assertIn(':checked', trecho)
        self.assertIn('p-livre', trecho)
        for campo in ('answers', 'labels', 'text'):
            with self.subTest(campo):
                self.assertRegex(trecho, rf'\b{campo}\b\s*:|["\']{campo}["\']\s*:')

    def test_sem_nada_nao_envia_e_mostra_o_aviso(self):
        self.assertIn('Marque uma opção ou escreva uma resposta.', self.h)
        antes, _ = self.envio()
        self.assertRegex(antes, r'if\s*\([^)]*\.length[^)]*\)\s*\{?\s*return\b',
                         'o envio não retorna antes do fetch quando não há opção nem texto')


class ServidorPaginaRodada(ServidorBase):
    def test_pagina_servida_tem_os_ids_da_rodada(self):
        st, _, corpo = self.get('/')
        self.assertEqual(st, 200)
        h = corpo.decode()
        for i in IDS_RODADA:
            with self.subTest(i):
                self.assertRegex(h, rf'\bid\s*=\s*["\']?{re.escape(i)}["\'\s>]')


def ts_local(dias_atras, hora, minuto=0, segundo=0):
    """Timestamp UTC ('Z') de um instante em hora local, `dias_atras` dias antes de hoje."""
    d = datetime.now().replace(hour=hora, minute=minuto, second=segundo, microsecond=0)
    d = (d - timedelta(days=dias_atras)).astimezone(timezone.utc)
    return d.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def hoje_cedo():
    return ts_local(0, 0, 0, 1)


class Ritmo(SessaoBase):
    T0 = '2026-01-01T10:00:00.000Z'

    def em(self, s):
        return f'2026-01-01T10:{s // 60:02d}:{s % 60:02d}.000Z'

    def test_48_trechos_somando_requests(self):
        self.jsonl('s.jsonl', [{'type': 'user', 'timestamp': self.T0, 'message': {}},
                               linha_assistant('a', self.em(5)), linha_assistant('b', self.em(15)),
                               linha_assistant('c', self.em(480))])
        s = painel.sessao(self.r)
        self.assertEqual(len(s['ritmo']), 48)
        self.assertEqual(sum(s['ritmo']), s['requests'])
        # 480 s / 48 = 10 s por trecho: 5 s -> 0, 15 s -> 1, 480 s (o fim) -> 47
        self.assertEqual(s['ritmo'][:2] + s['ritmo'][-1:], [1, 1, 1])

    def test_intervalo_vai_do_primeiro_ao_ultimo_timestamp_de_qualquer_linha(self):
        self.jsonl('s.jsonl', [{'type': 'user', 'timestamp': self.T0, 'message': {}},
                               linha_assistant('a', self.em(240)),
                               {'type': 'user', 'timestamp': self.em(480), 'message': {}}])
        r = painel.sessao(self.r)['ritmo']
        self.assertEqual(r[24], 1)
        self.assertEqual(sum(r), 1)

    def test_request_repetido_conta_uma_vez_no_primeiro_timestamp(self):
        self.jsonl('s.jsonl', [{'type': 'user', 'timestamp': self.T0, 'message': {}},
                               linha_assistant('a', self.em(5)), linha_assistant('a', self.em(400)),
                               {'type': 'user', 'timestamp': self.em(480), 'message': {}}])
        r = painel.sessao(self.r)['ritmo']
        self.assertEqual((r[0], r[40], sum(r)), (1, 0, 1))

    def test_sessao_de_um_instante_cai_toda_no_trecho_0(self):
        self.jsonl('s.jsonl', [linha_assistant('a', self.T0), linha_assistant('b', self.T0)])
        self.assertEqual(painel.sessao(self.r)['ritmo'], [2] + [0] * 47)


class Historico(SessaoBase):
    def hist(self):
        return painel.historico(self.r)

    def test_sem_sessoes_sao_zeros_sem_erro(self):
        self.assertEqual(self.hist(), {'dias': [0] * 140, 'horas': [0] * 24})
        os.makedirs(self.proj)
        self.assertEqual(self.hist(), {'dias': [0] * 140, 'horas': [0] * 24})

    def test_dias_termina_hoje_e_soma_todas_as_sessoes(self):
        self.jsonl('a.jsonl', [linha_assistant('a1', hoje_cedo()), linha_assistant('a2', hoje_cedo()),
                               linha_assistant('a3', ts_local(2, 12))])
        self.jsonl('b.jsonl', [linha_assistant('b1', hoje_cedo()), linha_assistant('b2', ts_local(139, 12))])
        d = self.hist()['dias']
        self.assertEqual(len(d), 140)
        self.assertEqual((d[-1], d[-3], d[0]), (3, 1, 1))
        self.assertEqual(sum(d), 5)

    def test_horas_usa_hora_local_de_todas_as_sessoes_e_dias(self):
        self.jsonl('a.jsonl', [linha_assistant('a1', ts_local(3, 9, 30)), linha_assistant('a2', ts_local(5, 9, 5))])
        self.jsonl('b.jsonl', [linha_assistant('b1', ts_local(1, 23, 59)), linha_assistant('b2', ts_local(200, 0, 10))])
        h = self.hist()['horas']
        self.assertEqual(len(h), 24)
        self.assertEqual((h[9], h[23], h[0], sum(h)), (2, 1, 1, 4))

    def test_request_repetido_entre_arquivos_conta_uma_vez(self):
        self.jsonl('a.jsonl', [linha_assistant('x', ts_local(1, 10)), linha_assistant('x', ts_local(1, 10, 0, 1))])
        self.jsonl('b.jsonl', [linha_assistant('x', ts_local(1, 10))])
        h = self.hist()
        self.assertEqual((sum(h['dias']), sum(h['horas']), h['dias'][-2]), (1, 1, 1))

    def test_sessao_do_sdk_nao_conta(self):
        self.jsonl('a.jsonl', [dict(linha_assistant('x', ts_local(1, 10)), entrypoint='cli')])
        self.jsonl('b.jsonl', [dict(linha_assistant('y', ts_local(1, 10)), entrypoint='sdk-py')])
        h = self.hist()
        self.assertEqual((sum(h['dias']), sum(h['horas'])), (1, 1))

    def test_sem_timestamp_e_nao_json_nao_entram_em_nada(self):
        sem = linha_assistant('x', None); del sem['timestamp']
        self.jsonl('a.jsonl', ['{quebrado', sem, linha_assistant('y', ts_local(1, 10))])
        h = self.hist()
        self.assertEqual((sum(h['dias']), sum(h['horas'])), (1, 1))

    def test_mais_velha_que_140_dias_so_entra_em_horas(self):
        self.jsonl('a.jsonl', [linha_assistant('x', ts_local(141, 8)), linha_assistant('y', ts_local(300, 8))])
        h = self.hist()
        self.assertEqual(sum(h['dias']), 0)
        self.assertEqual(h['horas'][8], 2)

    def test_dados_inclui_hist(self):
        self.jsonl('a.jsonl', [linha_assistant('x', ts_local(1, 10))])
        self.assertEqual(painel.dados(self.r)['hist'], painel.historico(self.r))
        self.assertEqual(painel.dados(self.r)['hist']['horas'][10], 1)


class CacheDeLeitura(SessaoBase):
    def abertos(self, caminho, fn):
        real = open
        with mock.patch('builtins.open', wraps=real) as m:
            fn()
        return [c for c in m.call_args_list if c.args and os.fspath(c.args[0]) == caminho]

    def test_arquivo_igual_nao_e_relido(self):
        p = self.jsonl('s.jsonl', [linha_assistant('x', ts_local(1, 10), i=4)], 1_000)
        primeira = painel.dados(self.r)
        self.assertEqual(self.abertos(p, lambda: painel.dados(self.r)), [])
        self.assertEqual(painel.dados(self.r)['hist'], primeira['hist'])
        self.assertEqual(painel.dados(self.r)['sessao'], primeira['sessao'])

    def test_arquivo_que_mudou_e_relido(self):
        p = self.jsonl('s.jsonl', [linha_assistant('x', ts_local(1, 10), i=4)], 1_000)
        painel.dados(self.r)
        self.jsonl('s.jsonl', [linha_assistant('x', ts_local(1, 10), i=4),
                               linha_assistant('y', ts_local(1, 11), i=6)], 1_000)  # mesmo mtime, outro tamanho
        self.assertEqual(painel.sessao(self.r)['requests'], 2)
        self.assertEqual(sum(painel.historico(self.r)['dias']), 2)
        self.jsonl('s.jsonl', [linha_assistant('x', ts_local(1, 10), i=4),
                               linha_assistant('z', ts_local(1, 11), i=6)], 2_000)  # mesmo tamanho, outro mtime
        self.assertTrue(self.abertos(p, lambda: painel.sessao(self.r)))

# Faixa única, etapa 1 — as fases da Rodada abrem os documentos; a faixa da Trilha sai.
class PaginaFaixaUnica(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(AQUI, 'painel.html'), encoding='utf-8') as f:
            self.h = f.read()

    def test_sem_a_faixa_da_trilha(self):
        self.assertNotRegex(self.h, r'class\s*=\s*["\']?[^"\'>]*\btrilha\b', 'o HTML ainda tem class="trilha"')
        self.assertNotRegex(self.h, r'\.trilha\b', 'o CSS ou o JS ainda cita .trilha')
        self.assertNotRegex(self.h, r'function\s+trilha\s*\(|\btrilha\s*=\s*(\([^)]*\)|\w+)\s*=>',
                            'a função trilha() ainda existe')

    def test_bloco_do_leitor_se_chama_documento(self):
        m = re.search(r'<div class="bloco"[^>]*>((?:(?!<div class="bloco").)*?id="leitor")', self.h, re.S)
        self.assertIsNotNone(m, 'id="leitor" não está num bloco')
        bloco = m[1]
        self.assertRegex(bloco, r'<h3>\s*Documento\s*</h3>')
        self.assertNotRegex(bloco, r'<h3>\s*Trilha\s*</h3>')
        self.assertRegex(bloco, r'\bid="trilha-cab"')

    def test_css_dos_botoes_das_fases(self):
        for sel in (r'\.fases button:hover', r'\.fases button:focus-visible',
                    r'\.fases button\[aria-pressed=["\']?true["\']?\]'):
            with self.subTest(sel):
                self.assertRegex(self.h, sel + r'[^{]*\{')


# Roda o JS do painel no node com um DOM de mentira. Modo padrão chama rodada() e devolve o que a faixa mostra;
# modo 'render' chama render() e devolve os filhos dos ids pedidos.
HARNESS = open(os.path.join(AQUI, 'simulacao_painel.js'), encoding='utf-8').read()

FEAT_ATUAL = {'topico': 'faixa-unica', 'data': '2026-09-29',
              'spec': 'docs/vesta/specs/2026-09-29-faixa-unica-design.md',
              'research': 'docs/vesta/research/2026-09-29-faixa-unica-research.md',
              'plano': None, 'mockup': None, 'grill': False}
FEAT_VELHA = {'topico': 'acesso-ao-painel', 'data': '2026-09-20',
              'spec': 'docs/vesta/specs/2026-09-20-acesso-ao-painel-design.md',
              'research': None, 'plano': 'docs/vesta/plans/2026-09-20-acesso-ao-painel.md',
              'mockup': 'docs/vesta/mockups/2026-09-20-acesso-ao-painel', 'grill': True}
RODADA_VIVA = {'formato': 'claude-code', 'sessoes': ['s1'], 'inicio': '09:00',
               'fases': [{'id': 'ativacao', 'estado': 'feita', 'hora': '09:00'},
                         {'id': 'spec', 'estado': 'feita', 'hora': '09:05'},
                         {'id': 'pesquisa', 'estado': 'feita', 'hora': '09:10'},
                         {'id': 'grill', 'estado': 'atual', 'hora': '09:20'},
                         {'id': 'mockup', 'estado': 'pendente', 'hora': None},
                         {'id': 'plano', 'estado': 'pendente', 'hora': None},
                         {'id': 'execucao', 'estado': 'pendente', 'hora': None},
                         {'id': 'concluida', 'estado': 'pendente', 'hora': None}],
               'historico': [], 'atividade': [], 'n_atividade': 0}


@unittest.skipUnless(shutil.which('node'), 'node ausente')
class FaixaUnicaNoNavegador(unittest.TestCase):
    ORDEM = ['ativacao', 'spec', 'pesquisa', 'grill', 'mockup', 'plano', 'execucao', 'concluida']

    def rodar(self, escolhida=None, aberto=None, clicar=None, atual=FEAT_ATUAL):
        D = {'atual': atual, 'features': [FEAT_ATUAL, FEAT_VELHA], 'rodada': RODADA_VIVA}
        cen = {'D': D, 'escolhida': escolhida, 'aberto': aberto, 'clicar': clicar}
        p = subprocess.run(['node', '-e', HARNESS, os.path.join(AQUI, 'painel.html'), json.dumps(cen)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(len(out['fases']), 8)
        out['por_fase'] = dict(zip(self.ORDEM, out['fases']))
        return out

    def botao(self, li):
        m = re.search(r'<button\b[^>]*>', li['html'])
        return m and m[0]

    def test_fases_com_documento_viram_botoes_com_data_doc(self):
        f = self.rodar()['por_fase']
        for fase, doc in (('spec', 'spec'), ('pesquisa', 'research')):
            with self.subTest(fase):
                b = self.botao(f[fase])
                self.assertIsNotNone(b, f'{fase} tem documento e não virou botão')
                self.assertIn(f'data-doc="{doc}"', b)
                self.assertRegex(b, r'type="button"')

    def test_fases_sem_documento_nao_tem_botao(self):
        f = self.rodar()['por_fase']
        # grill sem a linha na spec, sem mockup, sem plano; ativação/execução/concluída nunca têm.
        for fase in ('ativacao', 'grill', 'mockup', 'plano', 'execucao', 'concluida'):
            with self.subTest(fase):
                self.assertIsNone(self.botao(f[fase]))

    def test_grill_abre_o_documento_grill_quando_a_spec_tem_grill(self):
        atual = dict(FEAT_ATUAL, grill=True, plano='docs/vesta/plans/p.md', mockup='docs/vesta/mockups/m')
        f = self.rodar(atual=atual)['por_fase']
        for fase, doc in (('grill', 'grill'), ('plano', 'plano'), ('mockup', 'mockup')):
            with self.subTest(fase):
                b = self.botao(f[fase])
                self.assertIsNotNone(b)
                self.assertIn(f'data-doc="{doc}"', b)

    def test_aria_pressed_so_no_documento_aberto(self):
        f = self.rodar(aberto='research')['por_fase']
        self.assertIsNotNone(self.botao(f['pesquisa']), 'pesquisa não virou botão')
        self.assertIsNotNone(self.botao(f['spec']), 'spec não virou botão')
        self.assertRegex(self.botao(f['pesquisa']), r'aria-pressed="true"')
        self.assertRegex(self.botao(f['spec']), r'aria-pressed="false"')

    def test_clicar_na_fase_abre_o_documento(self):
        out = self.rodar(clicar='spec')
        self.assertEqual(out.get('doc_cab'), 'Spec // faixa unica')

    def test_clicar_na_pesquisa_mostra_o_nome_da_fase(self):
        out = self.rodar(clicar='research')
        self.assertEqual(out.get('doc_cab'), 'Pesquisa // faixa unica')

    def test_feature_atual_segue_com_horario_e_agora(self):
        f = self.rodar()['por_fase']
        self.assertIn('09:05', f['spec']['html'])
        self.assertNotIn('>ler<', f['spec']['html'])
        self.assertIn('agora', f['grill']['html'])

    def test_feature_antiga_mostra_as_fases_dela_com_ler(self):
        out = self.rodar(escolhida='acesso-ao-painel')
        f = out['por_fase']
        for fase, doc in (('spec', 'spec'), ('grill', 'grill'), ('mockup', 'mockup'), ('plano', 'plano')):
            with self.subTest(fase):
                self.assertIn('feita', f[fase]['classe'].split())
                b = self.botao(f[fase])
                self.assertIsNotNone(b)
                self.assertIn(f'data-doc="{doc}"', b)
                self.assertRegex(f[fase]['html'], r'>\s*ler\s*<')
        with self.subTest('pesquisa sem documento'):
            self.assertIn('pendente', f['pesquisa']['classe'].split())
            self.assertIsNone(self.botao(f['pesquisa']))
        for fase in self.ORDEM:
            with self.subTest(fase, horario=True):
                self.assertNotIn('agora', f[fase]['html'])
                self.assertNotRegex(f[fase]['html'], r'\d\d:\d\d')

    def test_feature_antiga_cabecalho_e_sem_historico(self):
        out = self.rodar(escolhida='acesso-ao-painel')
        self.assertEqual(out['cab'], 'acesso ao painel // 2026-09-20')
        self.assertTrue(out['aviso_oculto'])
        self.assertTrue(out['cols_ocultas'])

    def test_escolher_a_propria_feature_atual_nao_e_antiga(self):
        out = self.rodar(escolhida='faixa-unica')
        self.assertEqual(out['cab'], '1 sessão // desde 09:00')
        self.assertFalse(out['cols_ocultas'])


# Animações do painel, etapa 1 — a simulação roda o render() inteiro com um painel em execução.
ETAPA = lambda i, titulo, status, vermelho=None, commit=None, tent=0: {
    'id': i, 'titulo': titulo, 'tela': False, 'status': status,
    'provas': {'teste': {'vermelho': vermelho, 'resultado': 'verde' if commit else None,
                         'commit': commit, 'tentativas': tent}}}
FEAT_TERCEIRA = {'topico': 'rodada-ao-vivo', 'data': '2026-09-10',
                 'spec': 'docs/vesta/specs/2026-09-10-rodada-ao-vivo-design.md', 'research': None,
                 'plano': None, 'mockup': None, 'grill': False}
ENTRADA = [18_000 + 3_500 * i for i in range(22)]
PAINEL_RODANDO = {
    'projeto': 'vesta', 'caminho': '~/Code/vesta',
    'momento': {'tipo': 'rodando', 'texto': 'Rodando na etapa 2 de 4'},
    'estado': {'versao': 1, 'plano': 'docs/vesta/plans/2026-09-29-animacoes-do-painel.md', 'espera': None,
               'motivo': None, 'etapas': [
                   ETAPA('1', 'Simulação de página que roda o painel inteiro', 'feita', 'f00dbee', 'abc1234def', 1),
                   ETAPA('2', 'Motor de movimento e gráficos reaproveitados', 'pendente', 'c0ffee1', None, 2),
                   ETAPA('3', 'Listas, células e rótulos reaproveitados', 'pendente'),
                   ETAPA('4', 'Entrada escalonada dos blocos', 'pendente')]},
    'erro': None,
    'features': [FEAT_ATUAL, FEAT_VELHA, FEAT_TERCEIRA], 'atual': FEAT_ATUAL,
    'tempos': {'1': 14.5, '2': None, '3': None, '4': None},
    'sessao': {'inicio': '2026-09-29T12:00:00Z', 'fim': '2026-09-29T12:30:30Z', 'duracao_s': 1830,
               'requests': len(ENTRADA), 'entrada': ENTRADA, 'saida': 5_400,
               'ferramentas': [['Bash', 12], ['Read', 9], ['Edit', 4], ['Grep', 2]],
               'contexto': ENTRADA[-1], 'ritmo': [i % 6 for i in range(48)], 'janela': 200_000},
    'rodada': dict(RODADA_VIVA,
                   historico=[{'tipo': 'mensagem', 'texto': 'Começando o grill', 'hora': '09:20'},
                              {'header': 'Escopo', 'pergunta': 'Anima o odômetro?', 'hora': '09:21',
                               'resposta': 'Sim', 'onde': 'painel', 'livre': False},
                              {'header': 'Ritmo', 'pergunta': 'Quanto dura a entrada?', 'hora': '09:24',
                               'resposta': None, 'onde': 'terminal', 'livre': False}],
                   atividade=[{'hora': '09:25', 'ferramenta': 'Read', 'alvo': 'painel.html'},
                              {'hora': '09:24', 'ferramenta': 'Grep', 'alvo': 'requestAnimationFrame'},
                              {'hora': '09:23', 'ferramenta': 'Bash', 'alvo': 'git log'}],
                   n_atividade=7),
    'hist': {'dias': [i % 5 for i in range(140)], 'horas': [h % 7 for h in range(24)]},
}


@unittest.skipUnless(shutil.which('node'), 'node ausente')
class PainelInteiroNoNavegador(unittest.TestCase):
    """Interface que o teste espera do HARNESS no modo novo.

    Cenário (JSON em argv[2]): {'modo': 'render', 'D': <estado de /estado>, 'ids': [<id>, ...]}.
    Sem 'modo' (ou 'modo': 'rodada') o HARNESS segue como hoje, para FaixaUnicaNoNavegador.
    No modo 'render' ele define D e chama render() (não rodada()), e escreve no stdout:
      {'raf': typeof requestAnimationFrame, 'caf': typeof cancelAnimationFrame  (avaliados dentro da página),
       'ids': {<id>: {'n': <nº de filhos em children>, 'filhos': [<outer de cada filho>, ...]}}}
    Um erro no render() deixa o node com código de saída diferente de zero.
    """
    GRAFICOS = ['arco', 'pontos', 'colunas', 'ferr', 'dias', 'radar', 'onda', 'rel']
    LISTAS = ['etapas', 'fases', 'hist', 'ativ']

    def rodar(self, D=PAINEL_RODANDO):
        cen = {'modo': 'render', 'D': D, 'ids': self.GRAFICOS + self.LISTAS}
        p = subprocess.run(['node', '-e', HARNESS, os.path.join(AQUI, 'painel.html'), json.dumps(cen)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, f'render() falhou na simulação:\n{p.stderr}')
        return json.loads(p.stdout)

    def test_render_completo_roda_sem_erro(self):
        out = self.rodar()
        self.assertIn('ids', out, 'a simulação não tem o modo render')
        self.assertEqual(set(out['ids']), set(self.GRAFICOS + self.LISTAS))

    def test_cada_grafico_desenha_algo(self):
        ids = self.rodar()['ids']
        for g in self.GRAFICOS:
            with self.subTest(g):
                self.assertGreaterEqual(ids[g]['n'], 1, f'#{g} ficou vazio')
                self.assertEqual(len(ids[g]['filhos']), ids[g]['n'])
                self.assertRegex(ids[g]['filhos'][0], r'^<\w+', f'#{g}: filho sem outer')

    def test_etapas_um_item_por_etapa_na_ordem(self):
        e = self.rodar()['ids']['etapas']
        xs = PAINEL_RODANDO['estado']['etapas']
        self.assertEqual(e['n'], len(xs))
        for li, x in zip(e['filhos'], xs):
            with self.subTest(x['id']):
                self.assertIn(x['titulo'], li)
        self.assertIn('abc1234', e['filhos'][0])           # feita: commit curto
        self.assertIn('implementando', e['filhos'][1])     # atual
        self.assertIn('tent. 2/8', e['filhos'][1])
        for li in e['filhos'][2:]:
            self.assertIn('aguardando', li)                # pendentes

    def test_fases_uma_por_fase_da_rodada(self):
        f = self.rodar()['ids']['fases']
        fases = PAINEL_RODANDO['rodada']['fases']
        self.assertEqual(f['n'], len(fases))
        nomes = ['Ativação', 'Spec', 'Pesquisa', 'Grill', 'Mockup', 'Plano', 'Execução', 'Concluída']
        for li, nome in zip(f['filhos'], nomes):
            with self.subTest(nome):
                self.assertIn(f'<b>{nome}</b>', li)

    def test_historico_um_item_por_entrada(self):
        h = self.rodar()['ids']['hist']
        hist = PAINEL_RODANDO['rodada']['historico']
        self.assertEqual(h['n'], len(hist))
        for li, x in zip(h['filhos'], hist):
            with self.subTest(x['hora']):
                self.assertIn(x.get('pergunta') or x['texto'], li)

    def test_atividade_um_item_por_entrada(self):
        a = self.rodar()['ids']['ativ']
        ativ = PAINEL_RODANDO['rodada']['atividade']
        self.assertEqual(a['n'], len(ativ))
        for li, x in zip(a['filhos'], ativ):
            with self.subTest(x['alvo']):
                self.assertIn(x['alvo'], li)

    def test_pagina_sem_requestanimationframe(self):
        out = self.rodar()
        self.assertEqual(out.get('raf'), 'undefined', 'a simulação ainda define requestAnimationFrame')
        self.assertEqual(out.get('caf'), 'undefined', 'a simulação ainda define cancelAnimationFrame')


# Etapa 2 das animações — motor de movimento e gráficos reaproveitados por chave.
FEAT_QUARTA = {'topico': 'entrada-escalonada', 'data': '2026-09-01',
               'spec': 'docs/vesta/specs/2026-09-01-entrada-escalonada-design.md', 'research': None,
               'plano': None, 'mockup': None, 'grill': False}


def _attr(nome, outer):
    m = re.search(rf'^<[^>]*\s{re.escape(nome)}="([^"]*)"', outer)
    return m and m[1]


def _num(nome, outer):
    v = _attr(nome, outer)
    return None if v is None else float(v)


def _texto(outer):
    m = re.search(r'>([^<>]*)</\w+>$', outer)
    return m and m[1]


def _nums(s):
    return [float(x) for x in re.findall(r'-?\d*\.?\d+(?:e[-+]?\d+)?', s or '', re.I)]


@unittest.skipUnless(shutil.which('node'), 'node ausente')
class MovimentoNoNavegador(unittest.TestCase):
    """Interface que estes testes esperam do HARNESS (skill/scripts/simulacao_painel.js).

    Cenário (JSON em argv[2]):
      {'modo': 'render', 'passos': [D1, D2, ...], 'ids': [<id>, ...], 'avaliar': [<expr JS>, ...]}
    - Com 'passos', o HARNESS roda `D=Dk; render()` para cada passo, em ordem, no mesmo contexto.
      Antes de cada passo depois do primeiro, marca como "visto" todo descendente (recursivo) dos
      ids pedidos. O 'D' único antigo continua aceito (PainelInteiroNoNavegador).
    - Saída no stdout:
      {'raf', 'caf', 'ids': {<id>: {'n', 'filhos'}}   (do ÚLTIMO passo, como hoje),
       'passos': [{<id>: {'n': nº de filhos diretos,
                          'mesmos': quantos filhos diretos já estavam marcados como vistos
                                    (o mesmo objeto de uma leitura anterior; 0 no primeiro passo),
                          'filhos': [outer de cada filho]}}, ...]   (um item por passo),
       'avaliado': [resultado JSON de cada expressão de 'avaliar', avaliada no escopo da página
                    depois do último passo (null vira None)],
       'pendentes': `typeof vivos!=='undefined' ? vivos.size : null`, depois do último passo}
    Um erro em qualquer render() deixa o node com código de saída diferente de zero.
    """
    GRAFICOS = PainelInteiroNoNavegador.GRAFICOS

    def rodar(self, passos, ids=None, avaliar=()):
        cen = {'modo': 'render', 'passos': passos, 'ids': ids or self.GRAFICOS, 'avaliar': list(avaliar)}
        p = subprocess.run(['node', '-e', HARNESS, os.path.join(AQUI, 'painel.html'), json.dumps(cen)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, f'render() falhou na simulação:\n{p.stderr}')
        out = json.loads(p.stdout)
        self.assertEqual(len(out.get('passos') or []), len(passos), 'a simulação não devolve um item por passo')
        return out

    def D(self):
        return copy.deepcopy(PAINEL_RODANDO)

    def passos(self, out, g):
        return [x[g] for x in out['passos']]

    # --- reaproveitamento ---

    def test_mesmos_dados_mantem_cada_filho_como_o_mesmo_objeto(self):
        p1, p2 = out = self.rodar([self.D(), self.D()])['passos']
        for g in self.GRAFICOS:
            with self.subTest(g):
                self.assertGreater(p1[g]['n'], 0, f'#{g} ficou vazio')
                self.assertEqual(p2[g]['n'], p1[g]['n'], f'#{g}: a contagem mudou com os mesmos dados')
                self.assertEqual(p2[g]['mesmos'], p2[g]['n'],
                                 f'#{g}: {p2[g]["n"] - p2[g]["mesmos"]} filhos recriados na segunda leitura')

    def test_request_nova_acrescenta_uma_coluna_de_15_pontos_e_mantem_as_antigas(self):
        d2 = self.D()
        d2['sessao']['entrada'] = ENTRADA + [60_000]
        d2['sessao']['requests'] += 1
        p1, p2 = self.passos(self.rodar([self.D(), d2], ids=['pontos']), 'pontos')
        grupos = lambda p: [f for f in p['filhos'] if f.startswith('<g')]
        self.assertEqual(len(grupos(p2)) - len(grupos(p1)), 1, 'a request nova não virou um <g> a mais')
        self.assertEqual(p2['n'], p1['n'] + 1)
        self.assertEqual(p2['mesmos'], p1['n'], 'filhos antigos de #pontos foram recriados')
        novo = [g for g in grupos(p2) if (_nums(_attr('transform', g)) or [None])[0] is not None
                and abs(_nums(_attr('transform', g))[0] - 190) < 1e-6]
        self.assertEqual(len(novo), 1, 'grupo da coluna nova (translate 190) não encontrado')
        g = novo[0]
        self.assertRegex(_attr('transform', g) or '', r'^translate\(\S+ \S+\) scale\(\S+ \S+\)$')
        for a, b in zip(_nums(_attr('transform', g)), [190, 0, 1, 1]):
            self.assertAlmostEqual(a, b, places=6, msg=_attr('transform', g))
        circ = re.findall(r'<circle\b[^>]*>', g)
        self.assertEqual(len(circ), 15, 'o grupo novo não tem 15 pontos')
        cab = [c for c in circ if _attr('r', c) == '1.1']
        self.assertEqual(len(cab), 1, 'cabeça da coluna nova não encontrada')
        self.assertAlmostEqual(_num('cx', cab[0]), 0, places=6)
        mx = max(ENTRADA + [60_000]) * 1.1
        self.assertAlmostEqual(_num('cy', cab[0]), 108 - 60_000 / mx * 108, places=6,
                               msg='o cy da cabeça nova não chegou ao valor final')

    def test_tempo_que_muda_leva_barra_e_numero_ao_valor_novo(self):
        d1, d2 = self.D(), self.D()
        d1['tempos']['2'], d2['tempos']['2'] = 5.0, 20.0
        c1, c2 = self.passos(self.rodar([d1, d2], ids=['colunas']), 'colunas')
        self.assertEqual(c2['n'], c1['n'])
        self.assertEqual(c2['mesmos'], c2['n'], 'colunas recriadas quando só o valor mudou')
        barras = [f for f in c2['filhos'] if f.startswith('<rect') and 'url(#hx)' in f]
        self.assertEqual(len(barras), 2)
        mx = max(10, 14.5, 20.0) * 1.1
        self.assertAlmostEqual(_num('height', barras[1]), 20.0 / mx * 96, places=6)
        self.assertAlmostEqual(_num('y', barras[1]), 108 - 20.0 / mx * 96, places=6)
        valores = [_texto(f) for f in c2['filhos'] if f.startswith('<text') and 'fill:var(--tinta)' in f]
        self.assertEqual(valores, ['15', '20'])

    def test_etapa_que_some_de_tempos_perde_a_coluna(self):
        d2 = self.D()
        del d2['tempos']['4']
        c1, c2 = self.passos(self.rodar([self.D(), d2], ids=['colunas']), 'colunas')
        molduras = lambda p: [f for f in p['filhos'] if f.startswith('<rect') and 'class="s-traco"' in f]
        rotulos = lambda p: sorted(_texto(f) for f in p['filhos'] if re.fullmatch(r'<text[^>]*>0\d</text>', f))
        self.assertEqual(len(molduras(c1)), 4)
        self.assertEqual(rotulos(c1), ['01', '02', '03', '04'])
        self.assertEqual(len(molduras(c2)), 3, 'a coluna da etapa 4 ficou')
        self.assertEqual(rotulos(c2), ['01', '02', '03'])
        self.assertEqual(c2['n'], c1['n'] - 3)
        self.assertEqual(c2['mesmos'], c2['n'])

    def test_feature_que_sai_e_que_entra_no_radar(self):
        d2, d3 = self.D(), self.D()
        d2['features'] = [FEAT_ATUAL, FEAT_TERCEIRA]
        d3['features'] = [FEAT_ATUAL, FEAT_TERCEIRA, FEAT_QUARTA]
        r1, r2, r3 = self.passos(self.rodar([self.D(), d2, d3], ids=['radar']), 'radar')

        def trio(p):
            f = p['filhos']
            return (sum(1 for x in f if x.startswith('<circle') and _attr('r', x) == '8'),
                    sum(1 for x in f if x.startswith('<line') and _attr('x1', x) == '110' and _attr('y1', x) == '88'),
                    sum(1 for x in f if x.startswith('<text') and 'font-weight:600' in x))
        self.assertEqual(trio(r1), (3, 3, 3))
        self.assertEqual(trio(r2), (2, 2, 2), 'círculo, linha e número da feature que saiu ficaram')
        self.assertEqual(r2['n'], r1['n'] - 3)
        self.assertEqual(r2['mesmos'], r2['n'])
        self.assertEqual(trio(r3), (3, 3, 3), 'a feature que entrou não ganhou círculo, linha e número')
        self.assertEqual(r3['n'], r2['n'] + 3)
        self.assertEqual(r3['mesmos'], r2['n'])

    def test_contexto_novo_leva_o_arco_ao_percentual_novo(self):
        d2 = self.D()
        d2['sessao']['contexto'] = 123_400
        a2 = self.passos(self.rodar([self.D(), d2], ids=['arco']), 'arco')[1]
        direto = self.passos(self.rodar([d2], ids=['arco']), 'arco')[0]
        uso = lambda p: [f for f in p['filhos'] if f.startswith('<path') and 'class="s-acento"' in f]
        self.assertEqual(len(uso(a2)), 1)
        d = _attr('d', uso(a2)[0])
        self.assertEqual(d, _attr('d', uso(direto)[0]), 'o traço de uso não terminou no percentual novo')
        pct = 123_400 / 200_000
        P = lambda a, rr: (110 - rr * math.cos(a * math.pi), 112 - rr * math.sin(a * math.pi))
        esperado = [*P(0, 85), 85, 85, 0, 0, 1, *P(pct, 85)]
        obtido = _nums(d)
        self.assertEqual(len(obtido), len(esperado), d)
        for a, b in zip(obtido, esperado):
            self.assertAlmostEqual(a, b, places=6, msg=d)
        centro = [f for f in a2['filhos'] if f.startswith('<text') and '30px' in f]
        self.assertEqual([_texto(f) for f in centro], ['61.7'])

    def test_ferramentas_reordenadas_mantem_os_rotulos(self):
        d2 = self.D()
        nova = list(reversed(PAINEL_RODANDO['sessao']['ferramentas']))
        d2['sessao']['ferramentas'] = nova
        f1, f2 = self.passos(self.rodar([self.D(), d2], ids=['ferr']), 'ferr')
        self.assertEqual(f2['n'], f1['n'])
        self.assertEqual(f2['mesmos'], f2['n'], 'rótulos ou barras recriados ao mudar a ordem')
        for i, (nome, _) in enumerate(nova):
            with self.subTest(nome):
                rot = [f for f in f2['filhos'] if f.startswith('<text') and _texto(f) == nome[:7].upper()]
                self.assertEqual(len(rot), 1)
                self.assertAlmostEqual(_num('y', rot[0]), 6 + i * 19 + 4, places=6)

    def test_nada_fica_pendente_depois_do_render(self):
        d2 = self.D()
        s = d2['sessao']
        s['entrada'] = ENTRADA + [60_000]
        s['contexto'] = 123_400
        s['ferramentas'] = list(reversed(s['ferramentas']))
        s['ritmo'] = [(i * 3) % 7 for i in range(48)]
        d2['tempos']['2'] = 20.0
        d2['features'] = [FEAT_ATUAL, FEAT_TERCEIRA, FEAT_QUARTA]
        d2['hist'] = {'dias': [i % 3 for i in range(140)], 'horas': [(h * 5) % 9 for h in range(24)]}
        for passos in ([self.D()], [self.D(), d2]):
            with self.subTest(len(passos)):
                self.assertEqual(self.rodar(passos).get('pendentes'), 0)

    # --- mistura ---

    def misturar(self, *exprs):
        return self.rodar([self.D()], ids=['arco'], avaliar=exprs).get('avaliado')

    def test_mistura_interpola_cada_numero_do_mesmo_esqueleto(self):
        self.assertEqual(self.misturar("mistura('M0 0L10 10','M10 0L20 20',0.5)"), ['M5 0L15 15'])

    def test_mistura_esqueletos_diferentes_da_null(self):
        self.assertEqual(self.misturar("mistura('M0 0L10 10','M0 0Z',0.5)"), [None])

    def test_mistura_numero_igual_fica_como_esta(self):
        self.assertEqual(self.misturar("mistura('M0.50 0 A5 5 0 0 1 10 10','M0.50 0 A5 5 0 0 1 20 30',0.5)"),
                         ['M0.50 0 A5 5 0 0 1 15 20'])

    def test_mistura_texto_segue_as_casas_do_destino(self):
        self.assertEqual(self.misturar("mistura('12.3k','13.1k',0.3,true)", "mistura('12.3k','14k',0.3,true)"),
                         ['12.5k', '13k'])

    def test_mistura_texto_mantem_zero_a_esquerda(self):
        self.assertEqual(self.misturar("mistura('req 009','req 012',0.4,true)"), ['req 010'])


# Etapa 3 das animações — listas, células e rótulos reaproveitados.
def _vistos(id_):
    """Expressão JS: para cada filho direto de #id, se é o mesmo objeto de uma leitura anterior."""
    return f"[...document.getElementById('{id_}').children].map(c=>!!c._visto)"


def _txt(id_):
    return f"String(document.getElementById('{id_}').textContent)"


def _classes(outer):
    return (_attr('class', outer) or '').split()


@unittest.skipUnless(shutil.which('node'), 'node ausente')
class ListasNoNavegador(unittest.TestCase):
    """Usa o mesmo HARNESS e a mesma interface de MovimentoNoNavegador (modo 'render' com 'passos',
    'mesmos', 'avaliado'). O "mesmo objeto" de um filho em particular é lido por 'avaliar' com
    `c._visto`, a marca que o HARNESS põe nos descendentes antes de cada passo depois do primeiro.
    O clique na fase chama `li.children[0].onclick()` por 'avaliar' e lê `#trilha-cab`, que abrir()
    escreve antes do fetch (o fetch da simulação nunca resolve).
    """
    LISTAS = ['etapas', 'fases', 'hist', 'ativ', 'features', 'seq-bar', 'prov']
    rodar = MovimentoNoNavegador.rodar
    D = MovimentoNoNavegador.D

    def test_mesmos_dados_mantem_cada_item_e_celula_como_o_mesmo_objeto(self):
        p1, p2 = self.rodar([self.D(), self.D()], ids=self.LISTAS)['passos']
        for g in self.LISTAS:
            with self.subTest(g):
                self.assertGreater(p1[g]['n'], 0, f'#{g} sem filhos no DOM (ainda montado por innerHTML?)')
                self.assertEqual(p2[g]['n'], p1[g]['n'], f'#{g}: a contagem mudou com os mesmos dados')
                self.assertEqual(p2[g]['mesmos'], p2[g]['n'],
                                 f'#{g}: {p2[g]["n"] - p2[g]["mesmos"]} filhos recriados na segunda leitura')
                for f in p2[g]['filhos']:
                    self.assertNotRegex(f, r'\s(data-)?k="', f'#{g}: a chave virou atributo')

    def test_atividade_nova_no_topo_entra_primeiro_e_mantem_as_antigas(self):
        d2 = self.D()
        r = d2['rodada']
        antigas = [x['alvo'] for x in r['atividade']]
        r['atividade'] = [{'hora': '09:26', 'ferramenta': 'Edit', 'alvo': 'test_painel.py'}] + r['atividade']
        r['n_atividade'] += 1
        out = self.rodar([self.D(), d2], ids=['ativ'], avaliar=[_vistos('ativ'), _txt('ativ-cab')])
        p1, p2 = self.passos_de(out, 'ativ')
        self.assertEqual(p2['n'], p1['n'] + 1, 'a contagem de itens não subiu 1')
        self.assertEqual(p2['mesmos'], p1['n'], 'itens antigos de #ativ foram recriados')
        vistos, cab = out['avaliado']
        self.assertEqual(vistos, [False] + [True] * p1['n'], 'o item novo não é o primeiro, ou os antigos mudaram de objeto')
        self.assertIn('test_painel.py', p2['filhos'][0])
        for li, alvo in zip(p2['filhos'][1:], antigas):
            with self.subTest(alvo):
                self.assertIn(alvo, li, 'um item antigo passou a mostrar outra atividade')
        self.assertEqual(cab, '4 de 8')

    def passos_de(self, out, g):
        return [x[g] for x in out['passos']]

    def fases_andando(self):
        d2 = self.D()
        fs = d2['rodada']['fases']
        fs[3].update(estado='feita')               # grill: era a atual
        fs[4].update(estado='atual', hora='09:30')  # mockup: vira a atual
        return d2

    def test_fase_que_passa_a_feita_perde_aria_current_e_a_seguinte_ganha(self):
        out = self.rodar([self.D(), self.fases_andando()], ids=['fases'], avaliar=[_vistos('fases')])
        p1, p2 = self.passos_de(out, 'fases')
        self.assertEqual(_attr('aria-current', p1['filhos'][3]), 'step')
        self.assertEqual(out['avaliado'][0], [True] * 8, 'o li de alguma fase foi recriado')
        grill, mockup = p2['filhos'][3], p2['filhos'][4]
        self.assertIsNone(_attr('aria-current', grill), 'a fase que deixou de ser atual segue com aria-current')
        self.assertIn('feita', _classes(grill))
        self.assertEqual(_attr('aria-current', mockup), 'step')
        self.assertIn('atual', _classes(mockup))
        self.assertEqual(sum(_attr('aria-current', f) is not None for f in p2['filhos']), 1)

    def test_clique_na_fase_reaproveitada_abre_o_documento(self):
        clique = ("(()=>{const b=(document.getElementById('fases').children[2]||{children:[]}).children[0];"
                  "if(!b||typeof b.onclick!=='function')return 'sem onclick no botão';b.onclick();"
                  "return String(document.getElementById('trilha-cab').textContent)})()")
        out = self.rodar([self.D(), self.D()], ids=['fases'], avaliar=[_vistos('fases'), clique])
        vistos, cab = out['avaliado']
        self.assertTrue(vistos and vistos[2], 'o li da Pesquisa foi recriado na segunda leitura')
        self.assertEqual(cab, 'Pesquisa // faixa unica')

    def test_etapa_pendente_que_vira_feita_segue_o_mesmo_li_com_selo_verde(self):
        d2 = self.D()
        e = d2['estado']['etapas'][1]
        e['status'] = 'feita'
        e['provas']['teste'].update(resultado='verde', commit='beef1234cafe')
        out = self.rodar([self.D(), d2], ids=['etapas'], avaliar=[_vistos('etapas')])
        p1, p2 = self.passos_de(out, 'etapas')
        self.assertNotIn('feita', _classes(p1['filhos'][1]))
        self.assertTrue(out['avaliado'][0][1], 'o li da etapa 02 foi recriado')
        li = p2['filhos'][1]
        self.assertIn('feita', _classes(li))
        self.assertRegex(li, r'<span class="chip[^"]*">verde</span>', 'o selo da etapa feita não diz verde')
        self.assertIn('beef123', li)
        self.assertNotIn('implementando', li)

    def test_pergunta_pendente_respondida_segue_o_mesmo_li_sem_pend(self):
        d2 = self.D()
        d2['rodada']['historico'][2]['resposta'] = 'Meio segundo'
        out = self.rodar([self.D(), d2], ids=['hist'], avaliar=[_vistos('hist')])
        p1, p2 = self.passos_de(out, 'hist')
        self.assertIn('pend', _classes(p1['filhos'][2]))
        self.assertTrue(out['avaliado'][0][2], 'o li da pergunta respondida foi recriado')
        li = p2['filhos'][2]
        self.assertNotIn('pend', _classes(li), 'a pergunta respondida segue com a classe pend')
        self.assertIn('Meio segundo', li)
        self.assertNotIn('esperando resposta', li)

    def test_mudanca_de_estado_troca_palavra_percentual_e_requests(self):
        d2 = self.D()
        d2['momento'] = {'tipo': 'pausada', 'texto': 'Pausada na etapa 3 de 4'}
        e = d2['estado']['etapas'][1]
        e['status'] = 'feita'
        e['provas']['teste'].update(resultado='verde', commit='beef1234cafe')
        d2['sessao']['entrada'] = ENTRADA + [60_000]
        d2['sessao']['requests'] += 1
        out = self.rodar([self.D(), d2], ids=['etapas'], avaliar=[_txt('palavra'), _txt('pct'), _txt('n-req')])
        self.assertEqual(out['avaliado'], ['Pausada', '50', '023 req'])


class MovimentoNaPagina(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(AQUI, 'painel.html'), encoding='utf-8') as f:
            self.h = f.read()

    def desligados_no_reduz(self):
        sels = set()
        for m in re.finditer(r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{', self.h):
            i = j = m.end()
            n = 1
            while n and j < len(self.h):
                n += {'{': 1, '}': -1}.get(self.h[j], 0)
                j += 1
            for sel, corpo in re.findall(r'([^{}]+)\{([^{}]*)\}', self.h[i:j - 1]):
                if re.search(r'transition\s*:\s*none', corpo):
                    sels |= {' '.join(s.split()) for s in sel.split(',')}
        return sels

    def test_acento_registrado_com_property_e_transicao_no_body(self):
        self.assertRegex(self.h, r'@property\s+--acento\s*\{[^}]*syntax\s*:\s*[\'"]<color>[\'"]')
        self.assertRegex(self.h, r'(?:^|[}\s,])body\s*\{[^}]*transition\s*:[^;}]*--acento')

    def test_hachura_cresce_com_transicao_de_largura(self):
        self.assertRegex(self.h, r'\.hachura\s+\.cheio\s*\{[^}]*transition\s*:[^;}]*\bwidth\b')

    def test_movimento_reduzido_desliga_as_duas_transicoes(self):
        sels = self.desligados_no_reduz()
        self.assertIn('body', sels)
        self.assertIn('.hachura .cheio', sels)

    def test_script_consulta_movimento_reduzido(self):
        script = '\n'.join(re.findall(r'<script>([\s\S]*?)</script>', self.h))
        self.assertRegex(script, r'matchMedia\(\s*[\'"]\(prefers-reduced-motion:\s*reduce\)[\'"]\s*\)')

    def test_sem_restos_do_mockup(self):
        for t in ('mockup · simular', 'ACOES', 'dados de exemplo'):
            with self.subTest(t):
                self.assertNotIn(t, self.h)


if __name__ == '__main__':
    unittest.main()
