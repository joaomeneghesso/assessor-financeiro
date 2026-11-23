"""RC3.0.38 — painéis de leitura; não consultam nem alteram dados financeiros.

O Telegram reduz a imagem para ~360 px no celular: por isso o PNG tem LARGURA=720 px
e nenhum texto fica abaixo de FONTE_MINIMA=28 px (a altura se ajusta ao conteúdo).
"""
import io
import re
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LARGURA=720; MARGEM=24; INTERNA=LARGURA-2*MARGEM; PAD=22
FONTE_MINIMA=28
BG='#F2F5F8'; CARD='#FFFFFF'; INK='#14263D'; MUTED='#53657B'
TEAL='#087F68'; AMBER='#98600C'; RED='#BC3549'; BLUE='#245DCF'
LINE='#DDE5ED'; TRILHO='#C9D4E0'; VIOLET='#B45309'
_ALTURA_MAX=9000
_TONS={'success':('#E3F3EA',TEAL),'danger':('#FCEBED',RED),'warning':('#FFF3D8',AMBER),'neutral':('#E8EDF3',MUTED)}


@lru_cache(maxsize=128)
def font(size,bold=False):
    names=[Path('C:/Windows/Fonts')/('segoeuib.ttf' if bold else 'segoeui.ttf'),
           Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]
    for path in names:
        if path.exists():return ImageFont.truetype(str(path),size)
    return ImageFont.load_default(size=size)


def normalizar_dinheiro(text):
    """Zero negativo nunca aparece: 'R$ -0,00' / '-R$ 0,00' / '−R$ 0,00' viram 'R$ 0,00'."""
    return re.sub(r'(?:R\$\s*[-−]|[-−]\s*R\$)\s*0,00(?!\d)','R$ 0,00',str(text))


def texto(draw,text,xy,max_width,size=FONTE_MINIMA,color=INK,bold=False):
    text=normalizar_dinheiro(str(text).replace('\n',' ')[:500])
    size=max(int(size),FONTE_MINIMA)
    face=font(size,bold)
    while size>FONTE_MINIMA and draw.textlength(text,font=face)>max_width:
        size-=1;face=font(size,bold)
    if draw.textlength(text,font=face)>max_width:
        while text and draw.textlength(text+'…',font=face)>max_width:text=text[:-1]
        text+='…'
    draw.text(xy,text,font=face,fill=color)


def _quebrar(draw,text,width,size):
    rows=[];current='';face=font(max(size,FONTE_MINIMA))
    for word in normalizar_dinheiro(text).split():
        trial=(current+' '+word).strip()
        if draw.textlength(trial,font=face)>width and current:
            rows.append(current);current=word
        else:current=trial
    if current:rows.append(current)
    return rows


def _altura_linhas(draw,text,width,size,max_lines):
    return max(1,min(len(_quebrar(draw,text,width,size)),max_lines))*(max(size,FONTE_MINIMA)+10)


def linhas(draw,text,x,y,width,size=FONTE_MINIMA,max_lines=3,color=MUTED):
    """Escreve texto quebrado em linhas; devolve o y logo abaixo do bloco."""
    size=max(size,FONTE_MINIMA);rows=_quebrar(draw,text,width,size)
    for i,row in enumerate(rows[:max_lines]):
        suffix='…' if i==max_lines-1 and len(rows)>max_lines else ''
        texto(draw,row+suffix,(x,y+i*(size+10)),width,size,color)
    return y+_altura_linhas(draw,text,width,size,max_lines)


def moeda(value):
    """R$ 1.234,56; negativo '−R$ 1.234,56' (U+2212); zero negativo vira 'R$ 0,00'."""
    d=Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    body=f'{abs(d):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return ('−' if d<0 else '')+'R$ '+body


def _negativo(value):
    return normalizar_dinheiro(value).startswith(('R$ -','-R$','−','R$ −'))


def _canvas():
    image=Image.new('RGB',(LARGURA,_ALTURA_MAX),BG);return image,ImageDraw.Draw(image)


def _finalizar(image,y,nome):
    image=image.crop((0,0,LARGURA,min(_ALTURA_MAX,max(int(y),400))))
    output=io.BytesIO();image.save(output,format='PNG',compress_level=6)
    output.seek(0);output.name=nome
    return output


def _cabecalho(draw,spec,default_title,default_sub):
    draw.rectangle((0,0,LARGURA,6),fill=TEAL)
    texto(draw,spec.get('title',default_title),(MARGEM,26),INTERNA,40,INK,True)
    texto(draw,spec.get('subtitle',default_sub),(MARGEM+1,80),INTERNA-2,FONTE_MINIMA,MUTED)
    return 132


def _hero(draw,spec,hero,y,default_tone):
    fill,color=_TONS.get(spec.get('hero_tone',default_tone),('#E8EDF3',INK))
    draw.rounded_rectangle((MARGEM,y,LARGURA-MARGEM,y+168),radius=18,fill=fill)
    texto(draw,hero['label'],(MARGEM+PAD,y+14),INTERNA-2*PAD,FONTE_MINIMA,color,True)
    texto(draw,hero['value'],(MARGEM+PAD-2,y+58),INTERNA-2*PAD,76,color,True)
    return y+168+16


