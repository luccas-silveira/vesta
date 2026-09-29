"""Testes do vesta.py. Cada teste monta um repositório git descartável."""
import http.server
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, 'vesta.py')
# GIT_* de fora (GIT_INDEX_FILE num `git commit -a`) apontaria os repositórios descartáveis
# para o índice do repositório que está commitando. Sai do ambiente do processo inteiro.
for _k in [k for k in os.environ if k.startswith('GIT_')]:
    del os.environ[_k]
ENV = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}


TESTE = 'test -f ok || { echo "FAIL test_um"; exit 1; }'  # imita um executor: cita o arquivo que falhou


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = os.path.realpath(self.tmp.name)
        for args in (['init', '-q'], ['config', 'user.email', 't@t'], ['config', 'user.name', 't'],
                     ['commit', '-q', '--allow-empty', '-m', 'raiz']):
            subprocess.run(['git', *args], cwd=self.r, check=True)
        self.caminho_estado = os.path.join(self.r, '.claude', 'vesta', 'estado.json')

    def tearDown(self):
        self.tmp.cleanup()

    def sf(self, *args, entrada=None, cwd=None, env=None):
        return subprocess.run(['python3', SCRIPT, *args], cwd=cwd or self.r, env=env or ENV,
                              input=entrada, capture_output=True, text=True)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.r, capture_output=True, text=True,
                              check=True).stdout.strip()

    def criar(self, teste=TESTE, etapas=None):
        d = {'plano': 'plano.md', 'teste': teste, 'tela': [],
             'etapas': etapas or [{'id': '1', 'titulo': 'um'}]}
        p = self.sf('criar', entrada=json.dumps(d))
        self.assertEqual(p.returncode, 0, p.stderr)

    def estado(self):
        with open(self.caminho_estado) as f:
            return json.load(f)

    def commit(self, nome):
        open(os.path.join(self.r, nome), 'w').close()
        self.git('add', '-A')
        self.git('commit', '-q', '-m', nome)

    def hook(self, evento, sid='s1', **extra):
        p = self.sf(evento, entrada=json.dumps({'session_id': sid, 'cwd': self.r, **extra}))
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def vermelho(self, arquivo='test_um'):
        """O escritor de teste commita os testes; depois a prova confirma o vermelho."""
        self.commit(arquivo)
        return self.sf('prova', 'vermelho', '1')

    def adotar(self, sid, comando='iniciar'):
        self.hook('hook-adocao', sid=sid, tool_name='Bash',
                  tool_input={'command': f'python3 ~/.claude/skills/vesta/scripts/vesta.py {comando}'})


class Nucleo(Base):
    def test_criar_grava_estado_esperando_plano_sem_sujar_a_arvore(self):
        self.criar()
        e = self.estado()
        self.assertEqual(e['espera'], 'plano')
        self.assertEqual(e['etapas'][0]['status'], 'pendente')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_criar_recusa_quando_ja_existe(self):
        self.criar()
        p = self.sf('criar', entrada=json.dumps({'teste': 'true', 'etapas': [{'id': '1', 'titulo': 'x'}]}))
        self.assertEqual(p.returncode, 1)
        self.assertIn('já existe', p.stderr)

    def test_criar_recusa_id_repetido_sem_gravar(self):
        p = self.sf('criar', entrada=json.dumps(
            {'teste': 'true', 'etapas': [{'id': '1', 'titulo': 'a'}, {'id': '1', 'titulo': 'b'}]}))
        self.assertEqual(p.returncode, 1)
        self.assertFalse(os.path.exists(self.caminho_estado))

    def test_iniciar_deixa_a_sessao_para_adocao(self):
        self.criar()
        self.assertEqual(self.sf('iniciar').returncode, 0)
        e = self.estado()
        self.assertIsNone(e['espera'])
        self.assertEqual(e['sessao'], 'adotar')

    def test_criar_fora_do_git_recusa(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.sf('criar', cwd=d, entrada=json.dumps({'teste': 'true', 'etapas': [{'id': '1', 'titulo': 'a'}]}))
            self.assertEqual(p.returncode, 1)
            self.assertIn('repositório git', p.stderr)

    def test_iniciar_recusa_arvore_suja(self):
        self.criar()
        open(os.path.join(self.r, 'pendente-do-usuario'), 'w').close()
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 1)
        self.assertIn('não commitadas', p.stderr)
        self.assertEqual(self.estado()['espera'], 'plano')

    def test_pausar_recusa_plano_nao_aprovado(self):
        self.criar()
        p = self.sf('pausar')
        self.assertEqual(p.returncode, 1)
        self.assertEqual(self.estado()['espera'], 'plano')

    def test_comando_de_subpasta_acha_a_raiz(self):
        os.makedirs(os.path.join(self.r, 'sub'))
        p = self.sf('criar', cwd=os.path.join(self.r, 'sub'),
                    entrada=json.dumps({'teste': 'true', 'etapas': [{'id': '1', 'titulo': 'a'}]}))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.exists(self.caminho_estado))


