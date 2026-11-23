---
tipo: module
arquivo: app.py
linha: 
---
# app.py

Entrada do bot Telegram (whitelist, PIN, handlers).

`mod:app.py`

## Vai para
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] executar_core(processar_mensagem) app.py:4969, só se UX2 não devolver tela
- (chama) [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]] app.py:4691
- (chama) [[fn_telegram_midia.receive-25423|telegram_midia.receive]] app.py:4385 receber_midia (handler de voice/audio/photo)
- (chama) [[fn_telegram_alertas.rotina-a3d59|telegram_alertas.rotina]] app.py:4806 / 5243 (job de alertas)
- (chama) [[fn_telegram_alertas.callback-80f31|telegram_alertas.callback]] app.py:4806 callback_submenu -> telegram_alertas.callback
- (chama) [[fn_telegram_recursos.deep_action-f02e9|telegram_recursos.deep_action]] app.py:4357 /start <payload>
- (chama) [[mod_telegram_recursos.py-a9bf3|telegram_recursos.py]] import TopicPending/scope_update/thread_id (32)
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] executar_core(processar_mensagem) app.py:4930 texto livre; 5002/5031/5249 comandos guiados e confirmados
- (chama) [[text_backup_automático-d5735|backup automático]] job de backup app.py:5368/5377
- (chama) [[text_vencimentos_hoje-62d23|vencimentos hoje]] lembrete diário app.py:5401
- (chama) [[text_fechamento_semanal-02528|fechamento semanal]] resumo semanal app.py:5445
- (chama) [[text_fechamento_do_mês-fd23b|fechamento do mês]] resumo mensal app.py:5446
