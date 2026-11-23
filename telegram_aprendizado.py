"""Conteúdo didático de leitura: sem banco, pagamentos ou progresso persistente."""
import re
import unicodedata


# conceito, exemplo, conferência, ferramenta; exemplos nunca são executados.
LESSONS = {
 'primeiros': ('Começar com uma base confiável',
  'Primeiro informe o dinheiro disponível agora em cada banco. Depois cadastre o que ainda espera pagar ou receber e registre o que realmente acontecer.',
  'Se o banco mostra R$ 800 hoje, informe 800 em Ajustar saldos atuais. Esse ajuste não é receita e não registra um pagamento.',
  'Abra Início: o saldo deve representar o dinheiro disponível; a previsão considera também as pendências. Se a base for estimada, confira os saldos.', ('view','setup')),
 'lancamentos': ('Registrar entradas e despesas',
  'Use Registrar e escolha Despesa ou Entrada recebida. Informe valor, descrição, forma, banco e data. Confira a prévia antes de salvar.',
  'Um almoço de R$ 35 pago por Pix no Itaú: despesa, 35, almoço, Pix, Itaú e a data real. Uma entrada prevista só é recebida quando o dinheiro entra.',
  'No Histórico, confira valor, conta e data. Se o pagamento já está registrado, use o lançamento existente em vez de criar outro.', ('view','register')),
 'faturas': ('Separar compra e pagamento da fatura',
  'A compra no crédito entra na fatura escolhida e mantém sua data real. Ela não reduz o dinheiro do banco nesse momento. O pagamento da fatura é outra etapa.',
  'Com corte no dia 25: compra em 25/09 escolhendo outubro → data da compra 25/09 e fatura outubro. O dia de corte pode ser configurado por cartão; confira as opções exibidas.',
  'Abra A pagar e confira a fatura correspondente. Pague pelo detalhe da fatura quando a saída ocorrer. Parcelas futuras continuam existindo.', ('view','pay')),
 'caixa': ('Entender saldo e previsão',
  'Saldo agora é o dinheiro disponível. A receber são entradas ainda esperadas. Reservas líquidas representam o que ainda pesa na previsão. Sobra prevista não é o saldo do banco.',
  'R$ 1.000 disponíveis + R$ 200 a receber − R$ 300 reservados = R$ 900 previstos para o fim do mês.',
  'Em Ver cálculo, confira cada componente. Ajustar saldo usa o valor de agora, sem descontar outra vez pagamentos já incluídos no saldo informado.', ('view','balance')),
 'transferencias': ('Mover dinheiro entre suas contas',
  'Transferência própria reduz uma conta e aumenta outra. Ela preserva o total do dinheiro e não vira receita ou despesa.',
  'Transferir R$ 100 do Itaú para o Mercado Pago: −100 na origem e +100 no destino. Pix é a forma de pagamento; o nome do banco identifica a conta.',
  'Confira as duas contas e o total disponível. Use o guia de transferências para registrar origem e destino corretamente.', ('topic','transferencias')),
 'previsoes': ('Cadastrar fixos e entradas previstas',
  'Fixos são compromissos recorrentes com vigência. Entradas previstas ainda não são dinheiro recebido. Fixos no crédito compõem a fatura; Pix e débito têm pagamento próprio.',
  'Um plano de R$ 50 muda para R$ 60 em outubro: A partir de um mês preserva a condição anterior e cria a versão seguinte. Corrigir cadastro pode mudar resumos anteriores.',
  'Confira início, término, forma e banco. O relatório fixos exibe os ativos e vigentes; gerenciar cadastros também permite consultar o histórico.', ('fixed_list',0)),
 'meu mes': ('Ler Início, dashboard e análises',
  'Início e dashboard mostram saldo, reserva e sobra prevista. Análises mostram os movimentos registrados; despesas no crédito seguem a competência da fatura.',
  'R$ 900 de sobra prevista não significam R$ 900 ganhos no mês. O valor depende do dinheiro disponível, das entradas previstas e das reservas.',
  'Confira o mês do painel. Meses futuros são projeções. Use Entender valores para ver o cálculo e Categorias para investigar gastos.', ('chart','home')),
 'compromissos': ('Descobrir quanto falta pagar',
  'A pagar reúne obrigações abertas da competência e atrasos incluídos. A reserva do saldo é uma composição da previsão; os dois indicadores não devem ser somados.',
  'Uma fatura quitada não deve receber outro pagamento. Se a saída já está no Histórico, confira o lançamento e o vínculo correspondente.',
  'Abra a conta na lista e confira valor, vencimento e situação antes de registrar uma baixa.', ('view','pay')),
 'checklist': ('Organizar vencimentos e pagamentos',
  'Use A pagar para obrigações abertas e Agenda para os próximos vencimentos. Revisar baixas mostra marcações antigas cujo vínculo ainda precisa ser conferido.',
  'Uma internet vencida já paga pode precisar de vínculo com o lançamento existente, em vez de um novo pagamento.',
  'Confira data, conta e histórico no detalhe. Um alerta ou uma marcação não comprovam uma saída bancária.', ('view','agenda')),
 'conciliacao': ('Ligar previsão ao que aconteceu',
  'Conciliação relaciona um compromisso ao movimento real. Isso evita contar previsão e realização duas vezes.',
  'A previsão de internet é R$ 80 e o pagamento já está no Histórico: abra esse lançamento e relacione à previsão correta.',
  'Confira banco, valor e competência. Movimentos vinculados podem exigir desvinculação antes de uma correção financeira.', ('view','reconciliations')),
 'planejamento': ('Planejar antes de gastar',
  'Limites acompanham categorias. Meu plano mostra prioridades. Simular estima o impacto de uma compra sem gravar uma despesa.',
  'Simule uma compra e compare à vista com parcelas. Analise a primeira fatura e os compromissos dos meses seguintes.',
  'Uma simulação não aparece como compra realizada. Só confirme um registro real quando o dinheiro tiver sido movimentado ou a compra tiver ocorrido.', ('view','planning_tools')),
 'auditoria': ('Investigar antes de corrigir',
  'Quando um número surpreender, descubra sua origem em Histórico, Ver cálculo e detalhes da obrigação. Depois escolha a correção apropriada.',
  'Uma conta negativa pode decorrer de uma saída registrada em outro banco. Confira a conta do pagamento antes de ajustar o saldo.',
  'Correção altera um dado; novo registro cria outro movimento. Use a referência certa e confira a prévia da operação.', ('view','review_tools')),
 'dados': ('Guardar e proteger seus dados',
  'Backup serve para recuperação. Exportar CSV serve para consulta e não substitui o backup. Importação precisa de conferência antes de confirmar.',
  'Antes de uma manutenção, guarde uma cópia de recuperação. Ao terminar, use Bloquear se precisar restringir o acesso.',
  'Ocultar valores protege as novas telas, mas não apaga mensagens antigas do Telegram. Confira o que está visível na conversa.', ('view','data_tools')),
 'caju': ('Acompanhar Caju e benefícios',
  'Caju é uma conta própria. Registre o benefício quando ele entrar e informe Caju como conta nos gastos que saem desse saldo.',
  'Benefício recebido de R$ 500 e gasto de R$ 30: o saldo calculado da conta cai para R$ 470, desde que a base e os registros estejam completos.',
  'Compare Contas e saldos com o aplicativo do benefício. Use a forma que representa corretamente a saída.', ('cash_accounts',)),
 'rotina': ('Manter tudo em dia',
  'Começo do dia: confira a Agenda. Durante o dia: registre o que aconteceu. Ao pagar ou receber: use o movimento existente ou confirme um novo registro real.',
  'À noite, confira Início, saldos por conta e Histórico. Na virada do mês, confira a competência, as faturas e a base de saldo.',
  'No fim do mês, use Fechamento. Investigue divergências antes de corrigir e mantenha uma cópia de recuperação.', ('view','closing')),
}
ORDER=tuple(LESSONS)
ALIASES={str(i):key for i,key in enumerate(ORDER,1)}
ALIASES.update({'16':'tudo','primeiros passos':'primeiros','inicio':'primeiros','comecar':'primeiros',
 'lancamento':'lancamentos','gastos':'lancamentos','receitas':'lancamentos','fatura':'faturas','cartao':'faturas','credito':'faturas','fechamento cartao':'faturas',
 'saldo':'caixa','saldos':'caixa','transferencia':'transferencias','fixos':'previsoes','entradas previstas':'previsoes',
 'analises':'meu mes','quanto pagar':'compromissos','quanto vou pagar':'compromissos','vencimentos':'checklist','alertas':'checklist',
 'conciliar':'conciliacao','limites':'planejamento','planejar':'planejamento','simular':'planejamento','corrigir':'auditoria','correcao':'auditoria','auditar':'auditoria',
 'backup':'dados','seguranca':'dados','exportar':'dados','importar':'dados','vr':'caju','caju/vr':'caju','rotina diaria':'rotina','dia a dia':'rotina',
 'completo':'tudo','aula completa':'tudo'})


def normalize(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD',str(text).casefold()) if not unicodedata.combining(c)).split())


def route(text):
    match=re.fullmatch(r'/?(?:aprender|aula|treinamento|manual|tutorial|guia)(?:\s+(.+))?',normalize(text))
    if not match:return None
    topic=match[1] or ''
    return ALIASES.get(topic,topic)
