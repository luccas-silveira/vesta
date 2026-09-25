> Registro histórico; o funcionamento atual está em [como-funciona.md](../como-funciona.md).

# spec-flow, fase 5, parte 1 — trava e prova de teste — Plano de implementação

> **Para quem executa:** SUB-SKILL OBRIGATÓRIA: use `superpowers:executing-plans` (recomendado
> aqui, porque as tarefas 1 a 4 mexem no mesmo arquivo em sequência) ou
> `superpowers:subagent-driven-development`. Os passos usam checkbox (`- [ ]`).

**Objetivo:** o spec-flow ganha a fase 4 própria, em etapas, e a fase 5 com a prova de teste e
uma trava que não deixa o agente parar enquanto houver etapa sem prova.

**Arquitetura:** um script Python só, `spec_flow.py`, guarda o estado da execução em
`.claude/spec-flow/estado.json` na raiz do projeto, roda as provas e responde a dois hooks
(parada e início de sessão). O hook só lê estado e git; quem roda teste é o script, chamado
pelo agente. Os roteiros `plano.md` e `execucao.md` dizem ao agente o que fazer em cada fase.

**Tecnologia:** Python 3 só com biblioteca padrão (`unittest` nos testes), git, hooks do Claude
Code.

**Spec:** `docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md`. Dossiê:
`docs/vesta/research/2026-09-25-spec-flow-execucao-research.md`.

**Escopo deste plano:** a parte 1 da "Entrega em partes" da spec — trava com a prova de teste,
mais o que ela exige para funcionar sozinha: fase 4 em etapas, retomada, convivência com os
outros hooks, testes no pre-commit. As partes 2 (revisão adversária), 3 (prova visual e
protótipo) e 4 (aprendizados) ganham planos próprios depois que esta rodar de verdade.

## Restrições globais

- Scripts em Python 3, só biblioteca padrão. Python local: 3.13.
- Texto para o usuário e para o agente em português do Brasil, com acentos.
- O hook de parada nunca roda teste e nunca prende a sessão por defeito próprio: estado ilegível
  ou exceção liberam a parada.
- A sessão gravada no estado vem sempre da entrada de um hook, nunca de variável de ambiente.
- O hook de parada fala só com o agente: saída `{"decision": "block", "reason": ...}`, sem
  `systemMessage`.
- Estado sempre na raiz do projeto: `git rev-parse --show-toplevel` de `CLAUDE_PROJECT_DIR`, ou
  do diretório atual quando a variável não existe.
- Limites: 8 tentativas vermelhas por prova travam a etapa; mais de 5 bloqueios seguidos sem
  mudança liberam e marcam a execução como interrompida; comando de teste com teto de 1800 s.
- Nomes: "etapa" (o checkpoint do Helix) e "prova" (o gate do Helix).
- Caminho absoluto do script nos registros de hook:
  `/Users/luccassilveira/.claude/skills/spec-flow/scripts/spec_flow.py`.

## Foco de revisão

1. Comando de teste que nem roda (erro 126 ou 127) não pode contar como "vermelho confirmado":
   o teste da tarefa 2 `test_vermelho_recusa_comando_que_nao_roda` fixa isso.
2. Projeto sem commit ou fora do git: prova recusa com mensagem clara; o hook libera. Testes
   `test_projeto_sem_commit_recusa` (tarefa 2) e `test_sem_estado_libera` (tarefa 3).
3. Agente em subpasta do projeto acha o mesmo estado que o hook: `test_comando_de_subpasta_acha_a_raiz`
   (tarefa 1).
4. Estado corrompido à mão: hook libera, aviso de início denuncia. `test_estado_ilegivel_libera`
   (tarefa 3) e `test_estado_ilegivel_avisa` (tarefa 4).
5. Agente trabalhando sem commitar entre bloqueios não pode ser confundido com agente parado:
   mudança na árvore conta como progresso. `test_progresso_zera_o_contador` (tarefa 3).

---

## Mapa de arquivos

- Criar `~/.claude/skills/spec-flow/scripts/spec_flow.py`: estado, provas, hooks, comandos.
- Criar `~/.claude/skills/spec-flow/scripts/test_spec_flow.py`: testes de tudo acima e do
  registro no settings.
- Criar `~/.claude/skills/spec-flow/plano.md`: roteiro da fase 4.
- Criar `~/.claude/skills/spec-flow/execucao.md`: roteiro da fase 5, parte 1.
- Reescrever `~/.claude/skills/spec-flow/SKILL.md`.
- Criar `~/.claude/commands/spec-flow-retomar.md` e `~/.claude/commands/spec-flow-pausar.md`.
- Mudar `~/.claude/settings.json` (hooks Stop e SessionStart novos, guarda no supacode) e
  `~/.claude/settings.local.json` (guarda no impeccable).
- Mudar `~/.claude/CLAUDE.md`, seção "Fluxo de trabalho criativo".
- Neste repositório: `panel/hooks/pre-commit`, `docs/decisions/0016-execucao-travada-por-provas.md`,
  `docs/reference/vesta.md`, e a cópia em `config/claude/` via `backup/sync.sh`.

Em todos os comandos abaixo, `S=~/.claude/skills/spec-flow/scripts` e os testes rodam com:

```bash
cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow
```

---

### Tarefa 1: Núcleo do estado

**Arquivos:**
- Criar: `~/.claude/skills/spec-flow/scripts/spec_flow.py`
- Criar: `~/.claude/skills/spec-flow/scripts/test_spec_flow.py`

**Interfaces:**
- Produz: `raiz(cwd=None) -> str`, `ler(r) -> dict | None` (levanta `ValueError` se ilegível),
  `gravar(r, e)`, `exigir(r) -> dict`, `etapa(e, id_) -> dict`, `encerrada(e) -> bool`,
  `ativa(e) -> bool`, `proxima(e) -> dict`, `ler_entrada()`, `acrescentar(e, novas)`,
  exceção `Recusa`, dicionários `COMANDOS` e `HOOKS`, constantes `LIMITE_TENTATIVAS = 8`,
  `LIMITE_BLOQUEIOS = 5`, `TEMPO_TESTE = 1800`. Comandos `criar`, `iniciar`, `mostrar`.
- Formato do estado:
  `{"versao": 1, "plano": str, "teste": str, "tela": [str], "sessao": null | "adotar" | "<id>",
  "espera": "plano" | "interrompida" | null, "motivo": str | null,
  "bloqueios": {"seguidos": int, "assinatura": str}, "etapas": [{"id": str, "titulo": str,
  "tela": bool, "status": "pendente" | "feita" | "travada", "provas": {"teste": {"vermelho":
  sha | null, "resultado": "verde" | "vermelho" | null, "commit": sha | null, "tentativas": int}}}]}`

- [ ] **Passo 1: Escrever os testes que falham**

`~/.claude/skills/spec-flow/scripts/test_spec_flow.py`:

