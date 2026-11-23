---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1659
---
# pause_for_guidance

Suspende rascunho e guarda learning_stage ao abrir ajuda/aula/dashboard/obrigação.

`fn:ux.pause_for_guidance`

## Vai para
- (chama) [[fn_ux._suspend_flow-76c4a|_suspend_flow]] 
- (grava_estado) [[state_Session.learning_stage-1e8f0|Session.learning_stage]] 

## Vem de
- (chama) [[act_detail_obligation-b6e92|detail_obligation]] 
- (chama) [[act_chart-efa97|chart]] 
- (chama) [[fn_ux.open_learning-405a2|open_learning]] 
- (chama) [[act_topic-518da|topic]] 
- (chama) [[act_view-1d8b8|view]] 
