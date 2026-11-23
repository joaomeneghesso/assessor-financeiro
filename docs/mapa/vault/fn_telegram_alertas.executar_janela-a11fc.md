---
tipo: service
arquivo: telegram_alertas.py
linha: 160
---
# telegram_alertas.executar_janela

Decide alertas devidos (janela de 180 s) e envia mensagem sem valores; só ao dono autorizado.

`fn:telegram_alertas.executar_janela`

## Vai para
- (chama) [[fn_assessor_orientacao.preferencias-719d2|assessor_orientacao.preferencias]] 
- (chama) [[fn_telegram_alertas.elegiveis-53461|telegram_alertas.elegiveis]] 
- (chama) [[fn_telegram_alertas.sonecas-d0a3f|telegram_alertas.sonecas]] 
- (chama) [[fn_telegram_alertas._snapshot_alerta-02723|telegram_alertas._snapshot_alerta]] 
- (chama) [[fn_telegram_alertas.reservar-1a6f7|telegram_alertas.reservar]] 
- (chama) [[fn_telegram_alertas.montar_aviso-23d00|telegram_alertas.montar_aviso]] 
- (chama) [[fn_telegram_alertas.controles-5e527|telegram_alertas.controles]] 
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] enviado | entrega_incerta

## Vem de
- (chama) [[mod_telegram_alertas.py-deb44|telegram_alertas.py]] 
- (chama) [[fn_telegram_alertas.rotina-a3d59|telegram_alertas.rotina]] 