```python
"""Testes do spec_flow.py. Cada teste monta um repositório git descartável."""
import json
import os
import subprocess
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, 'spec_flow.py')
ENV = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = os.path.realpath(self.tmp.name)
        for args in (['init', '-q'], ['config', 'user.email', 't@t'], ['config', 'user.name', 't'],
                     ['commit', '-q', '--allow-empty', '-m', 'raiz']):
            subprocess.run(['git', *args], cwd=self.r, check=True)
        self.caminho_estado = os.path.join(self.r, '.claude', 'spec-flow', 'estado.json')

    def tearDown(self):
        self.tmp.cleanup()

    def sf(self, *args, entrada=None, cwd=None):
        return subprocess.run(['python3', SCRIPT, *args], cwd=cwd or self.r, env=ENV,
                              input=entrada, capture_output=True, text=True)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.r, capture_output=True, text=True,
                              check=True).stdout.strip()

    def criar(self, teste='test -f ok', etapas=None):
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

    def test_comando_de_subpasta_acha_a_raiz(self):
        os.makedirs(os.path.join(self.r, 'sub'))
        p = self.sf('criar', cwd=os.path.join(self.r, 'sub'),
                    entrada=json.dumps({'teste': 'true', 'etapas': [{'id': '1', 'titulo': 'a'}]}))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.exists(self.caminho_estado))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: 5 falhas, todas por `spec_flow.py` não existir (`can't open file`).

- [ ] **Passo 3: Implementar**

`~/.claude/skills/spec-flow/scripts/spec_flow.py`:

```python
#!/usr/bin/env python3
"""spec-flow, fase 5: estado da execução, provas e hooks. Só biblioteca padrão.

Uso: spec_flow.py <comando> [argumentos]. Os comandos estão em COMANDOS e HOOKS, no fim.
"""
import hashlib
import json
import os
import subprocess
import sys

PASTA = os.path.join('.claude', 'spec-flow')
# O .gitignore ignora a si mesmo: gravar o estado nunca suja a árvore. aprendizados.md fica
# de fora e vai para o git.
IGNORAR = '.gitignore\nestado.json\n*.tmp\npareceres/\nprototipo/\n'
LIMITE_TENTATIVAS = 8
LIMITE_BLOQUEIOS = 5
TEMPO_TESTE = 1800  # ponytail: teto fixo em segundos; vira campo do estado quando algum projeto precisar de mais


class Recusa(Exception):
    """Pedido que o estado atual não permite. A mensagem vai para o agente."""


def git(pasta, *args):
    try:
        p = subprocess.run(['git', *args], cwd=pasta, capture_output=True, text=True)
    except OSError:
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def raiz(cwd=None):
    """Raiz do projeto: a mesma para o hook e para o agente, de qualquer subpasta."""
    base = os.environ.get('CLAUDE_PROJECT_DIR') or cwd or os.getcwd()
    return git(base, 'rev-parse', '--show-toplevel') or base


def caminho(r):
    return os.path.join(r, PASTA, 'estado.json')


def ler(r):
    """None se não há execução. Estado ilegível levanta ValueError."""
    try:
        with open(caminho(r)) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def gravar(r, e):
    pasta = os.path.join(r, PASTA)
    os.makedirs(pasta, exist_ok=True)
    gi = os.path.join(pasta, '.gitignore')
    if not os.path.exists(gi):
        with open(gi, 'w') as f:
            f.write(IGNORAR)
    tmp = caminho(r) + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho(r))


def exigir(r):
    e = ler(r)
    if not e:
        raise Recusa('não há execução do spec-flow neste projeto')
    return e


def nova_etapa(d):
    if not isinstance(d, dict) or not d.get('id') or not d.get('titulo'):
        raise Recusa('toda etapa precisa de id e titulo')
    return {'id': str(d['id']), 'titulo': d['titulo'], 'tela': bool(d.get('tela')),
            'status': 'pendente',
            'provas': {'teste': {'vermelho': None, 'resultado': None, 'commit': None,
                                 'tentativas': 0}}}


def acrescentar(e, novas):
    ids = {x['id'] for x in e['etapas']}
    for d in novas:
        x = nova_etapa(d)
        if x['id'] in ids:
            raise Recusa(f'id de etapa repetido: {x["id"]}')
        ids.add(x['id'])
        e['etapas'].append(x)


def etapa(e, id_):
    for x in e['etapas']:
        if x['id'] == id_:
            return x
    raise Recusa(f'a etapa {id_} não existe no estado')


def encerrada(e):
    st = [x['status'] for x in e['etapas']]
    return 'travada' in st or all(s == 'feita' for s in st)


def ativa(e):
    return bool(e) and e.get('espera') is None and not encerrada(e)


def proxima(e):
    return next(x for x in e['etapas'] if x['status'] == 'pendente')


def ler_entrada():
    return json.loads(sys.stdin.read() or 'null')


def cmd_criar(r, args):
    if ler(r) is not None:
        raise Recusa('já existe execução neste projeto: retome (/spec-flow-retomar) ou feche (fechar)')
    d = ler_entrada()
    if not isinstance(d, dict) or not d.get('teste') or not d.get('etapas'):
        raise Recusa('criar espera um JSON com plano, teste e etapas')
    e = {'versao': 1, 'plano': d.get('plano', ''), 'teste': d['teste'], 'tela': d.get('tela', []),
         'sessao': None, 'espera': 'plano', 'motivo': None,
         'bloqueios': {'seguidos': 0, 'assinatura': ''}, 'etapas': []}
    acrescentar(e, d['etapas'])
    gravar(r, e)
    return f'estado criado com {len(e["etapas"])} etapa(s), esperando aprovação do plano'


def cmd_iniciar(r, args):
    e = exigir(r)
    if e['espera'] != 'plano':
        raise Recusa('iniciar só vale com o plano esperando aprovação')
    e.update(espera=None, sessao='adotar')
    gravar(r, e)
    return 'execução iniciada; a trava liga na próxima parada desta sessão'


def cmd_mostrar(r, args):
    return json.dumps(exigir(r), ensure_ascii=False, indent=2)


COMANDOS = {'criar': cmd_criar, 'iniciar': cmd_iniciar, 'mostrar': cmd_mostrar}
HOOKS = {}


def main(argv):
    if argv and argv[0] in HOOKS:
        return rodar_hook(HOOKS[argv[0]])
    if not argv or argv[0] not in COMANDOS:
        print('uso: spec_flow.py ' + '|'.join([*COMANDOS, *HOOKS]), file=sys.stderr)
        return 2
    try:
        saida = COMANDOS[argv[0]](raiz(), argv[1:])
    except (Recusa, ValueError) as err:
        print(f'spec-flow: {err}', file=sys.stderr)
        return 1
    if saida:
        print(saida)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
```

`rodar_hook` só nasce na tarefa 3; até lá `HOOKS` está vazio e a linha não é alcançada.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: `Ran 5 tests`, `OK`.

- [ ] **Passo 5: Guardar**

`~/.claude` não é repositório git. Nada a commitar aqui; a cópia entra neste repositório na
tarefa 7.

---

### Tarefa 2: Provas

**Arquivos:**
- Mudar: `~/.claude/skills/spec-flow/scripts/spec_flow.py`
- Mudar: `~/.claude/skills/spec-flow/scripts/test_spec_flow.py`

**Interfaces:**
- Consome: `raiz`, `exigir`, `etapa`, `gravar`, `git`, `Recusa`, constantes da tarefa 1.
- Produz: `limpa(r) -> str` (o HEAD, só com a árvore limpa), `rodar_teste(r, e) -> (int | None, str)`,
  `cauda(texto, linhas=60) -> str`, comandos `prova vermelho <id>`, `prova teste <id>`,
  `concluir <id>`.

- [ ] **Passo 1: Escrever os testes que falham**

Acrescentar em `test_spec_flow.py`, antes do `if __name__`:

```python
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
        p = self.sf('prova', 'vermelho', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('passaram antes', p.stderr)
        self.assertIsNone(self.estado()['etapas'][0]['provas']['teste']['vermelho'])

    def test_vermelho_recusa_comando_que_nao_roda(self):
        os.remove(self.caminho_estado)
        self.criar(teste='comando-que-nao-existe-xyz')
        p = self.sf('prova', 'vermelho', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('não roda', p.stderr)
        self.assertIsNone(self.estado()['etapas'][0]['provas']['teste']['vermelho'])

    def test_teste_exige_vermelho_antes(self):
        p = self.sf('prova', 'teste', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('confirme o vermelho', p.stderr)

    def test_ciclo_vermelho_verde_concluir(self):
        self.assertEqual(self.sf('prova', 'vermelho', '1').returncode, 0)
        self.commit('ok')
        self.assertEqual(self.sf('prova', 'teste', '1').returncode, 0)
        self.assertEqual(self.sf('concluir', '1').returncode, 0)
        self.assertEqual(self.estado()['etapas'][0]['status'], 'feita')

    def test_commit_depois_do_verde_invalida_a_prova(self):
        self.sf('prova', 'vermelho', '1')
        self.commit('ok')
        self.sf('prova', 'teste', '1')
        self.commit('outro')
        p = self.sf('concluir', '1')
        self.assertEqual(p.returncode, 1)
        self.assertIn('não está verde neste commit', p.stderr)

    def test_oitavo_vermelho_trava_a_etapa(self):
        self.sf('prova', 'vermelho', '1')
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
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: as 8 novas falham; `stderr` contém `uso: spec_flow.py`, porque `prova` e `concluir`
ainda não existem. As 5 da tarefa 1 continuam passando.

- [ ] **Passo 3: Implementar**

Em `spec_flow.py`, acrescentar antes de `COMANDOS`:

```python
def limpa(r):
    """HEAD atual, só com a árvore limpa: a prova vale para esse commit e nada mais."""
    head = git(r, 'rev-parse', 'HEAD')
    if head is None:
        raise Recusa('o projeto precisa ser um repositório git com pelo menos um commit')
    if git(r, 'status', '--porcelain') != '':
        raise Recusa('há mudança não commitada; commite antes da prova')
    return head


def rodar_teste(r, e):
    """(código de saída, saída). Código None quando estoura o tempo."""
    try:
        p = subprocess.run(e['teste'], shell=True, cwd=r, capture_output=True, text=True,
                           timeout=TEMPO_TESTE)
    except subprocess.TimeoutExpired:
        return None, f'o comando de teste passou de {TEMPO_TESTE} s'
    return p.returncode, p.stdout + p.stderr


def cauda(texto, linhas=60):
    return '\n'.join(texto.rstrip().splitlines()[-linhas:])


def cmd_prova(r, args):
    if len(args) != 2 or args[0] not in ('vermelho', 'teste'):
        raise Recusa('uso: prova vermelho|teste <etapa>')
    tipo, id_ = args
    e = exigir(r)
    x = etapa(e, id_)
    if x['status'] != 'pendente':
        raise Recusa(f'a etapa {id_} está {x["status"]}')
    t = x['provas']['teste']
    if tipo == 'teste' and not t['vermelho']:
        raise Recusa(f'confirme o vermelho antes: prova vermelho {id_}')
    head = limpa(r)
    codigo, saida = rodar_teste(r, e)
    if codigo in (126, 127):
        raise Recusa(f'o comando de teste não roda (saída {codigo}):\n{cauda(saida, 5)}')
    if tipo == 'vermelho':
        if codigo is None:
            raise Recusa(saida)
        if codigo == 0:
            raise Recusa('os testes passaram antes do código existir; eles não provam a etapa. '
                         'Refaça os testes.')
        t['vermelho'] = head
        gravar(r, e)
        return f'vermelho confirmado em {head[:7]}'
    verde = codigo == 0
    t.update(resultado='verde' if verde else 'vermelho', commit=head)
    if not verde:
        t['tentativas'] += 1
        if t['tentativas'] >= LIMITE_TENTATIVAS:
            x['status'] = 'travada'
    gravar(r, e)
    if verde:
        return f'verde em {head[:7]}'
    if x['status'] == 'travada':
        raise Recusa(f'etapa {id_} travada depois de {t["tentativas"]} tentativas\n{cauda(saida)}')
    raise Recusa(f'vermelho, tentativa {t["tentativas"]} de {LIMITE_TENTATIVAS}\n{cauda(saida)}')


def cmd_concluir(r, args):
    if len(args) != 1:
        raise Recusa('uso: concluir <etapa>')
    e = exigir(r)
    x = etapa(e, args[0])
    head = limpa(r)
    t = x['provas']['teste']
    if x['status'] != 'pendente' or t['resultado'] != 'verde' or t['commit'] != head:
        raise Recusa(f'a prova de teste da etapa {args[0]} não está verde neste commit; '
                     f'rode prova teste {args[0]}')
    x['status'] = 'feita'
    gravar(r, e)
    return f'etapa {args[0]} feita'
```

E trocar a linha de `COMANDOS` por:

```python
COMANDOS = {'criar': cmd_criar, 'iniciar': cmd_iniciar, 'mostrar': cmd_mostrar,
            'prova': cmd_prova, 'concluir': cmd_concluir}
```

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: `Ran 13 tests`, `OK`.

---

### Tarefa 3: Hook de parada

**Arquivos:**
- Mudar: `~/.claude/skills/spec-flow/scripts/spec_flow.py`
- Mudar: `~/.claude/skills/spec-flow/scripts/test_spec_flow.py`

**Interfaces:**
- Consome: `raiz`, `ler`, `gravar`, `ativa`, `proxima`, `git`, `ler_entrada`, `LIMITE_BLOQUEIOS`.
- Produz: `hook_parada(entrada: dict) -> dict | None`, `pendencia(x, head) -> str`,
  `rodar_hook(funcao) -> int` (sempre 0), comando `hook-parada`.

- [ ] **Passo 1: Escrever os testes que falham**

Acrescentar em `test_spec_flow.py`, antes do `if __name__`:

```python
class Parada(Base):
    def setUp(self):
        super().setUp()
        self.criar()
        self.sf('iniciar')

    def test_sem_estado_libera(self):
        os.remove(self.caminho_estado)
        self.assertIsNone(self.hook('hook-parada'))

    def test_estado_ilegivel_libera(self):
        with open(self.caminho_estado, 'w') as f:
            f.write('{quebrado')
        self.assertIsNone(self.hook('hook-parada'))

    def test_adota_a_sessao_e_bloqueia_so_com_o_agente(self):
        out = self.hook('hook-parada', sid='s1')
        self.assertEqual(out['decision'], 'block')
        self.assertIn('Etapa 1', out['reason'])
        self.assertIn('prova vermelho', out['reason'])
        self.assertNotIn('systemMessage', out)
        self.assertEqual(self.estado()['sessao'], 's1')

    def test_outra_sessao_libera(self):
        self.hook('hook-parada', sid='s1')
        self.assertIsNone(self.hook('hook-parada', sid='s2'))

    def test_plano_esperando_aprovacao_libera(self):
        os.remove(self.caminho_estado)
        self.criar()
        self.assertIsNone(self.hook('hook-parada'))

    def test_tarefa_em_segundo_plano_libera(self):
        self.assertIsNone(self.hook('hook-parada', background_tasks=[{'id': 'x'}]))

    def test_todas_feitas_libera(self):
        self.sf('prova', 'vermelho', '1')
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
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: as 9 novas falham em `self.hook`, com código de saída 2 (`uso: spec_flow.py`).

