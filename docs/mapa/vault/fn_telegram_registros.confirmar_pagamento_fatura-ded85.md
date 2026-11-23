---
tipo: service
arquivo: telegram_registros.py
linha: 220
---
# telegram_registros.confirmar_pagamento_fatura

Grava pagamento de fatura (total/parcial) revalidando saldo_esperado; idempotente.

`fn:telegram_registros.confirmar_pagamento_fatura`

## Vai para
- (chama) [[fn_services.calcular_resumo_fatura-b4797|services.calcular_resumo_fatura]] 
- (chama) [[fn_database.inserir_fatura_movimento_conn-457bd|database.inserir_fatura_movimento_conn]] 
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] telegram_fatura/confirmado + fatura_movimento

## Vem de
- (chama) [[mod_telegram_registros.py-6b0ea|telegram_registros.py]] 
- (chama) [[act_invoice_commit-7ad93|invoice_commit]] 