class Provas(Base):
    def setUp(self):
        super().setUp()
        self.criar()
        self.sf('iniciar')

    def test_arvore_suja_recusa(self):
        open(os.path.join(self.r, 'solto'), 'w').close()
        p = self.sf('prova', 'vermelho', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('não commitada', p.stderr)

    def test_vermelho_recusa_teste_que_ja_passa(self):
        self.commit('ok')
        p = self.vermelho()
        self.assertEqual(p.returncode, 1)
        self.assertIn('passaram antes', p.stderr)
        self.assertIsNone(self.estado()['etapas'][0]['provas']['teste']['vermelho'])

    def test_vermelho_recusa_comando_que_nao_roda(self):
        os.remove(self.caminho_estado)
        self.criar(teste='comando-que-nao-existe-xyz')
        p = self.vermelho()
        self.assertEqual(p.returncode, 1)
        self.assertIn('não roda', p.stderr)
        self.assertIsNone(self.estado()['etapas'][0]['provas']['teste']['vermelho'])

    def test_vermelho_recusa_falha_que_nao_cita_os_testes_novos(self):
        os.remove(self.caminho_estado)
        self.criar(teste='echo "npm ERR! missing script: test"; exit 1')
        p = self.vermelho()
        self.assertEqual(p.returncode, 1)
        self.assertIn('não cita', p.stderr)

    def test_vermelho_recusa_commit_sem_arquivo(self):
        self.git('commit', '-q', '--allow-empty', '-m', 'vazio')
        p = self.sf('prova', 'vermelho', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('nenhum arquivo', p.stderr)

    def test_teste_recusa_testes_mexidos_depois_do_vermelho(self):
        self.vermelho()
        with open(os.path.join(self.r, 'test_um'), 'w') as f:
            f.write('afrouxado')
        self.commit('ok')
        p = self.sf('prova', 'teste', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('mudaram depois do vermelho', p.stderr)
        self.assertIsNone(self.estado()['etapas'][0]['provas']['teste']['vermelho'])

    def test_teste_exige_vermelho_antes(self):
        p = self.sf('prova', 'teste', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('confirme o vermelho', p.stderr)

    def test_ciclo_vermelho_verde_concluir(self):
        self.assertEqual(self.vermelho().returncode, 0)
        self.commit('ok')
        self.assertEqual(self.sf('prova', 'teste', '1').returncode, 0)
        self.assertEqual(self.sf('concluir', '1').returncode, 0)
        self.assertEqual(self.estado()['etapas'][0]['status'], 'feita')

    def test_commit_depois_do_verde_invalida_a_prova(self):
        self.vermelho()
        self.commit('ok')
        self.sf('prova', 'teste', '1')
        self.commit('outro')
        p = self.sf('concluir', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('não está verde neste commit', p.stderr)

    def test_concluir_aceita_artefato_nao_rastreado_do_teste(self):
        os.remove(self.caminho_estado)
        self.criar(teste='test -f ok && touch relatorio.txt || { echo "FAIL test_um"; exit 1; }')
        self.sf('iniciar')
        self.vermelho()
        self.commit('ok')
        self.assertEqual(self.sf('prova', 'teste', '1').returncode, 0)
        p = self.sf('concluir', '1')
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_concluir_recusa_mudanca_rastreada_depois_da_prova(self):
        self.vermelho()
        self.commit('ok')
        self.sf('prova', 'teste', '1')
        with open(os.path.join(self.r, 'ok'), 'w') as f:
            f.write('mexido')
        p = self.sf('concluir', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('rastreado', p.stderr)

    def test_oitavo_vermelho_trava_a_etapa(self):
        self.vermelho()
        for _ in range(8):
            p = self.sf('prova', 'teste', '1')
            self.assertEqual(p.returncode, 1)
        x = self.estado()['etapas'][0]
        self.assertEqual(x['status'], 'travada')
        self.assertEqual(x['provas']['teste']['tentativas'], 8)
        self.assertIn('travada', p.stderr)

    def test_projeto_sem_commit_recusa(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
            self.sf('criar', cwd=d, entrada=json.dumps({'teste': 'true', 'etapas': [{'id': '1', 'titulo': 'a'}]}))
            p = self.sf('prova', 'vermelho', '1', cwd=d)
            self.assertEqual(p.returncode, 1)
            self.assertIn('pelo menos um commit', p.stderr)


class Parada(Base):
    def setUp(self):
        super().setUp()
        self.criar()
        self.sf('iniciar')
        self.adotar('s1')

    def test_sem_estado_libera(self):
        os.remove(self.caminho_estado)
        self.assertIsNone(self.hook('hook-parada'))

    def test_estado_ilegivel_libera(self):
        with open(self.caminho_estado, 'w') as f:
            f.write('{quebrado')
        self.assertIsNone(self.hook('hook-parada'))

    def test_bloqueia_so_com_o_agente(self):
        out = self.hook('hook-parada', sid='s1')
        self.assertEqual(out['decision'], 'block')
        self.assertIn('Etapa 1', out['reason'])
        self.assertIn('prova vermelho', out['reason'])
        self.assertNotIn('systemMessage', out)
        self.assertEqual(self.estado()['sessao'], 's1')

    def test_outra_sessao_libera(self):
        self.hook('hook-parada', sid='s1')
        self.assertIsNone(self.hook('hook-parada', sid='s2'))

    def test_fora_do_git_libera(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, '.claude', 'vesta'))
            with open(os.path.join(d, '.claude', 'vesta', 'estado.json'), 'w') as f:
                json.dump(self.estado(), f)
            p = self.sf('hook-parada', cwd=d, entrada=json.dumps({'session_id': 's1', 'cwd': d}))
            self.assertEqual(p.stdout.strip(), '')

    def test_hook_prefere_o_cwd_da_entrada(self):
        with tempfile.TemporaryDirectory() as outro:
            p = self.sf('hook-parada', env={**ENV, 'CLAUDE_PROJECT_DIR': outro},
                        entrada=json.dumps({'session_id': 's1', 'cwd': self.r}))
            self.assertEqual(json.loads(p.stdout)['decision'], 'block')

    def test_editar_arquivo_novo_conta_como_progresso(self):
        caminho = os.path.join(self.r, 'novo.py')
        for i in range(8):
            with open(caminho, 'w') as f:
                f.write(str(i))
            self.assertEqual(self.hook('hook-parada')['decision'], 'block')

    def test_razao_orienta_a_pausar_se_o_usuario_pediu(self):
        self.assertIn('pausar', self.hook('hook-parada')['reason'])

    def test_silenciar_so_quando_a_parada_seria_bloqueada(self):
        ent = lambda sid: json.dumps({'session_id': sid, 'cwd': self.r})
        self.assertEqual(self.sf('silenciar', entrada=ent('s1')).returncode, 0)
        self.assertEqual(self.sf('silenciar', entrada=ent('s2')).returncode, 1)
        self.assertEqual(self.estado()['bloqueios']['seguidos'], 0)
        for _ in range(5):
            self.hook('hook-parada')
        self.assertEqual(self.sf('silenciar', entrada=ent('s1')).returncode, 1)

    def test_guarda_repassa_a_entrada_ao_hook_original(self):
        guarda = self.sf('guarda').stdout
        self.assertTrue(guarda.startswith('__e='), guarda)
        for sid, esperado in (('s2', 'repassa'), ('s1', '')):
            entrada = json.dumps({'session_id': sid, 'cwd': self.r})
            p = subprocess.run(['sh', '-c', guarda + 'grep -q s2 && echo repassa'], cwd=self.r,
                               env=ENV, input=entrada, capture_output=True, text=True)
            self.assertEqual(p.stdout.strip(), esperado, sid)

    def test_plano_esperando_aprovacao_libera(self):
        os.remove(self.caminho_estado)
        self.criar()
        self.assertIsNone(self.hook('hook-parada'))

    def test_tarefa_em_segundo_plano_libera(self):
        self.assertIsNone(self.hook('hook-parada', background_tasks=[{'id': 'x'}]))

    def test_todas_feitas_libera(self):
        self.vermelho()
        self.commit('ok')
        self.sf('prova', 'teste', '1')
        self.sf('concluir', '1')
        self.assertIsNone(self.hook('hook-parada'))

    def test_sexto_bloqueio_sem_progresso_libera_e_interrompe(self):
        for _ in range(5):
            self.assertEqual(self.hook('hook-parada')['decision'], 'block')
        self.assertIsNone(self.hook('hook-parada'))
        e = self.estado()
        self.assertEqual(e['espera'], 'interrompida')
        self.assertIn('sem progresso', e['motivo'])

    def test_progresso_zera_o_contador(self):
        for _ in range(4):
            self.hook('hook-parada')
        open(os.path.join(self.r, 'rascunho'), 'w').close()
        for _ in range(5):
            self.assertEqual(self.hook('hook-parada')['decision'], 'block')


class Retomada(Base):
    def setUp(self):
        super().setUp()
        self.criar()
        self.sf('iniciar')
        self.adotar('s1')

    def test_sessao_nova_avisa_execucao_de_outra_sessao(self):
        out = self.hook('hook-inicio', sid='s2')
        self.assertIn('etapa 1', out['systemMessage'])
        self.assertIn('/vesta-retomar', out['systemMessage'])
        self.assertEqual(out['hookSpecificOutput']['hookEventName'], 'SessionStart')

    def tearDown(self):
        # hook-inicio em projeto com Vesta sobe o painel (etapa 5); derruba o deste projeto
        for i in range(100):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{4700 + i}/quem', timeout=0.3) as r:
                    if r.read().decode().strip() != f'vesta-painel {self.r}':
                        continue
            except Exception:
                continue
            for pid in subprocess.run(['lsof', '-ti', f'tcp:{4700 + i}', '-sTCP:LISTEN'],
                                      capture_output=True, text=True).stdout.split():
                subprocess.run(['kill', pid], capture_output=True)
        super().tearDown()

    def sem_aviso(self, out):
        """Sem aviso: nada, ou só a linha do painel (etapa 5)."""
        if out is not None:
            self.assertEqual(out.get('systemMessage', '').count('\n'), 0)
            self.assertNotIn('etapa', out.get('systemMessage', ''))
            self.assertIn('Painel deste projeto', out['hookSpecificOutput']['additionalContext'])

    def test_mesma_sessao_sem_aviso(self):
        self.sem_aviso(self.hook('hook-inicio', sid='s1'))

    def test_sem_estado_sem_aviso(self):
        os.remove(self.caminho_estado)
        self.sem_aviso(self.hook('hook-inicio', sid='s2'))

    def test_estado_ilegivel_avisa(self):
        with open(self.caminho_estado, 'w') as f:
            f.write('{')
        self.assertIn('ilegível', self.hook('hook-inicio', sid='s2')['systemMessage'])

    def test_estado_com_formato_errado_avisa_sem_traceback(self):
        with open(self.caminho_estado, 'w') as f:
            f.write('{}')
        self.assertIn('ilegível', self.hook('hook-inicio', sid='s2')['systemMessage'])
        self.assertIsNone(self.hook('hook-parada', sid='s1'))
        p = self.sf('mostrar')
        self.assertEqual(p.returncode, 1)
        self.assertNotIn('Traceback', p.stderr)

    def test_retomar_passa_a_execucao_para_a_sessao_seguinte(self):
        self.assertEqual(self.sf('retomar').returncode, 0)
        self.adotar('s2', 'retomar')
        self.assertEqual(self.hook('hook-parada', sid='s2')['decision'], 'block')
        self.assertEqual(self.estado()['sessao'], 's2')

    def test_retomar_recusa_plano_nao_aprovado(self):
        os.remove(self.caminho_estado)
        self.criar()
        p = self.sf('retomar')
        self.assertEqual(p.returncode, 1)
        self.assertIn('iniciar', p.stderr)

    def test_pausar_libera_e_avisa_com_motivo(self):
        self.sf('pausar', 'fim', 'do', 'dia')
        self.assertIsNone(self.hook('hook-parada', sid='s1'))
        self.assertIn('fim do dia', self.hook('hook-inicio', sid='s1')['systemMessage'])

    def test_retomar_destrava_etapa(self):
        self.vermelho()
        for _ in range(8):
            self.sf('prova', 'teste', '1')
        self.assertIn('travou', self.hook('hook-inicio', sid='s2')['systemMessage'])
        self.sf('retomar')
        x = self.estado()['etapas'][0]
        self.assertEqual(x['status'], 'pendente')
        self.assertEqual(x['provas']['teste']['tentativas'], 0)

    def test_adicionar_reabre_a_execucao(self):
        self.vermelho()
        self.commit('ok')
        self.sf('prova', 'teste', '1')
        self.sf('concluir', '1')
        p = self.sf('adicionar', entrada=json.dumps([{'id': '2', 'titulo': 'ajuste'}]))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.adotar('s1', 'adicionar')
        self.assertEqual(self.hook('hook-parada', sid='s1')['decision'], 'block')

    def test_adicionar_recusa_com_etapa_travada(self):
        self.vermelho()
        for _ in range(8):
            self.sf('prova', 'teste', '1')
        p = self.sf('adicionar', entrada=json.dumps([{'id': '2', 'titulo': 'ajuste'}]))
        self.assertEqual(p.returncode, 1)
        self.assertIn('retomar', p.stderr)


class Adocao(Base):
    def setUp(self):
        super().setUp()
        self.criar()
        self.sf('iniciar')

    def test_outra_sessao_que_para_nao_adota(self):
        self.assertIsNone(self.hook('hook-parada', sid='s2'))
        self.assertEqual(self.estado()['sessao'], 'adotar')

    def test_so_o_comando_da_vesta_adota(self):
        self.hook('hook-adocao', sid='s2', tool_name='Bash', tool_input={'command': 'ls'})
        self.assertEqual(self.estado()['sessao'], 'adotar')
        self.adotar('s1')
        self.assertEqual(self.estado()['sessao'], 's1')

    def test_dono_nao_e_trocado(self):
        self.adotar('s1')
        self.adotar('s2', 'retomar')
        self.assertEqual(self.estado()['sessao'], 's1')

    def test_fechar_apaga_o_estado(self):
        self.assertEqual(self.sf('fechar').returncode, 0)
        self.assertFalse(os.path.exists(self.caminho_estado))


PASTA_MOCK = 'docs/vesta/mockups/2026-09-28-x'
MOCK = PASTA_MOCK + '/index.html'


def provas(pasta, n=1):
    """As provas da verificação (VER-05, VER-10, VER-16) numa pasta, com o mesmo N."""
    return {f'{pasta}/relatorio.md': 'rodada 1',
            f'{pasta}/r{n}-375.png': 'png', f'{pasta}/r{n}-1440.png': 'png',
            f'{pasta}/r{n}-detector-375.json': '[]', f'{pasta}/r{n}-detector-1440.json': '[]'}


def direcoes(tela='painel'):
    """As duas direções da tela nova e os quatro prints delas (passo 3 da vesta-interface)."""
    d = 'docs/design/mockups'
    return {f'{d}/{tela}-a.html': '<p>a', f'{d}/{tela}-b.html': '<p>b',
            f'{d}/{tela}-a-375.png': 'png', f'{d}/{tela}-a-1440.png': 'png',
            f'{d}/{tela}-b-375.png': 'png', f'{d}/{tela}-b-1440.png': 'png'}


def completo():
    return {MOCK: '<p>mock', **provas(PASTA_MOCK), **direcoes()}


class ComMockup(Base):
    """Ferramentas para montar mockup, provas e direções no repositório descartável."""
    TELA = [{'id': '1', 'titulo': 'tela', 'tela': True}]

    def criar_com(self, **extra):
        d = {'plano': 'plano.md', 'teste': TESTE, 'tela': [], 'etapas': self.TELA, **extra}
        p = self.sf('criar', entrada=json.dumps(d))
        self.assertEqual(p.returncode, 0, p.stderr)

    def escrever(self, arquivos):
        for rel, conteudo in arquivos.items():
            caminho = os.path.join(self.r, rel)
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, 'w') as f:
                f.write(conteudo)

    def commitar(self, arquivos, msg='mockup'):
        self.escrever(arquivos)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', msg)

    def sem(self, *nomes, base=None):
        """O conjunto completo menos os arquivos cujo caminho termina em algum dos nomes."""
        return {k: v for k, v in (base or completo()).items() if not k.endswith(nomes)}

    def ignorar(self, *rels):
        """Presente no disco, fora do git, com a árvore limpa."""
        with open(os.path.join(self.r, '.git', 'info', 'exclude'), 'a') as f:
            f.write(''.join(r + '\n' for r in rels))

    def recusa_iniciar(self, falta):
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertRegex(p.stderr, falta)
        self.assertEqual(self.estado()['espera'], 'plano')
        return p


class Mockup(ComMockup):
    """Plano com tela não executa sem mockup commitado e as provas da verificação dele."""

    # --- o que já valia, com as provas acrescentadas

    def test_iniciar_recusa_etapa_de_tela_sem_mockup(self):
        self.criar_com()
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 1)
        self.assertIn('mockup', p.stderr)
        self.assertEqual(self.estado()['espera'], 'plano')

    def test_iniciar_recusa_pasta_de_tela_sem_mockup(self):
        self.criar_com(etapas=[{'id': '1', 'titulo': 'um'}], tela=['src/ui'])
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 1)
        self.assertIn('mockup', p.stderr)

    def test_iniciar_recusa_mockup_que_nao_esta_no_git(self):
        self.commitar(self.sem('index.html'))
        self.criar_com(mockup=MOCK)
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 1)
        self.assertIn('mockup', p.stderr)

    def test_iniciar_aceita_mockup_commitado_com_as_provas(self):
        self.commitar(completo())
        self.criar_com(mockup=MOCK)
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIsNone(self.estado()['espera'])

    def test_iniciar_sem_tela_dispensa_mockup(self):
        self.criar()
        self.assertEqual(self.sf('iniciar').returncode, 0)
        self.assertIsNone(self.estado()['mockup'])

    def test_adicionar_tela_sem_mockup_recusa_sem_gravar(self):
        self.criar()
        self.sf('iniciar')
        p = self.sf('adicionar', entrada=json.dumps([{'id': '2', 'titulo': 't', 'tela': True}]))
        self.assertEqual(p.returncode, 1)
        self.assertIn('mockup', p.stderr)
        self.assertEqual(len(self.estado()['etapas']), 1)

    def test_adicionar_aceita_objeto_com_mockup_e_provas_commitados(self):
        self.criar()
        self.sf('iniciar')
        self.commitar(completo())
        p = self.sf('adicionar', entrada=json.dumps(
            {'mockup': MOCK, 'etapas': [{'id': '2', 'titulo': 't', 'tela': True}]}))
        self.assertEqual(p.returncode, 0, p.stderr)
        e = self.estado()
        self.assertEqual(e['mockup'], MOCK)
        self.assertEqual(len(e['etapas']), 2)

    # --- provas da verificação na pasta do mockup

    def test_iniciar_recusa_sem_cada_prova_dizendo_qual_falta(self):
        faltas = {'relatorio.md': r'relatorio\.md', 'r1-375.png': r'r(1|<N>)-375\.png',
                  'r1-1440.png': r'r(1|<N>)-1440\.png',
                  'r1-detector-375.json': r'r(1|<N>)-detector-375\.json',
                  'r1-detector-1440.json': r'r(1|<N>)-detector-1440\.json'}
        self.criar_com(mockup=MOCK)
        for nome, falta in faltas.items():
            with self.subTest(falta=nome):
                self.git('rm', '-q', '-r', '--ignore-unmatch', 'docs')
                self.commitar(self.sem(nome), msg=f'sem {nome}')
                self.recusa_iniciar(falta)

    def test_iniciar_recusa_provas_presentes_mas_fora_do_git(self):
        self.commitar(self.sem('relatorio.md'))
        self.ignorar(f'{PASTA_MOCK}/relatorio.md')
        self.escrever({f'{PASTA_MOCK}/relatorio.md': 'rodada 1'})
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'relatorio\.md')

    def test_iniciar_recusa_prints_e_detectores_de_rodadas_diferentes(self):
        misturado = {k: v for k, v in completo().items() if '/r1-' not in k}
        misturado.update({f'{PASTA_MOCK}/r1-375.png': 'png', f'{PASTA_MOCK}/r1-detector-375.json': '[]',
                          f'{PASTA_MOCK}/r2-1440.png': 'png', f'{PASTA_MOCK}/r2-detector-1440.json': '[]'})
        self.commitar(misturado)
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'1440|375')

    def test_iniciar_aceita_provas_de_outra_rodada(self):
        self.commitar({MOCK: '<p>mock', **provas(PASTA_MOCK, n=3), **direcoes()})
        self.criar_com(mockup=MOCK)
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_iniciar_recusa_provas_fora_da_pasta_do_mockup(self):
        self.commitar({MOCK: '<p>mock', **provas('docs/vesta/mockups/outra'), **direcoes()})
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'relatorio\.md')

    def test_iniciar_recusa_detector_que_nao_e_json(self):
        self.commitar({**completo(), f'{PASTA_MOCK}/r1-detector-1440.json': 'detector: 0 achados'})
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'r(1|<N>)-detector-1440\.json')

    def test_adicionar_recusa_sem_relatorio_sem_gravar(self):
        self.criar()
        self.sf('iniciar')
        self.commitar(self.sem('relatorio.md'))
        p = self.sf('adicionar', entrada=json.dumps(
            {'mockup': MOCK, 'etapas': [{'id': '2', 'titulo': 't', 'tela': True}]}))
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('relatorio.md', p.stderr)
        e = self.estado()
        self.assertEqual(len(e['etapas']), 1)
        self.assertIsNone(e['mockup'])

    # --- direções da etapa 19

    def test_iniciar_recusa_sem_cada_direcao_dizendo_qual_falta(self):
        self.criar_com(mockup=MOCK)
        for nome in ('-a.html', '-b.html', '-a-375.png', '-a-1440.png', '-b-375.png', '-b-1440.png'):
            with self.subTest(falta=nome):
                self.git('rm', '-q', '-r', '--ignore-unmatch', 'docs')
                self.commitar(self.sem(nome), msg=f'sem {nome}')
                self.recusa_iniciar(r'(painel|<tela>)' + nome.replace('.', r'\.'))

    def test_iniciar_recusa_direcoes_de_telas_diferentes(self):
        so_a = {k: v for k, v in direcoes('painel').items() if '-a' in k}
        so_b = {k: v for k, v in direcoes('lista').items() if '-b' in k}
        self.commitar({MOCK: '<p>mock', **provas(PASTA_MOCK), **so_a, **so_b})
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'-b|-a')

    def test_iniciar_recusa_direcoes_fora_do_git(self):
        d = direcoes()
        self.commitar(self.sem(*d))
        self.ignorar(*d)
        self.escrever(d)
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'(painel|<tela>)-a')

    def test_adicionar_recusa_sem_direcao_b_sem_gravar(self):
        self.criar()
        self.sf('iniciar')
        self.commitar(self.sem('-b.html'))
        p = self.sf('adicionar', entrada=json.dumps(
            {'mockup': MOCK, 'etapas': [{'id': '2', 'titulo': 't', 'tela': True}]}))
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertRegex(p.stderr, r'(painel|<tela>)-b\.html')
        self.assertEqual(len(self.estado()['etapas']), 1)

    def test_tela_existente_dispensa_as_direcoes(self):
        self.commitar({MOCK: '<p>mock', **provas(PASTA_MOCK)})
        self.criar_com(mockup=MOCK, tela_existente=True)
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_tela_existente_mantem_as_outras_provas(self):
        self.commitar({MOCK: '<p>mock', **self.sem('relatorio.md', base=provas(PASTA_MOCK))})
        self.criar_com(mockup=MOCK, tela_existente=True)
        self.recusa_iniciar(r'relatorio\.md')

    def test_tela_nova_sem_direcoes_recusa(self):
        self.commitar({MOCK: '<p>mock', **provas(PASTA_MOCK)})
        self.criar_com(mockup=MOCK)
        self.recusa_iniciar(r'(painel|<tela>)-a\.html')


