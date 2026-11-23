---
tipo: text_trigger
arquivo: app.py
linha: 8922
---
# entradas

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:entradas`

## Vai para
- (navega) [[btn_mês_anterior_entradas-f9d6c|◀️ mês anterior (entradas)]] teclado inline
- (navega) [[btn_mês_seguinte_entradas-48cd8|mês seguinte ▶️ (entradas)]] teclado inline
- (navega) [[btn_Detalhar_mês-7cb84|📋 Detalhar mês]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (navega) [[btn_Ajuda_entradas-bd1c4|⚙️ Ajuda entradas]] teclado inline
- (chama) [[fn_compromissos.listar_entradas_mes_formatado-d2180|compromissos.listar_entradas_mes_formatado]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Entradas-52446|💰 Entradas]] envia 'entradas'
- (alias_de) [[alias_ver_entrada_s_receita_s-62b1e|ver entrada(s)/receita(s) -> entradas]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8922