- [ ] **Passo 3: Implementar**

Em `spec_flow.py`, acrescentar antes de `COMANDOS`:

```python
def pendencia(x, head):
    t = x['provas']['teste']
    if not t['vermelho']:
        return 'escrever os testes, commitar e confirmar o vermelho (prova vermelho)'
    if t['resultado'] != 'verde' or t['commit'] != head:
        return 'implementar, commitar e rodar a prova de teste (prova teste)'
    return 'concluir a etapa (concluir)'


def hook_parada(entrada):
    r = raiz(entrada.get('cwd'))
    try:
        e = ler(r)
    except (ValueError, OSError):
        return None  # estado ilegível: falha aberta; o aviso de início de sessão denuncia
    if not e or entrada.get('background_tasks'):
        return None
    sid = entrada.get('session_id') or ''
    if e.get('sessao') == 'adotar' and sid:
        e['sessao'] = sid
        gravar(r, e)
    if not sid or e.get('sessao') != sid or not ativa(e):
        return None
    x = proxima(e)
    head = git(r, 'rev-parse', 'HEAD') or ''
    # Progresso é qualquer mudança: estado das etapas, commit, ou arquivo mexido sem commit.
    arvore = (git(r, 'status', '--porcelain') or '') + (git(r, 'diff', 'HEAD') or '')
    assinatura = hashlib.sha1((json.dumps(e['etapas'], sort_keys=True) + head + arvore)
                              .encode()).hexdigest()
    b = e['bloqueios']
    b['seguidos'] = b['seguidos'] + 1 if b['assinatura'] == assinatura else 1
    b['assinatura'] = assinatura
    if b['seguidos'] > LIMITE_BLOQUEIOS:
        e.update(espera='interrompida',
                 motivo=f'{LIMITE_BLOQUEIOS} bloqueios seguidos sem progresso na etapa {x["id"]}')
        gravar(r, e)
        return None
    gravar(r, e)
    return {'decision': 'block',
            'reason': (f'Execução do spec-flow em andamento. Etapa {x["id"]} ({x["titulo"]}): falta '
                       f'{pendencia(x, head)}. Siga ~/.claude/skills/spec-flow/execucao.md e não '
                       'pare antes de todas as etapas estarem provadas.')}


def rodar_hook(funcao):
    try:
        saida = funcao(ler_entrada() or {})
    except Exception as err:  # hook nunca prende a sessão por defeito próprio
        print(f'spec-flow: {err}', file=sys.stderr)
        return 0
    if saida:
        print(json.dumps(saida, ensure_ascii=False))
    return 0
```

E trocar `HOOKS = {}` por:

```python
HOOKS = {'hook-parada': hook_parada}
```

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: `Ran 22 tests`, `OK`.

---

### Tarefa 4: Retomada, pausa e aviso de início de sessão

**Arquivos:**
- Mudar: `~/.claude/skills/spec-flow/scripts/spec_flow.py`
- Mudar: `~/.claude/skills/spec-flow/scripts/test_spec_flow.py`

**Interfaces:**
- Consome: tudo das tarefas 1 a 3.
- Produz: comandos `retomar`, `pausar [motivo...]`, `adicionar` (lista JSON de etapas na entrada),
  `fechar`, `ativa` (sai 0 com execução ativa, 1 sem); hook `hook-inicio`;
  `hook_inicio(entrada) -> dict | None`, `aviso(texto) -> dict`.

- [ ] **Passo 1: Escrever os testes que falham**

Acrescentar em `test_spec_flow.py`, antes do `if __name__`:

```python
class Retomada(Base):
    def setUp(self):
        super().setUp()
        self.criar()
        self.sf('iniciar')
        self.hook('hook-parada', sid='s1')

    def test_sessao_nova_avisa_execucao_de_outra_sessao(self):
        out = self.hook('hook-inicio', sid='s2')
        self.assertIn('etapa 1', out['systemMessage'])
        self.assertIn('/spec-flow-retomar', out['systemMessage'])
        self.assertEqual(out['hookSpecificOutput']['hookEventName'], 'SessionStart')

    def test_mesma_sessao_sem_aviso(self):
        self.assertIsNone(self.hook('hook-inicio', sid='s1'))

    def test_sem_estado_sem_aviso(self):
        os.remove(self.caminho_estado)
        self.assertIsNone(self.hook('hook-inicio', sid='s2'))

    def test_estado_ilegivel_avisa(self):
        with open(self.caminho_estado, 'w') as f:
            f.write('{')
        self.assertIn('ilegível', self.hook('hook-inicio', sid='s2')['systemMessage'])

    def test_retomar_passa_a_execucao_para_a_sessao_seguinte(self):
        self.assertEqual(self.sf('retomar').returncode, 0)
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
        self.sf('prova', 'vermelho', '1')
        for _ in range(8):
            self.sf('prova', 'teste', '1')
        self.assertIn('travou', self.hook('hook-inicio', sid='s2')['systemMessage'])
        self.sf('retomar')
        x = self.estado()['etapas'][0]
        self.assertEqual(x['status'], 'pendente')
        self.assertEqual(x['provas']['teste']['tentativas'], 0)

    def test_adicionar_reabre_a_execucao(self):
        self.sf('prova', 'vermelho', '1')
        self.commit('ok')
        self.sf('prova', 'teste', '1')
        self.sf('concluir', '1')
        p = self.sf('adicionar', entrada=json.dumps([{'id': '2', 'titulo': 'ajuste'}]))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.hook('hook-parada', sid='s1')['decision'], 'block')

    def test_ativa(self):
        self.assertEqual(self.sf('ativa').returncode, 0)
        self.sf('pausar')
        self.assertEqual(self.sf('ativa').returncode, 1)
        self.sf('fechar')
        self.assertEqual(self.sf('ativa').returncode, 1)
        self.assertFalse(os.path.exists(self.caminho_estado))
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: as 10 novas falham (`uso: spec_flow.py` ou `hook-inicio` com saída 2); as 22
anteriores passam.

- [ ] **Passo 3: Implementar**

Em `spec_flow.py`, acrescentar antes de `COMANDOS`:

```python
def zerar(e):
    e.update(espera=None, sessao='adotar', motivo=None, bloqueios={'seguidos': 0, 'assinatura': ''})


def cmd_retomar(r, args):
    e = exigir(r)
    if e['espera'] == 'plano':
        raise Recusa('o plano ainda espera aprovação; depois dela, use iniciar')
    for x in e['etapas']:
        if x['status'] == 'travada':
            x['status'] = 'pendente'
            x['provas']['teste']['tentativas'] = 0
    zerar(e)
    gravar(r, e)
    return 'execução retomada; a trava liga na próxima parada desta sessão'


def cmd_pausar(r, args):
    e = exigir(r)
    e.update(espera='interrompida', motivo=' '.join(args) or 'pausa manual')
    gravar(r, e)
    return 'execução pausada; /spec-flow-retomar retoma'


def cmd_adicionar(r, args):
    e = exigir(r)
    novas = ler_entrada()
    if not isinstance(novas, list) or not novas:
        raise Recusa('adicionar espera uma lista JSON de etapas')
    acrescentar(e, novas)
    zerar(e)
    gravar(r, e)
    return f'{len(novas)} etapa(s) nova(s); execução retomada'


def cmd_fechar(r, args):
    exigir(r)
    os.remove(caminho(r))
    return 'execução fechada'


