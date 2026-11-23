---
name: verificar-antes-de-concluir
description: Checagem obrigatória antes de dizer ao titular que algo está pronto, corrigido, testado ou publicado. Use sempre antes de afirmar sucesso, fechar uma tarefa, sugerir commit ou publicar.
---
# Verificar antes de concluir

Regra: **sem prova vista nesta mesma conversa, não há "pronto".** "Deve funcionar", "parece certo" e "o subagente disse que passou" não são prova.

## Antes de afirmar
1. Identifique qual comando ou observação prova a afirmação (tabela abaixo).
2. Rode-o agora, completo. Não reaproveite resultado antigo, de antes da última edição.
3. Leia a saída inteira: código de saída, total de testes e falhas.
4. Só então afirme, citando a evidência ("gate 1390/1390"). Se falhou, diga que falhou e mostre o trecho.

| Afirmação | Prova exigida | Não basta |
|---|---|---|
| "Testes passam" | Gate oficial com código 0 e N/N | Um teste isolado, ou o gate de antes da edição |
| "Bug corrigido" | Teste de regressão que falhava e agora passa, mais o gate | Só o código alterado "parecer" certo |
| "Não quebrou nada" | Gate completo, mais o teste de arquitetura (linha de base) | Rodar só os testes do módulo |
| "Publicado no servidor" | `publicar.ps1` terminou com OK e o bot respondeu na versão nova | O script ter rodado sem ler o fim da saída |
| "Subagente concluiu" | Conferir o diff ou o arquivo que ele diz ter mudado | O relatório dele |
| "Notas do vault atualizadas" | `python tools/gerar_vault_codigo.py` rodou e mostrou a contagem | Ter editado o código |

Gate oficial na pasta nuvem (ela não tem `.venv` próprio):
```powershell
C:\Projetos\assessor-financeiro\.venv\Scripts\python.exe validacao\validar_versao_oficial.py --projeto C:\Projetos\assessor-financeiro-nuvem --workers 4 --timeout 1500 --saida $env:TEMP\assessor-validacao
```

## Específico do assessor
- Mudou cálculo de dinheiro, fatura, saldo ou competência? Além do gate, mostre um exemplo concreto, antes e depois, em banco temporário.
- Mudou tela, botão ou comando? Confira se o mapa de rotas continua coerente (`docs/mapa/`) e se a gravação ainda passa por prévia e confirmação.
- Nunca use "confirmado", "garantido" ou "100%" sem a prova da tabela. Se algo ficou sem verificar (ex.: só o titular consegue testar no Telegram real), diga isso explicitamente.
- Commit e publicação continuam dependendo de pedido do titular. Verificar não autoriza nenhum dos dois.
