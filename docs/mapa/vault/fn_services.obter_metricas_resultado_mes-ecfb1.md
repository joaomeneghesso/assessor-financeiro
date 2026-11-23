---
tipo: service
arquivo: services.py
linha: 4693
---
# services.obter_metricas_resultado_mes

Função de negócio (destino de roteamento).

`fn:services.obter_metricas_resultado_mes`

## Vai para
- (le_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] _consulta_cache(chave) usa o dict do contexto se existir
- (grava_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] memoriza resultado no cache do contexto atual
- (chama) [[fn_services.calcular_saldo_mensal-ab5b8|services.calcular_saldo_mensal]] via _calcular_metricas_resultado_mes

## Vem de
- (chama) [[fn_services.gerar_meu_mes_curto_ux-1614a|services.gerar_meu_mes_curto_ux]] 
- (chama) [[fn_services.gerar_meu_mes_ux-f2a95|services.gerar_meu_mes_ux]] 
- (chama) [[fn_assessor_orientacao.coletar-df8f0|assessor_orientacao.coletar]] 81
- (chama) [[fn_telegram_alertas._snapshot_alerta-02723|telegram_alertas._snapshot_alerta]] via coletar
- (chama) [[fn_telegram_recursos.dispatch-a2ef9|telegram_recursos.dispatch]] 109
- (chama) [[text_herança_aaaa-mm-aa686|herança [aaaa-mm]]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] auxiliar de normalização/validação
- (chama) [[screen_home-111fe|home]] 
- (chama) [[screen_balance-64c54|balance]] 
- (chama) [[screen_balance_details-02072|balance_details]] 
- (chama) [[screen_review_details-b6002|review_details]] 
- (chama) [[screen_reconciliations-256e3|reconciliations]] 
- (chama) [[screen_balance_account-fac81|balance_account]] 
- (chama) [[fn_ux.preview-35809|preview]] 
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
- (chama) [[act_reconcile_baseline_commit-6bad7|reconcile_baseline_commit]] 
- (chama) [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]] 
