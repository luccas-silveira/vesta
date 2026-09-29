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
import urllib.request

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
         'mockup': d.get('mockup'), 'tela_existente': bool(d.get('tela_existente')),
         'sessao': None, 'espera': 'plano', 'motivo': None,
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
    exigir_provas(r, os.path.dirname(m))
    if not e.get('tela_existente'):
        exigir_direcoes(r)


def rastreados(r, pasta):
    """Nomes dos arquivos rastreados direto em `pasta` (sem subpastas)."""
    saida = git(r, 'ls-files', '--', pasta + '/') or ''
    return {os.path.basename(f) for f in saida.splitlines() if os.path.dirname(f) == pasta}


def melhor(grupos, sufixos):
    """O grupo (rodada ou tela) com mais arquivos presentes; None quando não há nenhum."""
    return max(sorted(grupos), key=lambda g: sum(g + s in grupos[g] for s in sufixos), default=None)


def exigir_provas(r, pasta):
    """As provas da verificação da vesta-interface, commitadas em `pasta`, com o mesmo N."""
    nomes = rastreados(r, pasta)
    if 'relatorio.md' not in nomes:
        raise Recusa(f'falta {pasta}/relatorio.md commitado: rode a verificação da vesta-interface')
    sufixos = ('-375.png', '-1440.png', '-detector-375.json', '-detector-1440.json')
    rodadas = {}
    for n in nomes:
        m = re.fullmatch(r'(r\d+)(-375\.png|-1440\.png|-detector-375\.json|-detector-1440\.json)', n)
        if m:
            rodadas.setdefault(m[1], set()).add(n)
    rn = melhor(rodadas, sufixos) or 'r<N>'
    for s in sufixos:
        if rn + s not in nomes:
            raise Recusa(f'falta {pasta}/{rn + s} commitado (prints e detectores da mesma rodada)')
    for s in sufixos[2:]:
        try:
            with open(os.path.join(r, pasta, rn + s)) as f:
                json.load(f)
        except (OSError, ValueError):
            raise Recusa(f'{pasta}/{rn + s} não é JSON válido: grave a saída do detector em JSON')


def exigir_direcoes(r):
    """As duas direções da tela nova e os quatro prints delas (passo 3 da vesta-interface)."""
    pasta = 'docs/design/mockups'
    nomes = rastreados(r, pasta)
    sufixos = ('-a.html', '-b.html', '-a-375.png', '-a-1440.png', '-b-375.png', '-b-1440.png')
    telas = {}
    for n in nomes:
        m = re.fullmatch(r'(.+)-[ab](\.html|-375\.png|-1440\.png)', n)
        if m:
            telas.setdefault(m[1], set()).add(n)
    t = melhor(telas, sufixos) or '<tela>'
    for s in sufixos:
        if t + s not in nomes:
            raise Recusa(f'falta {pasta}/{t + s} commitado: as duas direções da tela nova e os prints '
                         'delas (tela que já existe: "tela_existente": true no criar)')


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
    if x.get('tela'):
        exigir_provas(r, os.path.join(os.path.dirname(e.get('mockup') or ''), f'etapa-{x["id"]}'))
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


def cmd_painel(r, args):
    import painel
    url = painel.subir(r)
    if not url:
        raise Recusa('não há Vesta neste projeto (docs/vesta ou .claude/vesta)')
    subprocess.run(['open', url])
    return url


def cmd_aberto(r, args):
    """Código de saída, sem imprimir: 0 com a página do painel da raiz de args[0] aberta."""
    try:
        import painel
        url = painel.achar(raiz(args[0]))
        with urllib.request.urlopen(f'{url}/aberto', timeout=1) as resp:
            return 0 if json.load(resp).get('aberto') is True else 1
    except Exception:
        return 1


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
        e['tela_existente'] = bool(novas.get('tela_existente', e.get('tela_existente')))
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
    out = aviso_inicio(r, entrada)
    try:
        import painel
        url = painel.subir(r)
    except Exception:
        url = None
    if not url:
        return out
    linha = f'Painel deste projeto: {url}'
    visivel = f'vesta: painel de {os.path.basename(r)} em {url}'
    if out is None:
        return {'systemMessage': visivel,
                'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': linha}}
    out['hookSpecificOutput']['additionalContext'] += ' ' + linha
    out['systemMessage'] += '\n' + visivel
    return out


def aviso_inicio(r, entrada):
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


def pedir(url, corpo=None):
    """JSON de uma chamada HTTP curta; erro de rede ou HTTP levanta."""
    dados = None if corpo is None else json.dumps(corpo).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=dados), timeout=1.5) as resp:
        return json.load(resp)


