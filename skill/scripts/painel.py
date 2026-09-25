#!/usr/bin/env python3
"""Vesta, painel: dados da execução e das features. Só biblioteca padrão."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vesta  # noqa: E402
from vesta import LIMITE_TENTATIVAS, encerrada, ler, proxima, raiz  # noqa: E402,F401

DOCS = os.path.join('docs', 'vesta')
PASSOS = {'specs': 'spec', 'research': 'research', 'plans': 'plano', 'mockups': 'mockup'}
NOME = re.compile(r'^(\d{4}-\d{2}-\d{2})-(.+?)(-design|-research)?(\.md)?$')
GRILL = '## Decisões do grill'


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


def dados(r):
    erro = None
    try:
        e = ler(r)
    except ValueError as err:
        e, erro = None, str(err)
    fs = features(r)
    atual = (feature_do_plano(fs, e['plano']) if e else None) or (fs[0] if fs else None)
    return {'projeto': os.path.basename(r),
            'momento': {'tipo': 'ilegivel', 'texto': 'Estado ilegível'} if erro else momento(e),
            'estado': e, 'erro': erro, 'features': fs, 'atual': atual,
            'tempos': tempo_etapas(r, e) if e else {}}