def _card_largo(draw,card,y,valor_size=44):
    """Cartão em largura total: rótulo em cima, valor grande embaixo (+ dica opcional)."""
    inner=INTERNA-2*PAD
    label_h=_altura_linhas(draw,card['label'],inner,FONTE_MINIMA,2)
    hint_h=(FONTE_MINIMA+10) if card.get('hint') else 0
    h=14+label_h+valor_size+22+hint_h
    draw.rounded_rectangle((MARGEM,y,LARGURA-MARGEM,y+h),radius=16,fill=CARD,outline=LINE)
    yy=linhas(draw,card['label'],MARGEM+PAD,y+14,inner,FONTE_MINIMA,2,MUTED)
    value=str(card['value'])
    texto(draw,value,(MARGEM+PAD,yy),inner,valor_size,RED if _negativo(value) else INK,True)
    if card.get('hint'):texto(draw,card['hint'],(MARGEM+PAD,yy+valor_size+10),inner,FONTE_MINIMA,MUTED)
    return y+h+12


def painel(spec):
    """Painel de leitura compacto; recebe valores prontos do motor financeiro."""
    if spec.get('layout')=='dashboard':return painel_dashboard(spec)
    summary=spec.get('layout')=='summary'
    hero=spec.get('hero');cards=list(spec.get('cards',[]))[:3]
    all_bars=list(spec.get('bars',[]));bars=all_bars[:5]
    image,draw=_canvas();y=_cabecalho(draw,spec,'Seu painel','Atualizado nesta consulta')
    if hero:y=_hero(draw,spec,hero,y,'success')
    for card in cards:y=_card_largo(draw,card,y,48 if summary else 40)
    y+=6;inner=INTERNA-2*PAD;x=MARGEM+PAD
    if summary:
        # Apenas um complemento de leitura; detalhes financeiros ficam no botão.
        texto(draw,spec.get('headline','A RECEBER'),(MARGEM+2,y),INTERNA,FONTE_MINIMA,MUTED,True)
        y=linhas(draw,spec.get('detail',''),MARGEM+2,y+44,INTERNA-4,32,3,INK)+8
    else:
        section=str(spec.get('section','GASTOS REGISTRADOS')).replace('TOP 6','TOP 5')
        head_h=_altura_linhas(draw,section,inner,FONTE_MINIMA,2)
        if bars:body_h=len(bars)*120
        else:body_h=44+_altura_linhas(draw,spec.get('detail','Confira o período ou abra os detalhes.'),inner,FONTE_MINIMA,3)
        more=len(all_bars)>len(bars)
        extra_h=_altura_linhas(draw,f'{len(bars)} de {len(all_bars)} itens · lista completa nos detalhes',inner,FONTE_MINIMA,2) if more else 0
        top=y;total=18+head_h+10+body_h+extra_h+14
        draw.rounded_rectangle((MARGEM,top,LARGURA-MARGEM,top+total),radius=16,fill=CARD)
        yy=linhas(draw,section,x,top+18,inner,FONTE_MINIMA,2,MUTED)+10
        maximum=max([abs(float(value)) for _,value in bars]+[1])
        limits=spec.get('bar_limits',[])
        for index,(label,value) in enumerate(bars):
            limit=limits[index] if index<len(limits) else None
            color=RED if value<0 or (limit is not None and value>limit) else BLUE
            number=moeda(value)+((' / '+moeda(limit)) if limit is not None else '')
            # Rótulo e valor em linhas diferentes evitam colisão de nomes longos.
            texto(draw,label,(x,yy),inner,30,INK,True)
            texto(draw,number,(x,yy+42),inner,FONTE_MINIMA,color,True)
            by=yy+86
            draw.rounded_rectangle((x,by,x+inner,by+12),radius=6,fill=TRILHO)
            denominator=max(float(limit),.01) if limit is not None else maximum
            width=max(0,min(inner,round(inner*abs(float(value))/denominator)))
            if width:draw.rounded_rectangle((x,by,x+max(width,12),by+12),radius=6,fill=color)
            yy+=120
        if not bars:
            texto(draw,spec.get('headline','Sem gastos registrados'),(x,yy),inner,30,INK,True)
            yy=linhas(draw,spec.get('detail','Confira o período ou abra os detalhes.'),x,yy+44,inner,FONTE_MINIMA,3,MUTED)
        if more:
            linhas(draw,f'{len(bars)} de {len(all_bars)} itens · lista completa nos detalhes',x,yy,inner,FONTE_MINIMA,2,MUTED)
        y=top+total+8
    y=linhas(draw,spec.get('footer','Valores dos registros. Previsão não é saldo bancário.'),MARGEM+2,y+12,INTERNA-4,FONTE_MINIMA,3,MUTED)
    return _finalizar(image,y+20,'assessor_painel.png')


