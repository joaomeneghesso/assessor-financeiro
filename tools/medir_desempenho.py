"""Mede o tempo das operações do dia a dia num banco de TESTE do tamanho do real.

Uso (mesmo comando no PC e no servidor, para comparar):
    python tools/medir_desempenho.py [--sem-audio] [--sem-ocr]

Banco temporário (~260 lançamentos, ~45 fixos, 6 contas, jun/2026-abr/2027,
como o banco real em 14/11/2026); nunca toca data/financeiro.db.
Cada tela: 1ª vez ("fria") e mediana de 3 repetições ("quente").
"""
import argparse
import importlib.util
import math
import random
import statistics
import struct
import sys
import tempfile
import time
import wave
from datetime import date
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import database as db  # noqa: E402
import services as svc  # noqa: E402

HOJE = date(2026, 11, 14)
CONTAS = ['Itaú', 'Nubank', 'Mercado Pago', 'Caju', 'BTG', 'Inter']
CATEGORIAS = ['Alimentação', 'Mercado', 'Transporte', 'Lazer', 'Moradia', 'Saúde', 'Assinaturas', 'Viagem']


def montar_banco(pasta):
    banco = Path(pasta) / 'medicao.db'
    spec = importlib.util.spec_from_file_location('mig_medicao', RAIZ / 'migrations.py')
    mig = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mig
    spec.loader.exec_module(mig)
    for alvo in (db, svc):
        patch.object(alvo, 'DB_PATH', banco).start()
    patch.object(svc, 'BACKUPS_DIR', Path(pasta) / 'backups').start()
    db.init_db()
    mig.apply_migrations(banco, RAIZ / 'migrations', Path(pasta) / 'mig_bkp', executed_by='medicao')
    rnd = random.Random(42)
    for mes in range(6, 12):  # jun..nov/2026
        for i in range(38):
            dia = min(28, 1 + i % 28)
            db.inserir_transacao(dict(
                data=f'2026-{mes:02d}-{dia:02d}', tipo='despesa', valor=round(rnd.uniform(8, 400), 2),
                categoria=rnd.choice(CATEGORIAS), descricao=f'Compra {mes}-{i} loja {rnd.randint(1, 40)}',
                conta=rnd.choice(CONTAS), forma_pagamento=rnd.choice(['pix', 'débito', 'crédito']), parcelas_total=1))
        db.inserir_transacao(dict(data=f'2026-{mes:02d}-05', tipo='receita', valor=6500, categoria='Receita',
                                  descricao='Salário', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
    for p in range(4):  # parcelamentos até 2027
        db.inserir_parcelamento_atomico([
            dict(data=f'{2026 + (m > 12)}-{(m - 1) % 12 + 1:02d}-10', tipo='despesa', valor=150, categoria='Eletrônicos',
                 descricao=f'Parcelado {p}', conta='Nubank', forma_pagamento='crédito', parcela_atual=k, parcelas_total=6)
            for k, m in enumerate(range(9 + p, 15 + p), 1)])
    for f in range(45):
        db.inserir_compromisso(dict(tipo='fixo', nome=f'Fixo {f}', categoria=rnd.choice(CATEGORIAS),
                                    valor=round(rnd.uniform(20, 300), 2), data_inicio='2026-06-01',
                                    dia_vencimento=1 + f % 28, conta_pagamento=rnd.choice(CONTAS),
                                    forma_pagamento='pix', ativo=True))
    return banco


def cronometrar(nome, funcao, repeticoes=3):
    t0 = time.perf_counter()
    try:
        funcao()
        erro = ''
    except Exception as exc:  # mede mesmo assim e mostra o motivo
        erro = f'  ({type(exc).__name__}: {str(exc)[:60]})'
    fria = time.perf_counter() - t0
    quentes = []
    for _ in range(repeticoes):
        t0 = time.perf_counter()
        try:
            funcao()
        except Exception:
            pass
        quentes.append(time.perf_counter() - t0)
    print(f'{nome:<34} fria {fria:6.2f} s   quente {statistics.median(quentes):6.2f} s{erro}', flush=True)


def audio_teste(pasta):
    """5 s de tom com variação (passa no filtro de silêncio; custo de transcrição ~ de uma fala curta)."""
    caminho = Path(pasta) / 'teste.wav'
    with wave.open(str(caminho), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        quadros = b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * (220 + 80 * math.sin(i / 4000)) * i / 16000)))
                           for i in range(16000 * 5))
        w.writeframes(quadros)
    return caminho


def foto_teste(pasta):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (900, 300), 'white')
    d = ImageDraw.Draw(img)
    for i, linha in enumerate(['Comprovante de PIX', 'Valor: R$ 52,90', 'Data: 13/11/2026', 'Destino: Mercado Central']):
        d.text((40, 30 + i * 60), linha, fill='black', font_size=40)
    caminho = Path(pasta) / 'foto.png'
    img.save(caminho)
    return caminho


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sem-audio', action='store_true')
    ap.add_argument('--sem-ocr', action='store_true')
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='medicao_') as pasta:
        t0 = time.perf_counter()
        montar_banco(pasta)
        print(f'Banco de teste montado em {time.perf_counter() - t0:.1f} s', flush=True)
        import telegram_experiencia as ux
        e = ux.Experience(date_provider=lambda: HOJE)
        k = 'medicao'
        print(f'Máquina: {sys.platform}, Python {sys.version.split()[0]}\n', flush=True)
        cronometrar('Início (home)', lambda: e.act(k, ('view', 'home')))
        cronometrar('Saldo', lambda: e.act(k, ('view', 'balance')))
        cronometrar('A pagar', lambda: e.act(k, ('view', 'pay')))
        cronometrar('Análises', lambda: e.act(k, ('view', 'analytics')))
        cronometrar('Histórico do mês', lambda: e.act(k, ('view', 'history')))
        cronometrar('Consulta 6 meses', lambda: e.fast_deterministic_query(k, 'quanto gastei nos últimos 6 meses'))
        cronometrar('Busca em todos os meses', lambda: e.handle_text(k, 'buscar loja 7'))
        cronometrar('Lançamento por texto (prévia)', lambda: (e.invalidate(k), e.handle_text(k, 'gastei 35 no mercado')))
        cronometrar('Painel em imagem (PNG)', lambda: e.act(k, ('chart', 'home')), repeticoes=2)
        if not args.sem_ocr:
            import telegram_midia
            foto = foto_teste(pasta)
            cronometrar('Foto de comprovante (OCR)', lambda: telegram_midia.reconhecer_foto(foto), repeticoes=2)
        if not args.sem_audio:
            import transcricao_audio
            som = audio_teste(pasta)
            cronometrar('Áudio de 5 s (transcrição)', lambda: transcricao_audio.transcrever_audio(som), repeticoes=2)
            try:
                transcricao_audio._kill_worker()
            except Exception:
                pass


if __name__ == '__main__':
    main()
