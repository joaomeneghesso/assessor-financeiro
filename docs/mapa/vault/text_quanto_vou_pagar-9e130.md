---
tipo: text_trigger
arquivo: app.py
linha: 2934
---
# quanto vou pagar

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:quanto vou pagar`

## Vai para
- (navega) [[btn_Detalhar_mês-7cb84|📋 Detalhar mês]] teclado inline
- (navega) [[btn_Ver_contas-1a7ef|🏦 Ver contas]] teclado inline
- (navega) [[btn_Meu_mês_meu_mês_mes-9ae8b|📊 Meu mês]] teclado inline
- (navega) [[btn_Compromissos_compromissos_mes-abf1c|💳 Compromissos]] teclado inline
- (chama) [[fn_compromissos.resumo_pagamento_mes_consolidado-9efcf|compromissos.resumo_pagamento_mes_consolidado]] 
- (navega) [[text_detalhar_quanto_vou_pagar_no_banco_em_aaaa-mm-c0cb1|detalhar quanto vou pagar no <banco> [em aaaa-mm]]] mesma família
- (navega) [[text_quanto_vou_pagar_ux2_aaaa-mm-714dc|quanto vou pagar [aaaa-mm] (UX2)]] no Telegram UX2 o mesmo texto é tratado antes (dispatch_text); services só roda se UX2 devolver None
- (chama) [[fn_services.normalizar_ano_mes_flexivel-68b03|services.normalizar_ano_mes_flexivel]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8972
