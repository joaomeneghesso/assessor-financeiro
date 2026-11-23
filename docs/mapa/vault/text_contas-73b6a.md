---
tipo: text_trigger
arquivo: app.py
linha: 3052
---
# contas

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:contas`

## Vai para
- (navega) [[btn_mês_anterior_contas-963df|◀️ mês anterior (contas)]] teclado inline
- (navega) [[btn_mês_seguinte_contas-09626|mês seguinte ▶️ (contas)]] teclado inline
- (navega) [[btn_Detalhar_mês-7cb84|📋 Detalhar mês]] teclado inline
- (navega) [[btn_Categorias_categorias_mes-a79dd|🏷 Categorias]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (chama) [[fn_compromissos.resumo_contas_mes-7e95c|compromissos.resumo_contas_mes]] 

## Vem de
- (navega) [[btn_Contas_contas-3e876|💰 Contas]] envia 'contas'
- (alias_de) [[alias_ver_conta_s-c11a9|ver conta(s) -> contas]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9021
