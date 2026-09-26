"""Testes do vesta.py. Cada teste monta um repositório git descartável."""
import json
import os
import subprocess
import tempfile
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


class Mockup(Base):
    """Plano com tela não executa sem mockup commitado."""
    TELA = [{'id': '1', 'titulo': 'tela', 'tela': True}]

    def criar_com(self, **extra):
        d = {'plano': 'plano.md', 'teste': TESTE, 'tela': [], 'etapas': self.TELA, **extra}
        p = self.sf('criar', entrada=json.dumps(d))
        self.assertEqual(p.returncode, 0, p.stderr)

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
        self.criar_com(mockup='docs/mock.html')
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 1)
        self.assertIn('mockup', p.stderr)

    def test_iniciar_aceita_mockup_commitado(self):
        self.commit('mock.html')
        self.criar_com(mockup='mock.html')
        p = self.sf('iniciar')
        self.assertEqual(p.returncode, 0, p.stderr)

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

    def test_adicionar_aceita_objeto_com_mockup_commitado(self):
        self.criar()
        self.sf('iniciar')
        self.commit('mock.html')
        p = self.sf('adicionar', entrada=json.dumps(
            {'mockup': 'mock.html', 'etapas': [{'id': '2', 'titulo': 't', 'tela': True}]}))
        self.assertEqual(p.returncode, 0, p.stderr)
        e = self.estado()
        self.assertEqual(e['mockup'], 'mock.html')
        self.assertEqual(len(e['etapas']), 2)


if __name__ == '__main__':
    unittest.main()