class ConcluirTela(ComMockup):
    """Etapa com tela só conclui com as provas da verificação dela em <pasta do mockup>/etapa-<id>/."""
    ETAPA = PASTA_MOCK + '/etapa-1'

    def setUp(self):
        super().setUp()
        self.commitar(completo())
        self.criar_com(mockup=MOCK, etapas=[{'id': '1', 'titulo': 'tela', 'tela': True},
                                            {'id': '2', 'titulo': 'sem tela'}])
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 0, p.stderr)

    def verde(self, id_='1'):
        self.commit('test_um')
        self.assertEqual(self.sf('prova', 'vermelho', id_).returncode, 0)
        self.commit('ok')
        p = self.sf('prova', 'teste', id_)
        self.assertEqual(p.returncode, 0, p.stderr)

    def status(self, id_):
        return next(x['status'] for x in self.estado()['etapas'] if x['id'] == id_)

    def recusa_concluir(self, falta):
        p = self.sf('concluir', '1')
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertRegex(p.stderr, falta)
        self.assertEqual(self.status('1'), 'pendente')

    def com_provas(self, arquivos):
        self.commitar(arquivos, msg='provas da etapa')
        p = self.sf('prova', 'teste', '1')
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_verde_sem_provas_da_etapa_recusa(self):
        self.verde()
        self.recusa_concluir(r'etapa-1')

    def test_verde_com_provas_da_etapa_conclui(self):
        self.verde()
        self.com_provas(provas(self.ETAPA))
        p = self.sf('concluir', '1')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.status('1'), 'feita')

    def test_recusa_sem_cada_prova_da_etapa_dizendo_qual_falta(self):
        self.verde()
        faltas = {'relatorio.md': r'relatorio\.md', '-375.png': r'r(1|<N>)-375\.png',
                  '-1440.png': r'r(1|<N>)-1440\.png',
                  '-detector-375.json': r'r(1|<N>)-detector-375\.json',
                  '-detector-1440.json': r'r(1|<N>)-detector-1440\.json'}
        for nome, falta in faltas.items():
            with self.subTest(falta=nome):
                self.git('rm', '-q', '-r', '--ignore-unmatch', self.ETAPA)
                self.com_provas(self.sem(nome, base=provas(self.ETAPA)))
                self.recusa_concluir(falta)

    def test_provas_da_etapa_fora_do_git_recusa(self):
        self.verde()
        p = provas(self.ETAPA)
        self.ignorar(*p)
        self.escrever(p)
        self.recusa_concluir(r'relatorio\.md|etapa-1')

    def test_provas_de_outra_etapa_nao_valem(self):
        self.verde()
        self.com_provas(provas(PASTA_MOCK + '/etapa-2'))
        self.recusa_concluir(r'etapa-1')

    def test_detector_da_etapa_que_nao_e_json_recusa(self):
        self.verde()
        self.com_provas({**provas(self.ETAPA), f'{self.ETAPA}/r1-detector-375.json': 'sem achados'})
        self.recusa_concluir(r'r(1|<N>)-detector-375\.json')

    def test_etapa_sem_tela_conclui_sem_provas(self):
        self.verde('2')
        p = self.sf('concluir', '2')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.status('2'), 'feita')