def _metrica(draw,card,x,y,width,height):
    inner=width-2*16
    draw.rounded_rectangle((x,y,x+width,y+height),radius=16,fill=CARD,outline=LINE)
    yy=linhas(draw,card['label'],x+16,y+12,inner,FONTE_MINIMA,2,MUTED)
    value=str(card['value'])
    texto(draw,value,(x+16,yy),inner,36,RED if _negativo(value) else INK,True)
    if card.get('hint'):texto(draw,card['hint'],(x+16,yy+46),inner,FONTE_MINIMA,MUTED)


def painel_dashboard(spec):
    """Visão ampliada em blocos, com tipografia legível e navegação por assunto."""
    sections=spec.get('dashboard_sections',[]);hero=spec.get('hero');cards=spec.get('cards',[])[:2]
    image,draw=_canvas();y=_cabecalho(draw,spec,'Painel do mês','')
    if hero:y=_hero(draw,spec,hero,y,'neutral')
    for card in cards:y=_card_largo(draw,card,y,40)
    inner=INTERNA-2*PAD;x=MARGEM+PAD
    for section in sections:
        items=section['items'];kind=section['type'];y+=14
        y=linhas(draw,section['title'],MARGEM+2,y,INTERNA-4,FONTE_MINIMA,2,MUTED)+4
        if kind=='metrics':
            col=(INTERNA-12)//2
            for n in range(0,len(items),2):
                par=items[n:n+2]
                hh=max(12+_altura_linhas(draw,c['label'],col-32,FONTE_MINIMA,2)+36+14+(46 if c.get('hint') else 0)+8 for c in par)
                hh=max(hh,150)
                for k,card in enumerate(par):_metrica(draw,card,MARGEM+k*(col+12),y,col,hh)
                y+=hh+12
        elif kind=='bars':
            height=max(1,len(items))*124+20
            draw.rounded_rectangle((MARGEM,y,LARGURA-MARGEM,y+height),radius=16,fill=CARD)
            yy=y+16
            if not items:linhas(draw,section.get('empty','Sem registros.'),x,yy,inner,FONTE_MINIMA,2,MUTED)
            maximum=max([float(v) for _,v in items]+[1])
            for label,value in items:
                texto(draw,label,(x,yy),inner,30,INK,True)
                texto(draw,moeda(value),(x,yy+42),inner,FONTE_MINIMA,BLUE,True)
                draw.rounded_rectangle((x,yy+88,x+inner,yy+100),radius=6,fill=TRILHO)
                bar=max(0,min(inner,round(inner*float(value)/maximum)))
                if bar:draw.rounded_rectangle((x,yy+88,x+max(12,bar),yy+100),radius=6,fill=BLUE)
                yy+=124
            y+=height+8
        elif kind=='trend':
            maximum=max([float(r[k]) for r in items for k in ('income','spending')]+[1])
            y=linhas(draw,'Entradas em verde · Gastos em azul',MARGEM+2,y,INTERNA-4,FONTE_MINIMA,2,MUTED)+4
            for row in items:
                draw.rounded_rectangle((MARGEM,y,LARGURA-MARGEM,y+240),radius=16,fill=CARD)
                texto(draw,row['label']+(' · parcial' if row['partial'] else '')+(' · sem registros' if not row['count'] else ''),(x,y+12),inner,30,INK,True)
                for step,key,color in [(0,'income',TEAL),(1,'spending',BLUE)]:
                    yy=y+62+step*88
                    texto(draw,moeda(row[key]),(x,yy),inner,FONTE_MINIMA,color,True)
                    draw.rounded_rectangle((x,yy+44,x+inner,yy+56),radius=6,fill=TRILHO)
                    width=max(0,min(inner,round(inner*row[key]/maximum)))
                    if width:draw.rounded_rectangle((x,yy+44,x+max(12,width),yy+56),radius=6,fill=color)
                y+=252
        else:
            for item in items:
                fill,color=_TONS.get(item.get('tone'),(CARD,BLUE)) if item.get('tone') in ('warning','danger') else (CARD,BLUE)
                body_h=_altura_linhas(draw,item['body'],inner-12,FONTE_MINIMA,4)
                hh=16+42+body_h+14
                draw.rounded_rectangle((MARGEM,y,LARGURA-MARGEM,y+hh),radius=16,fill=fill)
                draw.rounded_rectangle((MARGEM,y+16,MARGEM+6,y+hh-16),radius=3,fill=color)
                texto(draw,item['title'],(x+6,y+14),inner-6,30,color,True)
                linhas(draw,item['body'],x+6,y+58,inner-12,FONTE_MINIMA,4,INK)
                y+=hh+12
    y=linhas(draw,spec.get('footer','Painel somente leitura.'),MARGEM+2,y+10,INTERNA-4,FONTE_MINIMA,3,MUTED)
    return _finalizar(image,y+20,'assessor_dashboard.png')