def texto_das(answers):
    """{"<pergunta>": {"labels", "text"}} -> {"<pergunta>": texto}; texto livre vence os rótulos."""
    return {q: a.get('text') or ', '.join(a.get('labels') or []) for q, a in answers.items()}


def hook_menu(entrada):
    """PreToolUse de AskUserQuestion: com a página do painel aberta, a pergunta vai ao painel e
    ao Knobler; vale a 1ª resposta. Sem painel, prazo ou erro: sai mudo e o menu fica no terminal."""
    import painel
    import time
    try:
        url = painel.achar(raiz(entrada.get('cwd')))
        if not url or pedir(f'{url}/aberto').get('aberto') is not True:
            return None
    except Exception:
        return None
    questions = (entrada.get('tool_input') or {}).get('questions')
    tid = entrada.get('tool_use_id') or ''
    id_ = f'menu-{tid}'
    kn = f'http://localhost:{os.environ.get("KNOBLER_PORT", "4477")}'
    try:
        pedir(f'{kn}/ask', {'id': id_, 'source': os.path.basename(entrada.get('cwd') or ''),
                            'questions': questions})
        knobler = True
    except Exception:
        knobler = False
    no_painel = True
    fim = time.time() + float(os.environ.get('VESTA_PRAZO_MENU', 3600))
    intervalo = float(os.environ.get('VESTA_INTERVALO_MENU', 1))
    answers = None
    try:
        pedir(f'{url}/pergunta', {'id': id_, 'questions': questions, 'knobler': knobler})
        while time.time() < fim and (knobler or no_painel):
            if no_painel:
                p = pedir(f'{url}/pergunta/{id_}')
                if p.get('estado') == 'respondida':
                    answers, onde = p['answers'], 'painel'
                    break
                no_painel = p.get('estado') != 'abandonada'
            if knobler:
                k = pedir(f'{kn}/ask/{id_}')
                if k.get('answered'):
                    answers, onde = k.get('answers') or {}, 'knobler'
                    break
                knobler = not k.get('cancelled')
            time.sleep(intervalo)
    except Exception:
        pass
    if answers is None or onde == 'painel':
        try:
            if knobler:
                pedir(f'{kn}/ask/{id_}/cancel', {})
        except Exception:
            pass
    if answers is None:
        return None
    if onde == 'knobler' and no_painel:
        try:
            pedir(f'{url}/pergunta/{id_}/encerrar', {'motivo': 'knobler'})
        except Exception:
            pass
    pasta = os.path.join(os.path.expanduser('~'), '.claude', 'vesta')
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, 'respostas.jsonl'), 'a') as f:
        f.write(json.dumps({'tool_use_id': tid, 'onde': onde}) + '\n')
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                                   'updatedInput': {'questions': questions,
                                                    'answers': texto_das(answers)}}}


def hook_ativacao(entrada):
    """PreToolUse de Skill: ativar a `vesta` sobe o painel da raiz, mesmo sem Vesta no projeto,
    e abre a página se ela não estiver aberta. Nunca decide a permissão da ferramenta."""
    if (entrada.get('tool_input') or {}).get('skill') != 'vesta':
        return None
    import painel
    r = raiz(entrada.get('cwd'))
    try:
        url = painel.achar(r)
        if url and pedir(f'{url}/aberto').get('aberto') is True:
            return None
    except Exception:
        pass
    url = painel.subir(r, forcar=True)
    if url:
        try:
            subprocess.run([os.environ.get('VESTA_ABRIR', 'open'), url], capture_output=True, timeout=5)
        except Exception:
            pass
    return None


COMANDOS = {'criar': cmd_criar, 'iniciar': cmd_iniciar, 'mostrar': cmd_mostrar,
            'prova': cmd_prova, 'concluir': cmd_concluir, 'retomar': cmd_retomar,
            'pausar': cmd_pausar, 'adicionar': cmd_adicionar, 'fechar': cmd_fechar,
            'guarda': cmd_guarda, 'painel': cmd_painel, 'aberto': cmd_aberto}
HOOKS = {'hook-parada': hook_parada, 'hook-inicio': hook_inicio, 'hook-adocao': hook_adocao,
         'hook-menu': hook_menu, 'hook-ativacao': hook_ativacao}


def main(argv):
    if argv and argv[0] in HOOKS:
        return rodar_hook(HOOKS[argv[0]])
    if argv and argv[0] == 'silenciar':
        return silenciar()
    if not argv or argv[0] not in COMANDOS:
        print('uso: vesta.py ' + '|'.join([*COMANDOS, *HOOKS]), file=sys.stderr)
        return 2
    if argv[0] == 'aberto':  # responde só pelo código de saída
        return cmd_aberto(None, argv[1:])
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