class ComPainel(Base):
    """Servidor real do painel da raiz, em subprocesso, na porta da raiz."""
    PRAZO = 1.5  # VESTA_PRAZO_ABERTO do servidor de teste (padrão real: 10 s)

    def setUp(self):
        super().setUp()
        import painel
        self.porta = painel.porta(self.r)
        self.fora = tempfile.TemporaryDirectory()  # cwd do processo: o comando usa o argumento
        self.addCleanup(self.fora.cleanup)

    def servir(self, env=None, **prazos):
        for _ in range(100):  # porta da raiz ocupada por outro painel: a seguinte, como achar()
            if not self.escuta():
                break
            self.porta = 4700 + (self.porta - 4700 + 1) % 100
        env = {**(env or ENV), 'VESTA_PRAZO_ABERTO': str(self.PRAZO),
               **{f'VESTA_PRAZO_{k.upper()}': str(v) for k, v in prazos.items()}}
        p = subprocess.Popen(['python3', os.path.join(AQUI, 'painel.py'), 'servir', self.r,
                              str(self.porta)], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(p.wait)
        self.addCleanup(p.kill)
        fim = time.time() + 5
        while not self.escuta():
            if time.time() > fim:
                self.fail('servidor não abriu a porta')
            time.sleep(0.05)
        return p

    def escuta(self):
        try:
            socket.create_connection(('127.0.0.1', self.porta), timeout=0.3).close()
            return True
        except OSError:
            return False

    def estado(self):
        urllib.request.urlopen(f'http://127.0.0.1:{self.porta}/estado', timeout=5).read()


class Aberto(ComPainel):
    """`vesta.py aberto <cwd>`: 0 com a página do painel da raiz aberta; 1 no resto; mudo."""

    def aberto(self, cwd=None):
        p = self.sf('aberto', cwd or self.r, cwd=self.fora.name)
        self.assertEqual((p.stdout, p.stderr), ('', ''))
        return p.returncode

    def test_sem_painel_sai_1(self):
        self.assertEqual(self.aberto(), 1)

    def test_painel_sem_pagina_sai_1(self):
        self.servir()
        self.assertEqual(self.aberto(), 1)

    def test_pagina_aberta_sai_0(self):
        self.servir()
        self.estado()
        self.assertEqual(self.aberto(), 0)

    def test_subpasta_usa_a_raiz(self):
        os.makedirs(os.path.join(self.r, 'a', 'b'))
        self.servir()
        self.estado()
        self.assertEqual(self.aberto(os.path.join(self.r, 'a', 'b')), 0)

    def test_pagina_fechada_pelo_prazo_sai_1(self):
        self.servir()
        self.estado()
        time.sleep(self.PRAZO + 0.3)
        self.assertEqual(self.aberto(), 1)

    def test_erro_sai_1_sem_saida(self):
        self.assertEqual(self.aberto(os.path.join(self.r, 'nao-existe', 'x')), 1)
        p = self.sf('aberto', cwd=self.fora.name)  # sem argumento
        self.assertEqual((p.returncode, p.stdout, p.stderr), (1, '', ''))


def porta_livre():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Knobler:
    """Knobler falso: POST /ask, GET /ask/<id>, POST /ask/<id>/cancel; registra os pedidos."""

    def __init__(self):
        self.pedidos = []  # (método, caminho, corpo JSON ou None)
        self.estados = {}  # id -> o que GET /ask/<id> devolve
        dono = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def devolver(self, d):
                corpo = json.dumps(d).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_POST(self):
                bruto = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                try:
                    corpo = json.loads(bruto) if bruto else None
                except ValueError:
                    corpo = None
                dono.pedidos.append(('POST', self.path, corpo))
                self.devolver({'ok': True})

            def do_GET(self):
                dono.pedidos.append(('GET', self.path, None))
                self.devolver(dono.estados.get(self.path.rsplit('/', 1)[-1],
                                               {'answered': False, 'cancelled': False}))

        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.srv.daemon_threads = True
        self.porta = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def posts(self, caminho):
        return [c for m, p, c in list(self.pedidos) if m == 'POST' and p == caminho]


Q = [{'question': 'Quais cores?', 'header': 'Cores', 'multiSelect': True,
      'options': [{'label': 'Azul', 'description': 'a'}, {'label': 'Verde', 'description': 'v'}]},
     {'question': 'Qual nome?', 'header': 'Nome', 'multiSelect': False,
      'options': [{'label': 'Vesta', 'description': 'v'}, {'label': 'Juno', 'description': 'j'}]}]
RESP = {'Quais cores?': {'labels': ['Azul', 'Verde'], 'text': ''},
        'Qual nome?': {'labels': ['Vesta'], 'text': 'Héstia'}}  # texto livre vence os rótulos
ESPERADO = {'Quais cores?': 'Azul, Verde', 'Qual nome?': 'Héstia'}


class Menu(ComPainel):
    """`vesta.py hook-menu` (PreToolUse de AskUserQuestion): painel e Knobler, vale a 1ª resposta."""
    ID = 'menu-tu1'

    def setUp(self):
        super().setUp()
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        # KNOBLER_PORT sempre definido: nunca a porta real 4477. Porta livre = Knobler fora do ar.
        self.env = {**ENV, 'HOME': self.home.name, 'KNOBLER_PORT': str(porta_livre()),
                    'VESTA_INTERVALO_MENU': '0.2'}

    def knobler(self):
        k = Knobler()
        self.addCleanup(k.fechar)
        self.env['KNOBLER_PORT'] = str(k.porta)
        return k

    def abrir(self, **prazos):
        """Painel no ar com a página aberta (um GET /estado)."""
        srv = self.servir(env=self.env, **prazos)
        self.estado()
        return srv

    def menu(self):
        p = subprocess.Popen(['python3', SCRIPT, 'hook-menu'], cwd=self.r, env=self.env,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: p.poll() is None and p.kill())
        p.stdin.write(json.dumps({'session_id': 's1', 'cwd': self.r, 'hook_event_name': 'PreToolUse',
                                  'tool_name': 'AskUserQuestion', 'tool_use_id': 'tu1',
                                  'tool_input': {'questions': Q}}))
        p.stdin.close()
        return p

    def fim(self, p, prazo=8):
        try:
            p.wait(timeout=prazo)
        except subprocess.TimeoutExpired:
            self.fail(f'o hook não saiu em {prazo} s')
        err = p.stderr.read()
        self.assertEqual(p.returncode, 0, err)
        return p.stdout.read()

    def saida(self, answers):
        return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                                       'updatedInput': {'questions': Q, 'answers': answers}}}

    def get(self, caminho):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.porta}{caminho}', timeout=5) as r:
            return json.loads(r.read())

    def pergunta(self):
        return self.get(f'/pergunta/{self.ID}')['estado']

    def responder(self):
        req = urllib.request.Request(f'http://127.0.0.1:{self.porta}/resposta/{self.ID}',
                                     data=json.dumps({'answers': RESP}).encode(), method='POST')
        urllib.request.urlopen(req, timeout=5).read()

    def ate(self, cond, oque, prazo=5):
        fim = time.time() + prazo
        while not cond():
            if time.time() > fim:
                self.fail(f'esperando {oque}')
            time.sleep(0.05)

    def no_painel(self):
        self.ate(lambda: self.pergunta() != 'desconhecida', 'a pergunta no painel')

    def no_knobler(self, k):
        self.ate(lambda: k.posts('/ask'), 'a pergunta no Knobler')

    def respostas(self):
        caminho = os.path.join(self.home.name, '.claude', 'vesta', 'respostas.jsonl')
        with open(caminho) as f:
            return [{k: l[k] for k in ('tool_use_id', 'onde')} for l in map(json.loads, f)]

    def cancelou(self, k):
        return bool(k.posts(f'/ask/{self.ID}/cancel'))

    def test_sem_painel_sai_mudo_rapido_sem_tocar_no_knobler(self):
        k = self.knobler()
        t = time.time()
        self.assertEqual(self.fim(self.menu(), prazo=5), '')
        self.assertLess(time.time() - t, 2)
        self.assertEqual(k.pedidos, [])

    def test_painel_sem_pagina_aberta_sai_mudo_rapido_sem_tocar_no_knobler(self):
        k = self.knobler()
        self.servir(env=self.env)  # no ar, mas nenhum GET /estado: aberto false
        t = time.time()
        self.assertEqual(self.fim(self.menu(), prazo=5), '')
        self.assertLess(time.time() - t, 2)
        self.assertEqual(k.pedidos, [])
        self.assertEqual(self.pergunta(), 'desconhecida')

    def test_resposta_no_painel_sem_knobler_sai_como_allow_com_answers(self):
        self.abrir()
        p = self.menu()
        self.no_painel()
        self.assertEqual(self.get('/estado')['perguntas'],
                         [{'id': self.ID, 'questions': Q, 'knobler': False, 'estado': 'pendente'}])
        self.assertIsNone(p.poll())  # espera a resposta
        self.responder()
        self.assertEqual(json.loads(self.fim(p)), self.saida(ESPERADO))
        self.assertEqual(self.respostas(), [{'tool_use_id': 'tu1', 'onde': 'painel'}])

    def test_knobler_no_ar_recebe_mesmo_id_e_source_e_sua_resposta_encerra_o_painel(self):
        k = self.knobler()
        self.abrir()
        p = self.menu()
        self.no_knobler(k)
        self.no_painel()
        ask = k.posts('/ask')[0]
        self.assertEqual({c: ask.get(c) for c in ('id', 'source', 'questions')},
                         {'id': self.ID, 'source': os.path.basename(self.r), 'questions': Q})
        self.assertTrue(self.get('/estado')['perguntas'][0]['knobler'])
        k.estados[self.ID] = {'answered': True, 'cancelled': False, 'answers': RESP}
        self.assertEqual(json.loads(self.fim(p)), self.saida(ESPERADO))
        self.assertEqual(self.pergunta(), 'encerrada')
        self.assertEqual(self.respostas(), [{'tool_use_id': 'tu1', 'onde': 'knobler'}])

    def test_resposta_no_painel_cancela_no_knobler(self):
        k = self.knobler()
        self.abrir()
        p = self.menu()
        self.no_knobler(k)
        self.no_painel()
        self.assertFalse(self.cancelou(k))
        self.responder()
        self.assertEqual(json.loads(self.fim(p)), self.saida(ESPERADO))
        self.assertTrue(self.cancelou(k))
        self.assertEqual(self.respostas(), [{'tool_use_id': 'tu1', 'onde': 'painel'}])

    def test_knobler_cancelado_segue_esperando_o_painel(self):
        k = self.knobler()
        self.abrir()
        p = self.menu()
        self.no_knobler(k)
        self.no_painel()
        k.estados[self.ID] = {'answered': False, 'cancelled': True}
        time.sleep(1.5)
        self.assertIsNone(p.poll(), 'o hook desistiu com o ✕ do Knobler')
        self.responder()
        self.assertEqual(json.loads(self.fim(p)), self.saida(ESPERADO))

    def test_painel_abandonado_segue_esperando_o_knobler_que_recebeu(self):
        k = self.knobler()
        self.abrir(abandono=1)
        p = self.menu()
        self.no_knobler(k)
        self.ate(lambda: self.pergunta() == 'abandonada', 'o painel abandonar a pergunta')
        time.sleep(1.5)
        self.assertIsNone(p.poll(), 'o hook desistiu com o Knobler ainda esperando')
        k.estados[self.ID] = {'answered': True, 'cancelled': False, 'answers': RESP}
        self.assertEqual(json.loads(self.fim(p)), self.saida(ESPERADO))
        self.assertEqual(self.respostas(), [{'tool_use_id': 'tu1', 'onde': 'knobler'}])

    def test_painel_abandonado_sem_knobler_sai_mudo(self):
        self.abrir(abandono=1)
        p = self.menu()
        self.assertEqual(self.fim(p, prazo=6), '')
        self.assertNotEqual(self.pergunta(), 'desconhecida')  # postou antes de desistir

    def test_prazo_do_menu_cancela_no_knobler_e_sai_mudo(self):
        self.env['VESTA_PRAZO_MENU'] = '1.5'
        k = self.knobler()
        self.abrir()
        p = self.menu()
        self.no_knobler(k)
        self.assertEqual(self.fim(p, prazo=6), '')
        self.assertTrue(self.cancelou(k))

    def test_erro_de_rede_no_painel_cancela_no_knobler_e_sai_mudo(self):
        k = self.knobler()
        srv = self.abrir()
        p = self.menu()
        self.no_knobler(k)
        self.no_painel()
        srv.kill()
        srv.wait()
        self.assertEqual(self.fim(p, prazo=6), '')
        self.assertTrue(self.cancelou(k))


