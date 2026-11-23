---
tipo: text_trigger
arquivo: app.py
linha: 
---
# menu

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:menu`

## Vai para
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] teclado inline da Central (comando in __help__/menu/central)
- (navega) [[btn_Lançar-e6c87|➕ Lançar]] teclado inline
- (navega) [[btn_Hoje-ab454|📆 Hoje]] teclado inline
- (navega) [[btn_Meu_mês_meu_mês-d5345|📊 Meu mês]] teclado inline
- (navega) [[btn_Dashboard_dashboard-e092a|📈 Dashboard]] teclado inline
- (navega) [[btn_Categorias_dashboard_categorias-a763c|🏷 Categorias]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (navega) [[btn_Revisar-ffeba|🔎 Revisar]] teclado inline
- (navega) [[btn_Compromissos_compromissos-aa678|💳 Compromissos]] teclado inline
- (navega) [[btn_Checklist_checklist-9c872|✅ Checklist]] teclado inline
- (navega) [[btn_Saldo-a48c4|🏦 Saldo]] teclado inline
- (navega) [[btn_Últimos-2594c|📌 Últimos]] teclado inline
- (navega) [[btn_Exportar_exportar_csv-427f8|📤 Exportar]] teclado inline
- (navega) [[btn_Ajustes-8142c|⚙️ Ajustes]] teclado inline
- (navega) [[btn_Ajuda-7a335|❓ Ajuda]] teclado inline
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] RESETA p/ mês corrente (l.2935)
- (chama) [[act_view-1d8b8|view]] home
- (volta) [[bug_menu_mes_novembro-e8fd4|BUG mês vaza para o Menu]] único caminho que corrige (reset l.2935)

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[fn_app.obter_resposta_comando_especial-bcaa6|app.obter_resposta_comando_especial]] 
- (navega) [[btn_Central-84b26|🏠 Central]] envia 'menu'
- (chama) [[btn_Histórico_teclado-15934|Teclado fixo: 🏠 Início ➕ Registrar 🧾 A pagar 🔎 Histórico 📊 Análises ⚙️ Mais]] "🏠 Início"
