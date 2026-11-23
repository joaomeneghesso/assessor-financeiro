---
tipo: service
arquivo: services.py
linha: 11440
---
# services.calcular_caixa_por_conta_mes

Função de negócio (destino de roteamento).

`fn:services.calcular_caixa_por_conta_mes`

## Vai para
- (le_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] _consulta_cache(chave) usa o dict do contexto se existir
- (grava_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] memoriza resultado no cache do contexto atual
- (chama) [[fn_services._avaliar_heranca-4ea4d|services._avaliar_heranca]] 

## Vem de
- (chama) [[fn_services.gerar_caixa_por_conta_mes-45535|services.gerar_caixa_por_conta_mes]] 
- (chama) [[screen_cash_accounts-cc984|cash_accounts]] 
- (chama) [[screen_cash_account_detail-b41d6|cash_account_detail]] 
- (chama) [[screen_balance_account-fac81|balance_account]] 
- (chama) [[fn_ux._cash_accounts_screen-0bdea|_cash_accounts_screen]] 
- (chama) [[fn_ux._cash_account_detail_screen-2f392|_cash_account_detail_screen]] 
- (chama) [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]] 
- (chama) [[fn_ux._cash_setup_start-b8255|_cash_setup_start]] 
