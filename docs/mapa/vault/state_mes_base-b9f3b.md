---
tipo: state
arquivo: app.py
linha: 2132
---
# mes_base

NAO e estado guardado: derivado a cada resposta (mes no comando > 1o AAAA-MM no texto da resposta > date.today()) e embutido no texto do botao

`state:mes_base`

## Vai para
- (le_estado) [[state_session.month-91610|session.month]] NAO se comunicam: mes_base ignora session.month; session.month so e usado pelo UX 2.0
- (navega) [[text___fallback_hoje-287b7|date.today()]] fallback date.today()

## Vem de
- (le_estado) [[fn_app.montar_teclado_inline_para_resposta-e330f|app.montar_teclado_inline_para_resposta]] obter_mes_base(comando, resposta)
- (le_estado) [[fn_app.montar_teclado_acao_produtiva-85b6e|app.montar_teclado_acao_produtiva]] 
