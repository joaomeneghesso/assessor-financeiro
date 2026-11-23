---
tipo: state
arquivo: database.py
linha: 735
---
# db:transacoes

Tabela de transações (lançamentos).

`state:db:transacoes`

## Vem de
- (grava_estado) [[fn_services.confirmar_importacao_csv-7c626|services.confirmar_importacao_csv]] importa transações
- (grava_estado) [[fn_services.confirmar_lancamento_pendente-2b96c|services.confirmar_lancamento_pendente]] 
- (grava_estado) [[fn_services.registrar_transacao_unica-f096c|services.registrar_transacao_unica]] database.inserir_transacao (sem confirmação extra)
- (grava_estado) [[fn_services.registrar_compra_parcelada-00023|services.registrar_compra_parcelada]] 
- (grava_estado) [[fn_services.apagar_por_id-de484|services.apagar_por_id]] só executa com _EXCLUSAO_CONFIRMADA
- (grava_estado) [[fn_services.apagar_por_faixa-66240|services.apagar_por_faixa]] 
- (grava_estado) [[fn_services.apagar_ultimo-34edd|services.apagar_ultimo]] 
- (grava_estado) [[fn_telegram_registros.confirmar_registro-9a9b2|telegram_registros.confirmar_registro]] 
- (grava_estado) [[fn_telegram_registros.desfazer_registro-d77a5|telegram_registros.desfazer_registro]] DELETE das linhas
