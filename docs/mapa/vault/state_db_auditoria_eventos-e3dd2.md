---
tipo: state
arquivo: database.py
linha: 1750
---
# db:auditoria_eventos

Tabela SQLite que guarda estado funcional (vínculos, âncoras de saldo, alertas, sonecas, preferências, registros Telegram).

`state:db:auditoria_eventos`

## Vem de
- (grava_estado) [[fn_services.confirmar_movimento_fatura_pendente-95ee9|services.confirmar_movimento_fatura_pendente]] grava fatura_movimentos + auditoria
- (grava_estado) [[fn_services.definir_saldo_inicial_formatado-cbce1|services.definir_saldo_inicial_formatado]] saldo inicial / herdado
- (grava_estado) [[fn_compromissos.apagar_compromisso_formatado-7fb15|compromissos.apagar_compromisso_formatado]] compromissos + auditoria
- (grava_estado) [[fn_assessor_orientacao.salvar_preferencias-c89c1|assessor_orientacao.salvar_preferencias]] entidade experiencia_preferencia
- (le_estado) [[fn_assessor_orientacao.preferencias-719d2|assessor_orientacao.preferencias]] 
- (grava_estado) [[fn_assessor_orientacao.configurar_saldo-1ec8e|assessor_orientacao.configurar_saldo]] saldo_mensal configurado_rc3
- (grava_estado) [[fn_telegram_registros.confirmar_registro-9a9b2|telegram_registros.confirmar_registro]] telegram_registro/confirmado
- (grava_estado) [[fn_telegram_registros.desfazer_registro-d77a5|telegram_registros.desfazer_registro]] telegram_registro/desfeito
- (grava_estado) [[fn_telegram_registros.confirmar_pagamento_fatura-ded85|telegram_registros.confirmar_pagamento_fatura]] telegram_fatura/confirmado + fatura_movimento
- (grava_estado) [[fn_telegram_alertas.reservar-1a6f7|telegram_alertas.reservar]] experiencia_alerta/reservado
- (grava_estado) [[fn_telegram_alertas.executar_janela-a11fc|telegram_alertas.executar_janela]] enviado | entrega_incerta
- (le_estado) [[fn_telegram_alertas.sonecas-d0a3f|telegram_alertas.sonecas]] 
- (grava_estado) [[fn_telegram_alertas.adiar-a92a0|telegram_alertas.adiar]] experiencia_soneca
