#!/usr/bin/env python3
"""Vesta, fase 5: estado da execução, provas e hooks. Só biblioteca padrão.

Uso: vesta.py <comando> [argumentos]. Os comandos estão em COMANDOS e HOOKS, no fim.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

PASTA = os.path.join('.claude', 'vesta')
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
    """Raiz do projeto, de qualquer subpasta. O hook passa o cwd da própria entrada, que
    vale mais que CLAUDE_PROJECT_DIR: o agente, que não tem essa variável, grava pelo cwd."""
    base = cwd or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    return git(base, 'rev-parse', '--show-toplevel') or base


def caminho(r):
    return os.path.join(r, PASTA, 'estado.json')


def ler(r):
    """None se não há execução. Estado ilegível ou fora do formato levanta ValueError."""
    try:
        with open(caminho(r)) as f:
            e = json.load(f)
    except FileNotFoundError:
        return None
    validar(e)
    return e


def validar(e):
    try:
        assert isinstance(e['teste'], str) and isinstance(e['bloqueios']['seguidos'], int)
        assert e['espera'] in ('plano', 'interrompida', None)
        for x in e['etapas']:
            assert x['status'] in ('pendente', 'feita', 'travada') and isinstance(x['id'], str)
            assert isinstance(x['provas']['teste']['tentativas'], int)
    except (AssertionError, KeyError, TypeError) as err:
        raise ValueError(f'estado fora do formato em {PASTA}/estado.json') from err


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
        raise Recusa('não há execução da Vesta neste projeto')
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
        raise Recusa('já existe execução neste projeto: retome (/vesta-retomar) ou feche (fechar)')
    if git(r, 'rev-parse', '--git-dir') is None:
        raise Recusa('a Vesta precisa de um repositório git: cada etapa termina num commit')
    d = ler_entrada()
    if not isinstance(d, dict) or not d.get('teste') or not d.get('etapas'):
        raise Recusa('criar espera um JSON com plano, teste e etapas')
    e = {'versao': 1, 'plano': d.get('plano', ''), 'teste': d['teste'], 'tela': d.get('tela', []),
         'mockup': d.get('mockup'), 'sessao': None, 'espera': 'plano', 'motivo': None,
         'bloqueios': {'seguidos': 0, 'assinatura': ''}, 'etapas': []}
    acrescentar(e, d['etapas'])
    gravar(r, e)
    return f'estado criado em {r} com {len(e["etapas"])} etapa(s), esperando aprovação do plano'


def exigir_mockup(r, e, etapas):
    """Plano com tela só executa com o mockup aprovado commitado."""
    if not (e.get('tela') or any(x.get('tela') for x in etapas)):
        return
    m = e.get('mockup')
    if not m or git(r, 'ls-files', '--error-unmatch', m) is None:
        raise Recusa('o plano tem tela e não há mockup aprovado e commitado; faça o mockup '
                     '(mockup.md) antes de executar')


def cmd_iniciar(r, args):
    e = exigir(r)
    if e['espera'] != 'plano':
        raise Recusa('iniciar só vale com o plano esperando aprovação')
    exigir_mockup(r, e, e['etapas'])
    if git(r, 'status', '--porcelain'):
        raise Recusa('há mudanças não commitadas neste projeto; antes da execução, o usuário '
                     'decide o que fazer com elas (commit ou stash)')
    e.update(espera=None, sessao='adotar')
    gravar(r, e)
    return f'execução iniciada em {r}; a trava vale para esta sessão'


def cmd_mostrar(r, args):
    return json.dumps(exigir(r), ensure_ascii=False, indent=2)


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
    if tipo == 'vermelho':
        arquivos = (git(r, 'diff-tree', '--no-commit-id', '--name-only', '-r', '--root', 'HEAD')
                    or '').splitlines()
        if not arquivos:
            raise Recusa('o último commit não tem nenhum arquivo; commite os testes da etapa antes '
                         'de confirmar o vermelho')
    else:
        mexidos = set((git(r, 'diff', '--name-only', t['vermelho'], 'HEAD') or '').splitlines())
        if mexidos & set(t.get('arquivos', [])):
            t['vermelho'] = None
            gravar(r, e)
            raise Recusa('os testes mudaram depois do vermelho; o implementador não mexe neles. '
                         f'Se a mudança é do escritor, confirme o vermelho de novo: prova vermelho {id_}')
    codigo, saida = rodar_teste(r, e)
    if codigo in (126, 127):
        raise Recusa(f'o comando de teste não roda (saída {codigo}):\n{cauda(saida, 5)}')
    if tipo == 'vermelho':
        if codigo is None:
            raise Recusa(saida)
        if codigo == 0:
            raise Recusa('os testes passaram antes do código existir; eles não provam a etapa. '
                         'Refaça os testes.')
        # A falha precisa vir dos testes novos, não de executor ausente ou mal configurado.
        # ponytail: basta a saída citar o nome de um dos arquivos; executor que não imprime
        # nomes pede o modo detalhado no comando de teste do plano.
        nomes = {os.path.splitext(os.path.basename(a))[0].lower() for a in arquivos}
        if not any(n and n in saida.lower() for n in nomes):
            raise Recusa('a falha não cita nenhum dos arquivos de teste do último commit '
                         f'({", ".join(arquivos)}); pode ser o executor ausente ou mal configurado, '
                         f'e não os testes novos:\n{cauda(saida, 10)}')
        t.update(vermelho=head, arquivos=arquivos)
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
    if x['status'] != 'pendente':
        raise Recusa(f'a etapa {args[0]} já está {x["status"]}')
    head = git(r, 'rev-parse', 'HEAD')
    t = x['provas']['teste']
    if t['resultado'] != 'verde' or t['commit'] != head:
        raise Recusa(f'a prova de teste da etapa {args[0]} não está verde neste commit; '
                     f'rode prova teste {args[0]}')
    # Arquivo não rastreado criado pelo próprio teste (relatório, cobertura) não invalida a prova.
    if git(r, 'status', '--porcelain', '--untracked-files=no'):
        raise Recusa('há arquivo rastreado mudado depois da prova; commite e rode prova teste de novo')
    x['status'] = 'feita'
    gravar(r, e)
    return f'etapa {args[0]} feita'


def pendencia(x, head):
    t = x['provas']['teste']
    if not t['vermelho']:
        return 'escrever os testes, commitar e confirmar o vermelho (prova vermelho)'
    if t['resultado'] != 'verde' or t['commit'] != head:
        return 'implementar, commitar e rodar a prova de teste (prova teste)'
    return 'concluir a etapa (concluir)'


def assinatura_da_arvore(r, e, head):
    """Progresso é qualquer mudança: estado das etapas, commit, arquivo rastreado mexido, ou
    conteúdo de arquivo novo ainda fora do git."""
    novos = git(r, 'ls-files', '-o', '--exclude-standard') or ''
    conteudo = ''
    if novos:
        p = subprocess.run(['git', 'hash-object', '--stdin-paths'], cwd=r, input=novos,
                           capture_output=True, text=True)
        conteudo = p.stdout
    arvore = (git(r, 'status', '--porcelain') or '') + (git(r, 'diff', 'HEAD') or '') + conteudo
    return hashlib.sha1((json.dumps(e['etapas'], sort_keys=True) + head + arvore)
                        .encode()).hexdigest()


def situacao(entrada):
    """Lê sem gravar. None quando a parada é livre; senão o que o hook de parada precisa,
    com o contador de bloqueios já calculado para esta parada."""
    r = raiz(entrada.get('cwd'))
    try:
        e = ler(r)
    except (ValueError, OSError):
        return None  # estado ilegível: falha aberta; o aviso de início de sessão denuncia
    if not e or entrada.get('background_tasks') or git(r, 'rev-parse', '--git-dir') is None:
        return None
    sid = entrada.get('session_id') or ''
    if not sid or e.get('sessao') != sid or not ativa(e):
        return None
    head = git(r, 'rev-parse', 'HEAD') or ''
    assinatura = assinatura_da_arvore(r, e, head)
    b = e['bloqueios']
    seguidos = b['seguidos'] + 1 if b['assinatura'] == assinatura else 1
    return {'r': r, 'e': e, 'x': proxima(e), 'head': head, 'assinatura': assinatura,
            'seguidos': seguidos}


def hook_parada(entrada):
    s = situacao(entrada)
    if not s:
        return None
    r, e, x = s['r'], s['e'], s['x']
    e['bloqueios'] = {'seguidos': s['seguidos'], 'assinatura': s['assinatura']}
    if s['seguidos'] > LIMITE_BLOQUEIOS:
        e.update(espera='interrompida',
                 motivo=f'{LIMITE_BLOQUEIOS} bloqueios seguidos sem progresso na etapa {x["id"]}')
        gravar(r, e)
        return None
    gravar(r, e)
    return {'decision': 'block',
            'reason': (f'Execução da Vesta em andamento. Etapa {x["id"]} ({x["titulo"]}): falta '
                       f'{pendencia(x, s["head"])}. Siga ~/.claude/skills/vesta/execucao.md e não '
                       'pare antes de todas as etapas estarem provadas. Se o usuário pediu para '
                       'parar, rode python3 ~/.claude/skills/vesta/scripts/vesta.py pausar '
                       'e pare.')}


def silenciar():
    """Guarda dos hooks de parada de terceiros: sai 0 (calar) só quando esta parada vai ser
    bloqueada. ponytail: lê o estado em paralelo com o hook de parada; na corrida, uma
    notificação pode escapar uma vez, nunca ser engolida na parada em que a trava desiste."""
    try:
        s = situacao(ler_entrada() or {})
    except Exception:
        return 1
    return 0 if s and s['seguidos'] <= LIMITE_BLOQUEIOS else 1


def cmd_guarda(r, args):
    script = os.path.abspath(__file__)
    return (f'__e=$(mktemp); cat > "$__e"; python3 "{script}" silenciar < "$__e" && '
            '{ rm -f "$__e"; exit 0; }; exec < "$__e"; rm -f "$__e"; ')


ADOCAO = re.compile(r'vesta\.py["\']?\s+(iniciar|retomar|adicionar)\b')


def hook_adocao(entrada):
    """PostToolUse do Bash: a sessão que rodou iniciar, retomar ou adicionar vira a dona.
    Só ela: uma sessão qualquer que pare no mesmo projeto não pega a execução."""
    comando = (entrada.get('tool_input') or {}).get('command') or ''
    sid = entrada.get('session_id') or ''
    if not sid or not ADOCAO.search(comando):
        return None
    r = raiz(entrada.get('cwd'))
    e = ler(r)
    if e and e.get('sessao') == 'adotar':
        e['sessao'] = sid
        gravar(r, e)
    return None


def rodar_hook(funcao):
    try:
        saida = funcao(ler_entrada() or {})
    except Exception as err:  # hook nunca prende a sessão por defeito próprio
        print(f'vesta: {err}', file=sys.stderr)
        return 0
    if saida:
        print(json.dumps(saida, ensure_ascii=False))
    return 0


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
    if e['espera'] == 'plano':
        raise Recusa('o plano ainda espera aprovação; não há execução para pausar')
    e.update(espera='interrompida', motivo=' '.join(args) or 'pausa manual')
    gravar(r, e)
    return 'execução pausada; /vesta-retomar retoma'


def cmd_adicionar(r, args):
    e = exigir(r)
    if any(x['status'] == 'travada' for x in e['etapas']):
        raise Recusa('há etapa travada; use /vesta-retomar antes de adicionar etapas')
    novas = ler_entrada()
    if isinstance(novas, dict):  # {"mockup": ..., "etapas": [...]}: o ajuste traz a primeira tela
        e['mockup'] = novas.get('mockup') or e.get('mockup')
        novas = novas.get('etapas')
    if not isinstance(novas, list) or not novas:
        raise Recusa('adicionar espera uma lista JSON de etapas')
    exigir_mockup(r, e, novas)
    acrescentar(e, novas)
    zerar(e)
    gravar(r, e)
    return f'{len(novas)} etapa(s) nova(s); execução retomada'


def cmd_fechar(r, args):
    exigir(r)
    os.remove(caminho(r))
    return 'execução fechada'


def aviso(texto):
    texto = 'vesta: ' + texto
    return {'systemMessage': texto,
            'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                   'additionalContext': texto + ' Diga isso ao usuário na primeira resposta.'}}


def hook_inicio(entrada):
    r = raiz(entrada.get('cwd'))
    try:
        e = ler(r)
    except (ValueError, OSError):
        return aviso('o estado da execução está ilegível (.claude/vesta/estado.json).')
    if not e or e.get('espera') == 'plano':
        return None
    travada = next((x for x in e['etapas'] if x['status'] == 'travada'), None)
    if travada:
        return aviso(f'a execução travou na etapa {travada["id"]} ({travada["titulo"]}) depois de '
                     f'{LIMITE_TENTATIVAS} tentativas. /vesta-retomar tenta de novo.')
    if encerrada(e):
        return None
    x = proxima(e)
    if e.get('espera') == 'interrompida':
        return aviso(f'a execução foi interrompida na etapa {x["id"]} ({x["titulo"]}). '
                     f'Motivo: {e.get("motivo")}. /vesta-retomar retoma nesta sessão.')
    if e.get('sessao') != entrada.get('session_id'):
        return aviso(f'há execução neste projeto, parada na etapa {x["id"]} ({x["titulo"]}), '
                     'ligada a outra sessão. Se ela não está mais rodando, /vesta-retomar '
                     'a passa para esta.')
    return None


COMANDOS = {'criar': cmd_criar, 'iniciar': cmd_iniciar, 'mostrar': cmd_mostrar,
            'prova': cmd_prova, 'concluir': cmd_concluir, 'retomar': cmd_retomar,
            'pausar': cmd_pausar, 'adicionar': cmd_adicionar, 'fechar': cmd_fechar,
            'guarda': cmd_guarda}
HOOKS = {'hook-parada': hook_parada, 'hook-inicio': hook_inicio, 'hook-adocao': hook_adocao}


def main(argv):
    if argv and argv[0] in HOOKS:
        return rodar_hook(HOOKS[argv[0]])
    if argv and argv[0] == 'silenciar':
        return silenciar()
    if not argv or argv[0] not in COMANDOS:
        print('uso: vesta.py ' + '|'.join([*COMANDOS, *HOOKS]), file=sys.stderr)
        return 2
    try:
        saida = COMANDOS[argv[0]](raiz(), argv[1:])
    except (Recusa, ValueError) as err:
        print(f'vesta: {err}', file=sys.stderr)
        return 1
    if saida:
        print(saida)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