def quem(n):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{n}/quem', timeout=0.5) as r:
            return r.read().decode().strip()
    except Exception:
        return ''


class Ativacao(ComPainel):
    """`vesta.py hook-ativacao` (PreToolUse de Skill): ativar a skill `vesta` sobe o painel da
    raiz, mesmo sem Vesta no projeto, e abre a página se ela não estiver aberta.

    Abridor: `VESTA_ABRIR` (padrão `open`), chamado com a url como único argumento. O falso
    grava cada chamada numa linha de `abertos`. Um `open` falso no PATH grava em `open-real`:
    nunca deve ser usado quando `VESTA_ABRIR` está definido."""

    def setUp(self):
        super().setUp()
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.bin = tempfile.TemporaryDirectory()
        self.addCleanup(self.bin.cleanup)
        self.abertos_em = os.path.join(self.bin.name, 'abertos')
        self.open_real = os.path.join(self.bin.name, 'open-real')
        self.abridor = self.script('abrir', self.abertos_em)
        self.script('open', self.open_real)
        self.env = {**ENV, 'HOME': self.home.name, 'VESTA_ABRIR': self.abridor,
                    'PATH': self.bin.name + os.pathsep + ENV.get('PATH', '')}
        self.addCleanup(self.matar)  # o painel sobe em sessão própria, fora do alcance do teste

    def script(self, nome, destino):
        caminho = os.path.join(self.bin.name, nome)
        with open(caminho, 'w') as f:
            f.write(f'#!/bin/sh\necho "$@" >> {destino}\n')
        os.chmod(caminho, 0o755)
        return caminho

    def vivos(self):
        return [4700 + i for i in range(100) if quem(4700 + i) == f'vesta-painel {self.r}']

    def matar(self):
        for n in self.vivos():
            out = subprocess.run(['lsof', '-ti', f'tcp:{n}', '-sTCP:LISTEN'], capture_output=True,
                                 text=True).stdout.split()
            for pid in out:
                subprocess.run(['kill', pid], capture_output=True)

    def ativar(self, skill='vesta', entrada=None):
        if entrada is None:
            entrada = json.dumps({'session_id': 's1', 'cwd': self.r, 'hook_event_name': 'PreToolUse',
                                  'tool_name': 'Skill', 'tool_use_id': 'tu1',
                                  'tool_input': {'skill': skill}})
        p = subprocess.run(['python3', SCRIPT, 'hook-ativacao'], cwd=self.fora.name, env=self.env,
                           input=entrada, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        if p.stdout.strip():  # saída opcional, mas nunca decide a permissão da ferramenta
            self.assertNotIn('permissionDecision',
                             json.loads(p.stdout).get('hookSpecificOutput') or {})
        return p

    def ler(self, caminho):
        if not os.path.exists(caminho):
            return []
        with open(caminho) as f:
            return f.read().split()

    def abertos(self, esperar=True):
        """Linhas do abridor falso; espera até 3 s pela primeira, depois mais 0,5 s por repetidas."""
        fim = time.time() + (3 if esperar else 0)
        while not self.ler(self.abertos_em) and time.time() < fim:
            time.sleep(0.05)
        time.sleep(0.5)
        self.assertEqual(self.ler(self.open_real), [], 'usou `open` em vez de VESTA_ABRIR')
        return self.ler(self.abertos_em)

    def arvore(self):
        return subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all', '--ignored'],
                              cwd=self.r, capture_output=True, text=True, check=True).stdout

    def test_sem_vesta_sem_painel_sobe_abre_uma_vez_e_nao_cria_pasta(self):
        self.ativar()
        vivos = self.vivos()
        self.assertEqual(len(vivos), 1, 'o painel da raiz não subiu')
        self.assertEqual(self.abertos(), [f'http://localhost:{vivos[0]}'])
        self.assertFalse(os.path.exists(os.path.join(self.r, 'docs')))
        self.assertFalse(os.path.exists(os.path.join(self.r, '.claude')))
        self.assertEqual(self.arvore(), '')

    def test_painel_no_ar_sem_pagina_abre_o_mesmo_sem_subir_outro(self):
        self.servir(env=self.env)
        self.ativar()
        self.assertEqual(self.abertos(), [f'http://localhost:{self.porta}'])
        self.assertEqual(self.vivos(), [self.porta])

    def test_pagina_aberta_nao_abre(self):
        self.servir(env=self.env)
        self.estado()
        self.ativar()
        self.assertEqual(self.abertos(esperar=False), [])
        self.assertEqual(self.vivos(), [self.porta])

    def test_subpasta_usa_a_raiz(self):
        os.makedirs(os.path.join(self.r, 'a', 'b'))
        entrada = json.dumps({'session_id': 's1', 'cwd': os.path.join(self.r, 'a', 'b'),
                              'tool_name': 'Skill', 'tool_input': {'skill': 'vesta'}})
        self.ativar(entrada=entrada)
        vivos = self.vivos()
        self.assertEqual(len(vivos), 1)
        self.assertEqual(self.abertos(), [f'http://localhost:{vivos[0]}'])

    def test_outra_skill_nao_faz_nada(self):
        for nome in ('vesta-interface', 'vesta-painel', 'grill-me'):
            p = self.ativar(nome)
            self.assertEqual(p.stdout, '')
        self.assertEqual(self.vivos(), [])
        self.assertEqual(self.abertos(esperar=False), [])
        self.assertEqual(self.arvore(), '')

    def test_abridor_quebrado_nao_bloqueia(self):
        self.env['VESTA_ABRIR'] = os.path.join(self.bin.name, 'nao-existe')
        self.ativar()
        self.assertEqual(len(self.vivos()), 1)

    def test_entrada_ruim_sai_0_sem_decidir(self):
        for entrada in ('', 'não é json', json.dumps({'tool_name': 'Skill',
                                                      'tool_input': {'skill': 'vesta'},
                                                      'cwd': os.path.join(self.r, 'nao-existe')})):
            self.ativar(entrada=entrada)


if __name__ == '__main__':
    unittest.main()
