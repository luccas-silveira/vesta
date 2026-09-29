#!/usr/bin/env python3
"""Vesta, painel: dados da execução e das features. Só biblioteca padrão."""
import glob
import hashlib
import socket
import subprocess
import time
import urllib.request
import http.server
import urllib.parse
import json
import os
import re
from collections import Counter
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vesta  # noqa: E402
from vesta import LIMITE_TENTATIVAS, encerrada, ler, proxima, raiz  # noqa: E402,F401

DOCS = os.path.join('docs', 'vesta')
PASSOS = {'specs': 'spec', 'research': 'research', 'plans': 'plano', 'mockups': 'mockup'}
NOME = re.compile(r'^(\d{4}-\d{2}-\d{2})-(.+?)(-design|-research)?(\.md)?$')
GRILL = '## Decisões do grill'
FASES = ['ativacao', 'spec', 'pesquisa', 'grill', 'mockup', 'plano', 'execucao', 'concluida']
MARCO = re.compile(r'(?:skills/vesta|vesta/skill)/(spec|research|grill|mockup|plano|execucao)\.md')
FASE_DO_MARCO = {'research': 'pesquisa'}
ALVOS = ('file_path', 'command', 'pattern', 'url', 'query', 'description', 'skill')


def momento(e):
    if e is None:
        return {'tipo': 'vazio', 'texto': 'Nenhuma execução neste projeto'}
    if e['espera'] == 'plano':
        return {'tipo': 'plano', 'texto': 'Esperando aprovação do plano'}
    etapas = e['etapas']
    pos = {id(x): i for i, x in enumerate(etapas, 1)}
    if e['espera'] == 'interrompida':
        n = pos[id(proxima(e))] if not encerrada(e) else len(etapas)
        return {'tipo': 'pausada', 'texto': f'Pausada na etapa {n} — {e["motivo"]}'}
    trav = next((x for x in etapas if x['status'] == 'travada'), None)
    if trav:
        t = trav['provas']['teste']['tentativas']
        return {'tipo': 'travada', 'texto': f'Travada na etapa {pos[id(trav)]} depois de {t} tentativas'}
    k = len(etapas)
    if encerrada(e):
        return {'tipo': 'concluida', 'texto': f'Concluída — {k} de {k} etapas com prova'}
    return {'tipo': 'rodando', 'texto': f'Rodando na etapa {pos[id(proxima(e))]} de {k}'}


def features(r):
    grupos = {}
    for pasta, passo in PASSOS.items():
        base = os.path.join(r, DOCS, pasta)
        if not os.path.isdir(base):
            continue
        for nome in os.listdir(base):
            m = NOME.match(nome)
            if not m or (passo == 'mockup') != os.path.isdir(os.path.join(base, nome)):
                continue
            f = grupos.setdefault((m[1], m[2]), {'topico': m[2], 'data': m[1], 'spec': None,
                                                 'research': None, 'plano': None,
                                                 'mockup': None, 'grill': False})
            f[passo] = os.path.join(DOCS, pasta, nome)
    for f in grupos.values():
        if f['spec']:
            with open(os.path.join(r, f['spec'])) as arq:
                f['grill'] = GRILL in arq.read().splitlines()
    return sorted(sorted(grupos.values(), key=lambda f: f['topico']),
                  key=lambda f: f['data'], reverse=True)


def feature_do_plano(fs, plano):
    return next((f for f in fs if f['plano'] == plano), None)


def tempo_etapas(r, e):
    tempos = {}
    for x in e['etapas']:
        p = x['provas']['teste']
        t = None
        if p['vermelho'] and p['commit'] and p['resultado'] == 'verde':
            a = vesta.git(r, 'show', '-s', '--format=%ct', p['vermelho'])
            b = vesta.git(r, 'show', '-s', '--format=%ct', p['commit'])
            if a and b:
                t = (int(b) - int(a)) / 60
        tempos[x['id']] = t
    return tempos


def doc_seguro(r, rel):
    if os.path.isabs(rel):
        return None
    base = os.path.realpath(os.path.join(r, DOCS))
    p = os.path.realpath(os.path.join(r, rel))
    return p if p.startswith(base + os.sep) and os.path.isfile(p) else None


def pasta_sessoes(r):
    return os.path.join(os.environ['HOME'], '.claude', 'projects',
                        r.replace('/', '-').replace('.', '-'))


def _instante(ts):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def _do_sdk(caminho):
    with open(caminho) as f:
        for _, linha in zip(range(50), f):
            if '"entrypoint":"sdk' in linha.replace(' ', ''):
                return True
    return False


