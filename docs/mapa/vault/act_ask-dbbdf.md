---
tipo: action
arquivo: telegram_experiencia.py
linha: 2892
---
# ask

Escrever pergunta (stage=ask).

`act:ask`

## Vai para
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] ask
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] zera
- (navega) [[screen_question-e9cf8|question]] 
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (le_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_assistant-c05b6|assistant]] Escrever uma pergunta
- (navega) [[screen_local_ai-599c7|local_ai]] Testar uma pergunta
- (navega) [[fn_ux.question_result-77118|question_result]] Perguntar de novo
