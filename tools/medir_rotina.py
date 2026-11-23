"""Rotina do dia a dia, cronometrada, no motor real do bot (banco de TESTE do tamanho do real).

    python tools/medir_rotina.py [--voltas 10]

Cada volta: 3 lançamentos completos (texto -> botões -> salvar), 1 baixa de fixo
(escolhe a conta -> confirma), painel em imagem (Início, Análises, A pagar) e a
navegação mais comum (Início, mês seguinte/anterior, A pagar, Histórico, Saldo).
Mostra o tempo de cada passo (mediana e pior caso) e o total de cada volta, para
ver se a máquina desacelera com uso seguido. Confere que tudo foi gravado.
"""
import argparse
import sqlite3
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'tools'))

import database as db  # noqa: E402
from medir_desempenho import HOJE, montar_banco  # noqa: E402

TEMPOS = defaultdict(list)


def acoes(tela):
    return [tuple(a) for linha in (tela.rows if tela else []) for _, a in linha if a]


def achar(tela, tipo, arg=None):
    for a in acoes(tela):
        if a[0] == tipo and (arg is None or (len(a) > 1 and a[1] == arg)):
            return a
    raise AssertionError(f'tela sem a ação {tipo!r} {arg!r}: {acoes(tela)[:8]}')


def passo(nome, funcao):
    t0 = time.perf_counter()
    r = funcao()
    TEMPOS[nome].append(time.perf_counter() - t0)
    return r


def lancar(e, k, texto, respostas):
    e.invalidate(k)
    tela = passo('lançar: digitar o gasto', lambda: e.handle_text(k, texto))
    for r in respostas:
        tela = passo('lançar: tocar botão da etapa', lambda r=r, tela=tela: e.act(k, achar(tela, 'answer', r)))
    return passo('lançar: salvar', lambda: e.act(k, achar(tela, 'commit')))


def baixar(e, k, fixo_id, conta):
    e.invalidate(k)
    tela = passo('baixa: abrir', lambda: e.act(k, ('settle', fixo_id, HOJE.strftime('%Y-%m'))))
    tela = passo('baixa: escolher conta', lambda: e.act(k, achar(tela, 'answer', conta)))
    return passo('baixa: confirmar', lambda: e.act(k, achar(tela, 'commit')))


def contar(banco):
    with closing(sqlite3.connect(banco)) as c:
        return c.execute('SELECT COUNT(*) FROM transacoes').fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--voltas', type=int, default=10)
    ap.add_argument('--pausa', type=float, default=0, help='segundos parados entre voltas (uso real: sessões espaçadas)')
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='rotina_') as pasta:
        banco = montar_banco(pasta)
        import telegram_experiencia as ux
        e = ux.Experience(date_provider=lambda: HOJE)
        k = 'rotina'
        fixos = [dict(f) for f in db.listar_compromissos() if dict(f)['tipo'] == 'fixo']
        antes = contar(banco)
        print(f'Máquina: {sys.platform}, Python {sys.version.split()[0]}; {args.voltas} voltas\n', flush=True)
        totais = []
        for v in range(args.voltas):
            if v and args.pausa:
                time.sleep(args.pausa)
            t0 = time.perf_counter()
            lancar(e, k, f'gastei 45,90 no mercado {v}', ['pix', 'Itaú'])
            lancar(e, k, f'paguei 12 de padaria {v} no débito', ['Itaú'])
            lancar(e, k, f'gastei 30 no pix lanche {v}', ['Nubank'])
            if v < len(fixos):  # cada fixo só pode ser baixado uma vez no mês (depois o bot mostra a conciliação)
                baixar(e, k, fixos[v]['id'], 'Itaú')
            for vista in ('home', 'analytics', 'pay'):
                passo(f'painel em imagem ({vista})', lambda vista=vista: e.act(k, ('chart', vista)))
            passo('navegar: Início', lambda: e.act(k, ('view', 'home')))
            passo('navegar: mês seguinte', lambda: e.act(k, ('month', 1, 'home')))
            passo('navegar: mês anterior', lambda: e.act(k, ('month', -1, 'home')))
            passo('navegar: A pagar', lambda: e.act(k, ('view', 'pay')))
            passo('navegar: Histórico', lambda: e.act(k, ('view', 'history')))
            passo('navegar: Saldo', lambda: e.act(k, ('view', 'balance')))
            totais.append(time.perf_counter() - t0)
            print(f'volta {v + 1:2d}: {totais[-1]:5.2f} s', flush=True)
        gravados = contar(banco) - antes
        esperado = args.voltas * 3 + min(args.voltas, len(fixos))  # 3 lançamentos + 1 baixa por volta
        print(f'\nGravados: {gravados} lançamentos/baixas (esperado {esperado}) -> {"OK" if gravados == esperado else "DIVERGENTE"}')
        print(f'\n{"Passo":<36} {"mediana":>8} {"pior":>8}')
        for nome, ts in TEMPOS.items():
            print(f'{nome:<36} {statistics.median(ts):7.2f}s {max(ts):7.2f}s')
        print(f'\nVolta completa: mediana {statistics.median(totais):.2f} s, pior {max(totais):.2f} s')
        if gravados != esperado:
            sys.exit(1)


if __name__ == '__main__':
    main()
