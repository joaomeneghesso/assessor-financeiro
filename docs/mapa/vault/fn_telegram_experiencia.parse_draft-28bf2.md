---
tipo: service
arquivo: telegram_experiencia.py
linha: 2613
---
# telegram_experiencia.parse_draft

Cria rascunho via extrair_campos e avança o registro guiado (confirmação obrigatória).

`fn:telegram_experiencia.parse_draft`

## Vai para
- (chama) [[fn_registro_conversa.extrair_campos-776ac|registro_conversa.extrair_campos]] 
- (chama) [[fn_telegram_experiencia._advance_registration-7c204|telegram_experiencia._advance_registration]] 

## Vem de
- (chama) [[fn_telegram_experiencia.handle_text-7faea|telegram_experiencia.handle_text]] 2974/2984 gastei|recebi|comprei -> rascunho com confirmação