def aviso(texto):
    texto = 'spec-flow: ' + texto
    return {'systemMessage': texto,
            'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                   'additionalContext': texto + ' Diga isso ao usuário na primeira resposta.'}}


def hook_inicio(entrada):
    r = raiz(entrada.get('cwd'))
    try:
        e = ler(r)
    except (ValueError, OSError):
        return aviso('o estado da execução está ilegível (.claude/spec-flow/estado.json).')
    if not e or e.get('espera') == 'plano':
        return None
    travada = next((x for x in e['etapas'] if x['status'] == 'travada'), None)
    if travada:
        return aviso(f'a execução travou na etapa {travada["id"]} ({travada["titulo"]}) depois de '
                     f'{LIMITE_TENTATIVAS} tentativas. /spec-flow-retomar tenta de novo.')
    if encerrada(e):
        return None
    x = proxima(e)
    if e.get('espera') == 'interrompida':
        return aviso(f'a execução foi interrompida na etapa {x["id"]} ({x["titulo"]}). '
                     f'Motivo: {e.get("motivo")}. /spec-flow-retomar retoma nesta sessão.')
    if e.get('sessao') != entrada.get('session_id'):
        return aviso(f'há execução neste projeto, parada na etapa {x["id"]} ({x["titulo"]}), '
                     'ligada a outra sessão. Se ela não está mais rodando, /spec-flow-retomar '
                     'a passa para esta.')
    return None


def ativa_aqui():
    try:
        return ativa(ler(raiz()))
    except (ValueError, OSError):
        return False
```

Trocar `COMANDOS` e `HOOKS` por:

```python
COMANDOS = {'criar': cmd_criar, 'iniciar': cmd_iniciar, 'mostrar': cmd_mostrar,
            'prova': cmd_prova, 'concluir': cmd_concluir, 'retomar': cmd_retomar,
            'pausar': cmd_pausar, 'adicionar': cmd_adicionar, 'fechar': cmd_fechar}
HOOKS = {'hook-parada': hook_parada, 'hook-inicio': hook_inicio}
```

E, em `main`, logo depois do bloco dos hooks:

```python
    if argv and argv[0] == 'ativa':
        return 0 if ativa_aqui() else 1
```

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: `Ran 32 tests`, `OK`.

---

### Tarefa 5: Registro dos hooks e comandos

**Arquivos:**
- Mudar: `~/.claude/settings.json`, `~/.claude/settings.local.json`
- Criar: `~/.claude/commands/spec-flow-retomar.md`, `~/.claude/commands/spec-flow-pausar.md`
- Mudar: `~/.claude/skills/spec-flow/scripts/test_spec_flow.py`

**Interfaces:**
- Consome: comandos `hook-parada`, `hook-inicio`, `ativa`, `retomar`, `pausar`, `mostrar`.
- Produz: a guarda `python3 "<script>" ativa && exit 0; ` na frente dos hooks de parada do
  supacode e do impeccable.

- [ ] **Passo 1: Escrever o teste que falha**

Acrescentar em `test_spec_flow.py`, antes do `if __name__`:

```python
# O settings.json vizinho: o de ~/.claude, ou a cópia do backup em config/claude.
RAIZ_CLAUDE = os.path.normpath(os.path.join(AQUI, '..', '..', '..'))
GUARDA = r'^python3 "[^"]*spec_flow\.py" ativa && exit 0; '


class Registro(unittest.TestCase):
    def comandos(self, evento):
        with open(os.path.join(RAIZ_CLAUDE, 'settings.json')) as f:
            h = json.load(f)['hooks']
        return [x['command'] for g in h.get(evento, []) for x in g['hooks']]

    def test_hooks_do_spec_flow_registrados(self):
        self.assertTrue(any('spec_flow.py" hook-parada' in c for c in self.comandos('Stop')))
        self.assertTrue(any('spec_flow.py" hook-inicio' in c for c in self.comandos('SessionStart')))

    def test_notificacao_do_supacode_com_guarda(self):
        supacode = [c for c in self.comandos('Stop') if 'supacode-managed-hook' in c]
        self.assertTrue(supacode)
        for c in supacode:
            self.assertRegex(c, GUARDA)
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: `test_hooks_do_spec_flow_registrados` e `test_notificacao_do_supacode_com_guarda` falham.

- [ ] **Passo 3: Guardar cópia e registrar**

```bash
SCRATCH=/private/tmp/claude-501/-Users-luccassilveira-Code-claude-tooling/5a85612b-cf93-4d26-b721-18acf18b7643/scratchpad
cp ~/.claude/settings.json "$SCRATCH/settings.json.antes"
cp ~/.claude/settings.local.json "$SCRATCH/settings.local.json.antes"
python3 - <<'PY'
import json, os
S = '/Users/luccassilveira/.claude/skills/spec-flow/scripts/spec_flow.py'
GUARDA = f'python3 "{S}" ativa && exit 0; '

def editar(nome, mudar):
    p = os.path.expanduser(f'~/.claude/{nome}')
    with open(p) as f:
        d = json.load(f)
    mudar(d['hooks'])
    with open(p, 'w') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')

def proteger(grupos, marca):
    for g in grupos:
        for x in g['hooks']:
            if marca in x['command'] and not x['command'].startswith(GUARDA):
                x['command'] = GUARDA + x['command']

def registrar(h, evento, sub):
    cmd = f'python3 "{S}" {sub}'
    if not any(cmd == x['command'] for g in h[evento] for x in g['hooks']):
        h[evento].append({'hooks': [{'type': 'command', 'command': cmd, 'timeout': 10}]})

def principal(h):
    registrar(h, 'Stop', 'hook-parada')
    registrar(h, 'SessionStart', 'hook-inicio')
    proteger(h['Stop'], 'supacode-managed-hook')

editar('settings.json', principal)
editar('settings.local.json', lambda h: proteger(h['Stop'], 'skills/impeccable/scripts/impeccable'))
PY
diff <(python3 -m json.tool "$SCRATCH/settings.json.antes") <(python3 -m json.tool ~/.claude/settings.json)
diff <(python3 -m json.tool "$SCRATCH/settings.local.json.antes") <(python3 -m json.tool ~/.claude/settings.local.json)
```

Esperado nos dois `diff`: só as linhas dos dois registros novos e a guarda na frente dos
comandos do supacode e do impeccable. Qualquer outra diferença: restaurar das cópias
`.antes` e investigar.

A guarda não lê a entrada do hook, então o comando do supacode continua recebendo o JSON
inteiro. Se o supacode reescrever o próprio hook numa atualização, a guarda some; o teste
`test_notificacao_do_supacode_com_guarda` pega isso no próximo backup.

- [ ] **Passo 4: Criar os comandos**

`~/.claude/commands/spec-flow-retomar.md`:

```markdown
---
description: Retoma nesta sessão a execução do spec-flow interrompida neste projeto
---

Rode `python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py retomar`.

Recusou: mostre a mensagem ao usuário e pare.

Aceitou: rode `python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py mostrar` para ver a
primeira etapa pendente e em que prova ela está, leia `~/.claude/skills/spec-flow/execucao.md`
e continue a fase 5 dali. Não refaça o que já foi provado.
```

`~/.claude/commands/spec-flow-pausar.md`:

```markdown
---
description: Pausa a execução do spec-flow neste projeto, mantendo o estado para retomar
argument-hint: [motivo]
---

Rode `python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py pausar $ARGUMENTS` e pare. Não
comece trabalho novo depois.
```

- [ ] **Passo 5: Rodar e ver passar**

Rodar: `cd ~/.claude/skills/spec-flow/scripts && python3 -m unittest -q test_spec_flow`
Esperado: `Ran 34 tests`, `OK`.

Conferir o hook de verdade, fora de projeto com execução (deve sair calado e com 0):

```bash
echo '{"session_id":"x","cwd":"/tmp"}' | python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py hook-parada; echo "saída $?"
```

Esperado: só `saída 0`.

---

### Tarefa 6: Roteiros da fase 4 e da fase 5, e o SKILL.md

**Arquivos:**
- Criar: `~/.claude/skills/spec-flow/plano.md`
- Criar: `~/.claude/skills/spec-flow/execucao.md`
- Reescrever: `~/.claude/skills/spec-flow/SKILL.md`
- Mudar: `~/.claude/CLAUDE.md`, seção "Fluxo de trabalho criativo"

**Interfaces:**
- Consome: comandos `criar`, `iniciar`, `prova`, `concluir`, `adicionar`, `fechar`, `mostrar`.
- Produz: o formato de plano em etapas que a tarefa 8 vai usar.

Texto de roteiro não tem teste automático; a prova desta tarefa é a tarefa 8.

- [ ] **Passo 1: Criar `plano.md`**

````markdown
# Fase 4 — Plano

Não anuncie a entrada nesta fase. Você volta a escrever quando o plano estiver pronto para a
parada 1.

Entrada: a spec revisada pelo grill. Saída: o plano em
`docs/vesta/plans/YYYY-MM-DD-<feature>.md`, commitado, e o estado da execução criado,
esperando aprovação.

## O plano é uma lista de etapas

Etapa é o menor pedaço que carrega a própria prova e que um revisor poderia rejeitar sozinho.
Ordem: da mais simples à mais complexa. Cada uma se apoia na anterior, e uma decisão errada
aparece cedo, quando ainda é barata.

Projeto sem comando de teste que rode: a etapa 0 monta o mínimo para rodar testes.

Para cada etapa, escreva:

- **Título**, uma linha.
- **Tela:** sim quando a etapa cria ou muda algo visível; não, caso contrário.
- **Arquivos:** caminhos exatos a criar e a mudar.
- **O que prova a etapa:** os casos de teste, do ponto de vista de quem usa, com os casos de
  borda. Escreva o que cada teste verifica, não o código do teste: quem escreve o teste é um
  subagente que lê isto.
- **Como fazer:** o suficiente para um implementador sem contexto do projeto — nomes, formatos,
  o padrão existente a seguir, com `arquivo:linha`.

Proibido no plano: "a definir", "tratar erros adequadamente", "como na etapa N". Repita o que
for preciso: cada subagente lê só a etapa dele.

## Cabeçalho do plano

- Objetivo, uma frase.
- Caminho da spec.
- Comando de teste do projeto, exato, rodando da raiz. É o que a prova de teste executa; ele
  precisa sair com código diferente de zero quando algum teste falha.
- Pastas de tela: as pastas cujos arquivos contam como visíveis (componentes, estilos,
  templates). Projeto sem tela: nenhuma.

## Crie o estado

Commite o plano. Depois:

```bash
python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py criar <<'JSON'
{"plano": "docs/vesta/plans/<arquivo>.md",
 "teste": "<comando de teste>",
 "tela": ["<pasta>"],
 "etapas": [{"id": "1", "titulo": "<título>", "tela": false}]}
JSON
```

Uma entrada em `etapas` por etapa do plano, com os mesmos ids. O estado nasce esperando
aprovação: a trava ainda não age.

## Parada 1

Mensagem ao usuário, cinco linhas: o que o plano vai fazer, quantas etapas, o que trava, o
que decidir agora, o caminho do plano. Não repita o que está nos arquivos.

Aprovado: leia `execucao.md` e siga.

Mudança pedida: edite o plano, commite, e recrie o estado (`fechar`, depois `criar`).
````

- [ ] **Passo 2: Criar `execucao.md`**

````markdown
# Fase 5 — Execução

Não anuncie a entrada nesta fase. Entre as duas paradas você não escreve nada para o usuário:
ele não está olhando, e o hook não deixa você parar antes do fim.

Toda prova passa pelo script. Você nunca edita o estado à mão.

```bash
S=~/.claude/skills/spec-flow/scripts/spec_flow.py
```

## Começo

1. `python3 $S iniciar`. A trava liga na próxima vez que você tentar parar.
2. Leia o plano inteiro uma vez.

## Cada etapa, na ordem do plano

1. **Escritor de teste.** Subagente novo, em primeiro plano, com o pedido abaixo.
2. Commit: `git add -A && git commit -m "test(etapa N): <título>"`.
3. `python3 $S prova vermelho N`. Recusou porque os testes já passam: devolva ao escritor com a
   saída, commite a correção e repita este passo.
4. **Implementador.** Outro subagente novo, em primeiro plano, com o pedido abaixo.
5. Commit: `git add -A && git commit -m "feat(etapa N): <título>"`.
6. `python3 $S prova teste N`. Vermelho: retome o mesmo implementador com a saída e volte ao
   passo 5. O script conta as tentativas e trava a etapa na oitava.
7. Verde: `python3 $S concluir N`.

As tentativas acontecem dentro do mesmo turno: não pare entre uma e outra.

Implementador respondeu BLOCKED porque um teste está errado: devolva ao escritor com o motivo,
commite o teste corrigido e rode de novo `prova vermelho N` antes de retomar o implementador.

Subagentes sempre em primeiro plano, nunca em segundo.

Etapa travada: vá à parada 2.

### Pedido ao escritor de teste

```
Você escreve os testes da etapa {N} de um plano. Não escreva código de produção e não rode commit.

Etapa, copiada do plano:
{texto integral da etapa}

Comando de teste do projeto: {comando}

Regras:
- Ache os testes que já existem no projeto e siga o padrão deles.
- Cada caso de "O que prova a etapa" vira pelo menos um teste. Teste o que quem usa vê, não a implementação.
- Os testes precisam falhar agora, porque o código ainda não existe. Falha por import ou símbolo ausente conta.
- Para cada teste, pense numa implementação errada plausível e confira que o teste a reprova. Teste que passaria com ela não prova nada.

Responda com os arquivos de teste criados e, para cada teste, uma linha dizendo o que ele verifica.
```

### Pedido ao implementador

```
Você implementa a etapa {N} de um plano. Os testes já existem e estão falhando.

Etapa, copiada do plano:
{texto integral da etapa}

Arquivos de teste da etapa: {lista}
Comando de teste do projeto: {comando}

Regras:
- Não altere os testes. Se um teste parecer errado, pare e responda BLOCKED com o motivo.
- Faça o mínimo que deixa os testes verdes, no padrão do código ao redor.
- Rode o comando de teste antes de responder.
- Não rode commit e não abra subagentes.

Responda com o status (DONE ou BLOCKED) e os arquivos mudados.
```

## Parada 2

Depois de concluir a última etapa, ou quando uma travar, escreva ao usuário em cinco linhas: o
que ficou pronto, o que travou e por quê (a linha decisiva da última saída), como testar a
feature.

Ajuste pedido: acrescente as etapas no plano, commite, e registre:

```bash
python3 $S adicionar <<'JSON'
[{"id": "<próximo id>", "titulo": "<ajuste>", "tela": false}]
JSON
```

Depois volte ao ciclo de etapa.

Usuário aprovou a feature: `python3 $S fechar`.
````

- [ ] **Passo 3: Reescrever `SKILL.md`**

````markdown
---
name: spec-flow
description: Fluxo padrão para qualquer trabalho criativo — feature nova, componente, funcionalidade, mudança de comportamento. Encadeia spec (brainstorming) → pesquisa (codebase + web) → grill com dossiê → plano em etapas → execução travada por provas. Use ANTES de escrever qualquer código. Dispara em "/spec-flow", "vamos construir X", "quero criar X", "adiciona X", ou qualquer pedido de feature nova.
---

# spec-flow

Ideia crua vira feature pronta passando por cinco fases. Nenhuma pula.

Anuncie uma vez, no começo: "Usando spec-flow: spec, pesquisa, grill, plano, execução."

Depois disso, nunca mais fale de fase. Não anuncie entrada, saída, conclusão nem próximo
passo — o usuário vê as ferramentas rodando e não precisa de legenda. Entre uma fase e
outra você não escreve nada; volta a escrever quando tiver pergunta para ele ou resultado
na mão.

## Fases

| # | Fase | O que roda | Artefato |
|---|---|---|---|
| 1 | Spec | skill `superpowers:brainstorming` | `docs/vesta/specs/YYYY-MM-DD-<topico>-design.md` |
| 2 | Pesquisa | `research.md` (nesta pasta) | `docs/vesta/research/YYYY-MM-DD-<topico>-research.md` |
| 3 | Grill | `grill.md` (nesta pasta) | spec revisada in-place + seção `## Decisões do grill` |
| 4 | Plano | `plano.md` (nesta pasta) | `docs/vesta/plans/YYYY-MM-DD-<feature>.md` + estado criado |
| 5 | Execução | `execucao.md` (nesta pasta) | um commit por etapa, todas provadas |

Crie um todo por fase, na ordem, antes de começar.

## OVERRIDE DO BRAINSTORMING — leia antes da fase 1

O `superpowers:brainstorming` classifica o pedido em três caminhos e fecha cada um de um
jeito. Aqui, instrução do usuário tem precedência sobre skill — o próprio superpowers
estabelece isso:

- **Architectural.** Quando ele mandar invocar `writing-plans`, PARE e entre na fase 2. O
  `writing-plans` não faz parte deste fluxo: o plano é a fase 4.
- **Bounded** (mudança pequena em fluxo que já existe). Quando ele mandar implementar, não
  implemente. Pule as fases 2, 3 e 4, crie o estado com uma etapa só e entre na fase 5. O
  design aprovado no chat conta como parada 1 e é o texto da etapa. Projeto sem comando de
  teste: acrescente antes a etapa `0`, que monta o mínimo para rodar testes.

  ```bash
  python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py criar <<'JSON'
  {"plano": "chat", "teste": "<comando de teste>", "tela": [],
   "etapas": [{"id": "1", "titulo": "<o pedido>", "tela": false}]}
  JSON
  ```

- **Spike.** Segue como o brainstorming manda: a resposta é uma recomendação, não código que
  fica.

A aprovação do brainstorming continua valendo: nada de código antes do design aprovado.

## Regras de fase

- Não avance de fase sem o artefato da fase anterior existir em disco. Confira.
- Fases 2 e 3 só pulam se o usuário pedir explicitamente ("pula a pesquisa", "vai direto
  pro plano"), ou no caminho bounded. Registre o pulo numa linha no fim da spec, quando houver
  spec.
- Spec decomposta em sub-projetos: cada sub-projeto roda o ciclo inteiro sozinho.
  Não pesquise/grille os quatro de uma vez.
- Fases 2 a 5: leia o `.md` correspondente nesta pasta na hora de entrar na fase, não antes.

## Fase 1 — Spec

Invoque `superpowers:brainstorming`. Siga inteiro. Pare no ponto do override acima.

## Fase 2 — Pesquisa

Leia `research.md` nesta pasta e siga.

Entrada: a spec da fase 1. Saída: dossiê de achados + fila de pontos quentes.

## Fase 3 — Grill

Leia `grill.md` nesta pasta e siga.

Entrada: spec + dossiê. Saída: spec corrigida, cada decisão rastreada ao achado que a
motivou.

## Fase 4 — Plano

Leia `plano.md` nesta pasta e siga, sobre a spec **revisada**, não a original. Termina na
parada 1: o usuário aprova o plano.

## Fase 5 — Execução

Depois da aprovação, leia `execucao.md` nesta pasta e siga. Um hook não deixa você parar
enquanto houver etapa sem prova. Termina na parada 2: o usuário testa a feature.

## Retomada

Execução interrompida (Esc, limite de uso, erro de API, /clear): o aviso aparece no começo da
próxima sessão do projeto. `/spec-flow-retomar` passa a execução para a sessão atual;
`/spec-flow-pausar` para de propósito, mantendo o estado.

## As mensagens das paradas

Cinco linhas cada. Parada 1: o que o plano vai fazer, o que trava, o que decidir agora.
Parada 2: o que ficou pronto, o que travou, como testar.

Não repita o que está nos arquivos. Cite só o caminho que o usuário abre em seguida.

Não liste estado que não mudou: working tree sujo de antes, commits que já existiam,
pendência de handoff anterior. Se algo disso for bloqueante, é uma linha na parte do
"o que trava"; se não for, fica fora.

Correção de achado errado descoberta no caminho entra, sempre — em uma frase, dizendo o
que muda para o usuário, não o número do achado.
````

- [ ] **Passo 4: Atualizar o `~/.claude/CLAUDE.md`**

Na seção "Fluxo de trabalho criativo", trocar:

```
`spec-flow` (`~/.claude/skills/spec-flow/SKILL.md`): spec → pesquisa → grill → plano.
Invocar via Skill tool antes de escrever qualquer código.

Isso substitui o gate final do `superpowers:brainstorming`, que manda ir direto pro
`writing-plans`. Instrução do usuário tem precedência sobre skill.
```

por:

```
`spec-flow` (`~/.claude/skills/spec-flow/SKILL.md`): spec → pesquisa → grill → plano →
execução. Invocar via Skill tool antes de escrever qualquer código.

Isso substitui o fim do `superpowers:brainstorming`, que manda ir direto pro `writing-plans`
ou implementar direto. Instrução do usuário tem precedência sobre skill.
```

- [ ] **Passo 5: Conferir**

```bash
grep -n -E 'writing-plans|Regras dos gates|quatro fases' ~/.claude/skills/spec-flow/SKILL.md
```

Esperado: só as linhas do override que dizem que o `writing-plans` não faz parte do fluxo.

---

### Tarefa 7: Neste repositório — pre-commit, ADR, referência e backup

**Arquivos:**
- Mudar: `panel/hooks/pre-commit`
- Criar: `docs/decisions/0016-execucao-travada-por-provas.md`
- Mudar: `docs/reference/vesta.md`
- Atualizar: `config/claude/` via `backup/sync.sh`

- [ ] **Passo 1: Reescrever `panel/hooks/pre-commit`**

```sh
#!/bin/sh
# Roda os testes antes de deixar o commit passar.
# Instalar: git config core.hooksPath panel/hooks
#
# Cada bloco só age quando o commit toca a pasta dele.
raiz=$(git rev-parse --show-toplevel)
mudou=$(git diff --cached --name-only)

if printf '%s\n' "$mudou" | grep -qE '^(docs|panel)/'; then
  if [ -d "$raiz/panel/node_modules" ]; then
    npm test --prefix "$raiz/panel" --silent || {
      echo "" >&2
      echo "pre-commit: o formato do wayfinder quebrou. Ver docs/wayfinder/TRACKER.md." >&2
      exit 1
    }
  else
    echo "pre-commit: panel/node_modules não existe, pulando o teste de formato." >&2
  fi
fi

# A cópia do backup traz o script, os testes e o settings.json que registra os hooks.
if printf '%s\n' "$mudou" | grep -qE '^config/claude/(skills/spec-flow/|settings\.json$)'; then
  python3 -m unittest discover -q -s "$raiz/config/claude/skills/spec-flow/scripts" -p 'test_*.py' || {
    echo "" >&2
    echo "pre-commit: os testes do spec-flow quebraram. Ver config/claude/skills/spec-flow/scripts." >&2
    exit 1
  }
fi
```

- [ ] **Passo 2: Escrever o ADR-0016**

`docs/decisions/0016-execucao-travada-por-provas.md`:

```markdown
# ADR-0016 — A execução do spec-flow é travada por provas, não por instrução

Data: 2026-09-25. Status: em vigor. Aplica o ADR-0014 ao spec-flow.

## Contexto

O spec-flow terminava no plano. Daí em diante a qualidade dependia de instrução em prosa, e o
agente parava antes do fim, declarava pronto sem testar e repetia erros já corrigidos. O
Helix, da Shopify (https://shopify.engineering/helix), resolve o mesmo problema com etapas
pequenas e provas que a etapa precisa passar antes da seguinte.

Spec: `docs/vesta/specs/2026-09-25-spec-flow-execucao-design.md`. Pesquisa:
`docs/vesta/research/2026-09-25-spec-flow-execucao-research.md`.

## A decisão

O spec-flow ganha a fase 5. Um hook de parada lê o estado da execução e devolve o agente ao
trabalho enquanto houver etapa sem prova. A prova de teste é rodada por um script, não
declarada pelo agente, e vale para um commit exato com a árvore limpa.

A fase 4 deixa de usar o `superpowers:writing-plans`: o formato de etapas e o fim da fase são
do spec-flow, e o texto do superpowers muda entre versões.

Limites: 8 tentativas vermelhas por prova travam a etapa; mais de 5 bloqueios seguidos sem
mudança liberam a parada e marcam a execução como interrompida. O Claude Code já corta
sozinho em 8 bloqueios seguidos, sem avisar o hook.

Os nomes são "etapa" e "prova", e não os do Helix, porque "checkpoint" e "gate" já tinham
outro sentido neste setup.

## O que o hook não cobre

O hook de parada não dispara no Esc, em erro de API nem em limite de uso. Nesses casos a
sessão para e o estado fica dizendo que a execução está ativa. A saída é um aviso no começo
da sessão seguinte e o comando `/spec-flow-retomar`.

A guarda que cala a notificação do supacode durante a execução está no comando que o
supacode gerencia. Se ele reescrever o próprio hook, a guarda some; o teste do registro, que o
pre-commit roda sobre a cópia do backup, reprova quando isso acontecer.

## O que fica pendente

Partes 2 a 4 da spec: revisão adversária, prova visual com protótipo, arquivo de aprendizados.
Cada uma entra quando a parte 1 tiver rodado numa feature real.
```

- [ ] **Passo 3: Atualizar `docs/reference/vesta.md`**

Trocar o começo do arquivo, do título até o fim da lista numerada, por:

```markdown
# spec-flow

Arquivos vivos: `~/.claude/skills/spec-flow/SKILL.md`, `research.md`, `grill.md`, `plano.md`,
`execucao.md` e `scripts/spec_flow.py`. Comandos: `/spec-flow-retomar`, `/spec-flow-pausar`.
Criada em 2026-08-06; fase 5 em 2026-09-25 ([ADR-0016](../decisions/0016-execucao-travada-por-provas.md)).

Ideia crua vira feature pronta passando por cinco fases, nenhuma pula:

1. Spec — roda `superpowers:brainstorming`, produz `docs/vesta/specs/YYYY-MM-DD-<topico>-design.md`
2. Pesquisa — `research.md`, três Explore mais busca web em paralelo, produz dossiê de achados e uma fila de pontos quentes
3. Grill — `grill.md`, o `grill-me` alimentado pela fila do dossiê, produz a spec corrigida com uma seção de decisões
4. Plano — `plano.md`, plano em etapas da mais simples à mais complexa, e o estado da execução criado
5. Execução — `execucao.md`, cada etapa com teste escrito antes do código, confirmado vermelho, implementado e provado verde num commit; um hook de parada não deixa o agente parar antes

Pedido pequeno (o caminho "bounded" do brainstorming) pula as fases 2 a 4 e entra na 5 com uma
etapa só.
```

E trocar a seção "## O override do brainstorming" inteira por:

```markdown
## O override do brainstorming

O `superpowers:brainstorming` fecha cada caminho de um jeito: o arquitetural manda invocar o
`writing-plans`, o bounded manda implementar direto. O `SKILL.md` intercepta os dois, apoiado
na regra de precedência do próprio superpowers: instrução do usuário ganha de skill. O
`writing-plans` saiu do fluxo em 2026-09-25.

O gate de aprovação continua valendo: nada de código antes do design aprovado.
```

- [ ] **Passo 4: Copiar a configuração viva para o repositório e rodar os testes na cópia**

```bash
cd /Users/luccassilveira/Code/claude-tooling && bash backup/sync.sh
python3 -m unittest discover -q -s config/claude/skills/spec-flow/scripts -p 'test_*.py'
```

Esperado: `Ran 34 tests`, `OK`.

- [ ] **Passo 5: Commit**

```bash
cd /Users/luccassilveira/Code/claude-tooling
git add panel/hooks/pre-commit docs/decisions/0016-execucao-travada-por-provas.md \
  docs/reference/vesta.md docs/vesta/plans/2026-09-25-spec-flow-execucao-parte-1.md \
  config/claude/skills/spec-flow config/claude/commands config/claude/settings.json config/claude/CLAUDE.md
git commit -m "feat(spec-flow): fase 5, execução travada pela prova de teste"
```

Esperado: o pre-commit roda os testes do painel e os do spec-flow, e o commit passa. Não
adicionar `.gitignore`, `.DS_Store` nem `.ignore`, que já estavam soltos antes deste trabalho.

---

### Tarefa 8: Prova real

Não é automatizável: exige uma sessão nova e uma feature de verdade. Feita com o usuário.

- [ ] **Passo 1:** abrir uma sessão nova num projeto real com testes, escolhido pelo usuário, e
  pedir uma feature pequena. Esperado: o brainstorming classifica, o spec-flow intercepta, e o
  estado é criado (`python3 ~/.claude/skills/spec-flow/scripts/spec_flow.py mostrar`).
- [ ] **Passo 2:** aprovar o plano. Esperado: a execução anda sem voltar ao usuário, com um
  commit de teste e um de implementação por etapa.
- [ ] **Passo 3:** provocar uma falha de prova — por exemplo, um caso de borda que a primeira
  implementação não cobre. Esperado: `prova teste` vermelha, tentativa contada, correção,
  verde.
- [ ] **Passo 4:** apertar Esc no meio de uma etapa e abrir sessão nova no mesmo projeto.
  Esperado: o aviso de execução interrompida no começo; `/spec-flow-retomar` continua de onde
  parou.
- [ ] **Passo 5:** registrar o resultado como sessão em `docs/sessions/` e, se algo falhou,
  como achado no ADR-0016.
