---
tipo: grupo
tags: [grupo, nucleo-financeiro]
---
# Núcleo financeiro

As regras que mexem em dinheiro: compromissos e fixos, conciliação, faturas e competência, saldos e categorias.

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[compromissos.py]] | 2175 | 8 |  |
| [[conciliacao.py]] | 372 | 8 | Vínculos explícitos entre uma ocorrência de compromisso e um lançamento. |
| [[ajustar_fatura_itau.py]] | 241 | 0 |  |
| [[fixos_edicao.py]] | 165 | 2 | Edição de fixos: correção do cadastro ou nova condição mensal, com auditoria. |
| [[faturas_competencia.py]] | 163 | 7 | V39: calendario de faturas separado da data real da compra. |
| [[categorias.py]] | 148 | 10 | Taxonomia e categorização canônica compartilhada pelo assessor. |
| [[categorias_pessoais.py]] | 128 | 5 | Regras pessoais e explícitas de categorização. |
| [[fixos_variaveis.py]] | 117 | 3 | Fixos de valor variável (ex.: conta de luz): regras puras, sem banco. |
| [[fatura_conferencia.py]] | 114 | 1 | Conferência explícita com o banco; diferença de composição não é estorno. |
| [[pagamentos_canonicos.py]] | 101 | 1 | Leitura canônica, pura e não inferencial dos dados de pagamento. |
| [[fixos_variaveis_acoes.py]] | 71 | 1 | Ativar/desligar "valor variável" num fixo e sugerir o histórico (camada de ações). |
| [[saldos_edicao.py]] | 69 | 1 | Confirmação atômica do saldo atual de uma conta e da base geral do mês. |
| [[contas_inativas.py]] | 66 | 1 | Contas desativadas: saem das listas de escolha, mas o histórico, os relatórios e o backup seguem intactos. |
| [[money.py]] | 57 | 14 |  |
| [[fixos_vigencia.py]] | 50 | 3 | Identidade de versões pela auditoria existente; nenhuma inferência por nome. |
| [[saldo_resumo.py]] | 40 | 5 | Composição explicável do saldo, sem banco e sem novas regras financeiras. |
| [[reservas_faturas.py]] | 37 | 1 | Ponte de caixa: crédito em um cartão não é dinheiro em outro banco. |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