def sessao(r):
    arqs = glob.glob(os.path.join(pasta_sessoes(r), '*.jsonl'))
    if not arqs:
        return None
    # sessões do SDK (claude -p de revisores automáticos) caem na mesma pasta e não são a do usuário
    arqs = [a for a in sorted(arqs, key=os.path.getmtime, reverse=True) if not _do_sdk(a)]
    if not arqs:
        return None
    usos, saidas, marcas, ferr = {}, {}, [], Counter()
    with open(arqs[0]) as f:
        for linha in f:
            try:
                l = json.loads(linha)
            except ValueError:
                continue
            if not isinstance(l, dict):
                continue
            if l.get('timestamp'):
                marcas.append(l['timestamp'])
            msg = l.get('message') or {}
            if l.get('type') != 'assistant' or not isinstance(msg, dict):
                continue
            for c in msg.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    ferr[re.sub(r'^mcp__.+?__', '', c.get('name', ''))] += 1
            u = msg.get('usage')
            if u:
                rid = l.get('requestId')
                usos[rid] = (u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0)
                             + u.get('cache_creation_input_tokens', 0))
                saidas[rid] = u.get('output_tokens', 0)
    if not usos:
        return None
    entrada = list(usos.values())
    return {'inicio': marcas[0], 'fim': marcas[-1],
            'duracao_s': int((_instante(marcas[-1]) - _instante(marcas[0])).total_seconds()),
            'requests': len(usos), 'entrada': entrada, 'saida': sum(saidas.values()),
            'ferramentas': [[n, c] for n, c in sorted(ferr.items(), key=lambda x: (-x[1], x[0]))],
            'contexto': entrada[-1],
            # ponytail: heurística, o modelo não fica no registro; ler o modelo se ele passar a constar
            'janela': 1000000 if max(entrada) > 200000 else 200000}


def _hora(ts):
    return _instante(ts).astimezone().strftime('%H:%M')


def _alvo(nome, e):
    if nome == 'AskUserQuestion':
        return ((e.get('questions') or [{}])[0]).get('question', '')
    for k in ALVOS:
        if isinstance(e.get(k), str):
            return e[k].split('\n')[0][:120] if k == 'command' else e[k]
    return ''


def _ondes():
    ondes = {}
    try:
        with open(os.path.join(os.environ['HOME'], '.claude', 'vesta', 'respostas.jsonl')) as f:
            for linha in f:
                try:
                    l = json.loads(linha)
                    ondes[l['tool_use_id']] = l['onde']
                except (ValueError, KeyError, TypeError):
                    continue
    except OSError:
        pass
    return ondes


def rodada(r):
    arqs = glob.glob(os.path.join(pasta_sessoes(r), '*.jsonl'))
    arqs = [a for a in sorted(arqs, key=os.path.getmtime, reverse=True) if not _do_sdk(a)]
    if not arqs:
        return {'formato': 'sem'}
    conhecido, inicio, marcos, hist, ativ, respostas = False, None, {}, [], [], {}
    with open(arqs[0]) as f:
        for linha in f:
            try:
                l = json.loads(linha)
            except ValueError:
                continue
            msg = l.get('message') if isinstance(l, dict) else None
            if not isinstance(msg, dict) or not isinstance(msg.get('content'), list):
                continue
            conhecido = True
            res = l.get('toolUseResult')
            if isinstance(res, dict) and isinstance(res.get('answers'), dict):
                for c in msg['content']:
                    if isinstance(c, dict) and c.get('type') == 'tool_result':
                        respostas[c.get('tool_use_id')] = res['answers']
            if l.get('type') != 'assistant':
                continue
            ts = l.get('timestamp')
            for c in msg['content']:
                if not isinstance(c, dict):
                    continue
                if c.get('type') == 'text' and inicio:
                    hist.append({'tipo': 'mensagem', 'texto': c.get('text', ''), 'hora': _hora(ts)})
                if c.get('type') != 'tool_use':
                    continue
                nome, e = c.get('name', ''), c.get('input') or {}
                if nome == 'Skill' and e.get('skill') == 'vesta':
                    inicio, marcos, hist, ativ = ts, {}, [], []
                if not inicio:
                    continue
                ativ.append({'ferramenta': re.sub(r'^mcp__.+?__', '', nome),
                             'alvo': _alvo(nome, e), 'hora': _hora(ts)})
                alvo = e.get('file_path') if nome == 'Read' else e.get('command') if nome == 'Bash' else None
                if isinstance(alvo, str):
                    m = MARCO.search(alvo)
                    fase = FASE_DO_MARCO.get(m[1], m[1]) if m else (
                        'execucao' if nome == 'Bash' and re.search(r'vesta\.py (?:criar|iniciar)', alvo) else None)
                    if fase:
                        marcos.pop(fase, None)
                        marcos[fase] = ts
                if nome == 'AskUserQuestion':
                    for q in e.get('questions') or []:
                        hist.append({'id': c.get('id'), 'header': q.get('header'),
                                     'pergunta': q.get('question'), 'multipla': bool(q.get('multiSelect')),
                                     'rotulos': [o.get('label') for o in q.get('options') or []],
                                     'hora': _hora(ts)})
    if not conhecido:
        return {'formato': 'desconhecido'}
    if not inicio:
        return {'formato': 'nenhuma'}
    ondes = _ondes()
    for h in hist:
        if 'pergunta' in h:
            resp = (respostas.get(h['id']) or {}).get(h['pergunta'])
            rot = h.pop('rotulos')
            h.update(resposta=resp, onde=ondes.get(h.pop('id'), 'terminal'),
                     livre=resp is not None and not all(p in rot for p in resp.split(', ')))
    # lê sem validar: só o status das etapas importa aqui
    try:
        with open(vesta.caminho(r)) as f:
            fim = encerrada(json.load(f))
    except (OSError, ValueError, KeyError, TypeError):
        fim = False
    atual = 7 if fim else FASES.index(list(marcos)[-1]) if marcos else 0
    fases = []
    for i, fase in enumerate(FASES):
        hora = _hora(inicio) if i == 0 else _hora(marcos[fase]) if fase in marcos else None
        estado = ('atual' if i == atual else 'pendente' if i > atual
                  else 'feita' if i == 0 or fase in marcos else 'pulada')
        fases.append({'id': fase, 'estado': estado, 'hora': hora})
    return {'formato': 'claude-code', 'sessoes': [os.path.basename(arqs[0])[:-6]],
            'inicio': _hora(inicio), 'fases': fases, 'historico': hist,
            'atividade': ativ[::-1][:200], 'n_atividade': len(ativ)}


def dados(r):
    erro = None
    try:
        e = ler(r)
    except ValueError as err:
        e, erro = None, str(err)
    fs = features(r)
    atual = (feature_do_plano(fs, e['plano']) if e else None) or (fs[0] if fs else None)
    casa = os.path.expanduser('~')
    caminho = '~' + r[len(casa):] if r.startswith(casa + os.sep) else r
    return {'projeto': os.path.basename(r), 'caminho': caminho,
            'momento': {'tipo': 'ilegivel', 'texto': 'Estado ilegível'} if erro else momento(e),
            'estado': e, 'erro': erro, 'features': fs, 'atual': atual,
            'tempos': tempo_etapas(r, e) if e else {}, 'sessao': sessao(r),
            'rodada': rodada(r)}


def servir(r, porta):
    aqui = os.path.dirname(os.path.abspath(__file__))
    estaticos = {'/': ('painel.html', 'text/html; charset=utf-8'),
                 '/marked.js': ('marked.js', 'text/javascript; charset=utf-8')}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def responder(self, corpo, tipo='text/plain; charset=utf-8', status=200):
            self.send_response(status)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            u = urllib.parse.urlsplit(self.path)
            if u.path == '/estado':
                return self.responder(json.dumps(dados(r)).encode(), 'application/json')
            if u.path == '/quem':
                return self.responder(f'vesta-painel {r}'.encode())
            if u.path == '/doc':
                rel = urllib.parse.parse_qs(u.query).get('caminho', [''])[0]
                p = doc_seguro(r, rel) if rel else None
                if p:
                    with open(p, 'rb') as f:
                        return self.responder(f.read(), 'text/html; charset=utf-8'
                                              if p.endswith('.html') else 'text/plain; charset=utf-8')
            elif u.path in estaticos:
                nome, tipo = estaticos[u.path]
                with open(os.path.join(aqui, nome), 'rb') as f:
                    return self.responder(f.read(), tipo)
            self.responder(b'', status=404)

    try:
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', porta), Handler)
    except OSError:
        return 0
    srv.daemon_threads = True
    srv.serve_forever()


def porta(r):
    return 4700 + int(hashlib.sha1(r.encode()).hexdigest()[:4], 16) % 100


def _quem(n):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{n}/quem', timeout=0.5) as resp:
            return resp.read().decode().strip()
    except Exception:
        return None


def _ocupada(n):
    try:
        socket.create_connection(('127.0.0.1', n), timeout=0.3).close()
        return True
    except OSError:
        return False


def subir(r):
    if not (os.path.isdir(os.path.join(r, 'docs', 'vesta'))
            or os.path.isdir(os.path.join(r, '.claude', 'vesta'))):
        return None
    base = porta(r)
    for i in range(100):
        n = 4700 + (base - 4700 + i) % 100
        if _ocupada(n):
            if _quem(n) == f'vesta-painel {r}':
                return f'http://localhost:{n}'
            continue
        subprocess.Popen([sys.executable, os.path.abspath(__file__), 'servir', r, str(n)],
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        fim = time.time() + 2
        while time.time() < fim:
            if _ocupada(n):
                return f'http://localhost:{n}'
            time.sleep(0.05)
    return None


if __name__ == '__main__' and sys.argv[1:2] == ['servir']:
    sys.exit(servir(os.path.abspath(sys.argv[2]), int(sys.argv[3])))
