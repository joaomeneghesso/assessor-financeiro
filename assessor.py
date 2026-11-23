import calendar
from datetime import date


def formatar_moeda(valor: float):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def somar_meses(data_base: date, meses: int):
    mes_total = data_base.month - 1 + meses
    ano = data_base.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia_mes)
    return date(ano, mes, dia)


def calcular_impacto_parcelado(transacao: dict):
    parcelas_total = transacao.get("parcelas_total", 1)
    valor_total = transacao["valor"]

    if parcelas_total <= 1:
        return {}

    valor_parcela = round(valor_total / parcelas_total, 2)
    data_base = date.fromisoformat(transacao["data"])
    impacto = {}
    total_lancado = 0

    for parcela_atual in range(1, parcelas_total + 1):
        data_parcela = somar_meses(data_base, parcela_atual - 1)
        mes = data_parcela.strftime("%Y-%m")

        if parcela_atual == parcelas_total:
            valor_atual = round(valor_total - total_lancado, 2)
        else:
            valor_atual = valor_parcela
            total_lancado = round(total_lancado + valor_atual, 2)

        impacto[mes] = impacto.get(mes, 0) + valor_atual

    return impacto


def avaliar_risco_mes(receitas: float, despesas: float, parcelas_futuras: dict, metas_estouradas: list):
    saldo = receitas - despesas
    comprometimento = (despesas / receitas) * 100 if receitas > 0 else 0
    maior_parcela_futura = max(parcelas_futuras.values()) if parcelas_futuras else 0
    comprometimento_futuro = (maior_parcela_futura / receitas) * 100 if receitas > 0 else 0

    pontos = 0
    motivos = []

    if receitas <= 0 and despesas > 0:
        pontos += 3
        motivos.append("há despesas registradas sem receita no mês")

    if saldo < 0:
        pontos += 4
        motivos.append("o saldo do mês está negativo")

    if comprometimento >= 90:
        pontos += 3
        motivos.append("mais de 90% da renda do mês está comprometida")
    elif comprometimento >= 75:
        pontos += 2
        motivos.append("mais de 75% da renda do mês está comprometida")
    elif comprometimento >= 60:
        pontos += 1
        motivos.append("mais de 60% da renda do mês já foi consumida")

    if comprometimento_futuro >= 35:
        pontos += 3
        motivos.append("parcelas futuras têm peso alto sobre a renda")
    elif comprometimento_futuro >= 20:
        pontos += 2
        motivos.append("parcelas futuras já merecem atenção")
    elif comprometimento_futuro >= 10:
        pontos += 1
        motivos.append("há parcelas futuras relevantes")

    if metas_estouradas:
        pontos += len(metas_estouradas)
        motivos.append("existem metas de categoria estouradas")

    if pontos >= 7:
        return "🔴 Crítico", motivos
    if pontos >= 4:
        return "🟠 Pressionado", motivos
    if pontos >= 2:
        return "🟡 Atenção", motivos
    return "🟢 Saudável", motivos


def gerar_simulacao_transacao(transacao: dict):
    parcelas = transacao.get("parcelas_total", 1)
    linhas = [
        "🧪 Simulação de lançamento",
        "",
        f"Tipo: {transacao['tipo']}",
        f"Valor total: {formatar_moeda(transacao['valor'])}",
        f"Categoria: {transacao['categoria']}",
        f"Data inicial: {transacao['data']}",
        f"Forma: {transacao.get('forma_pagamento') or 'não informada'}",
        f"Conta: {transacao.get('conta') or 'não informada'}"
    ]

    if parcelas > 1:
        valor_parcela = transacao["valor"] / parcelas
        impacto = calcular_impacto_parcelado(transacao)
        linhas.extend([f"Parcelas: {parcelas}x de aproximadamente {formatar_moeda(valor_parcela)}", "", "Impacto previsto:"])
        for mes, valor in sorted(impacto.items())[:12]:
            linhas.append(f"- {mes}: {formatar_moeda(valor)}")
        if len(impacto) > 12:
            linhas.append(f"- ... mais {len(impacto) - 12} mês(es)")
    else:
        linhas.append("Parcelas: não parcelado")

    linhas.extend(["", "Nada foi registrado no banco."])
    return "\n".join(linhas)


def gerar_analise_compra(transacao: dict, contexto: dict):
    parcelas = transacao.get("parcelas_total", 1)
    receitas = contexto["receitas"]
    despesas = contexto["despesas"]
    saldo_atual = receitas - despesas

    linhas = [
        "🧠 Análise de compra",
        "",
        f"Compra analisada: {transacao.get('descricao') or 'não informada'}",
        f"Valor total: {formatar_moeda(transacao['valor'])}",
        f"Categoria: {transacao['categoria']}",
        f"Forma: {transacao.get('forma_pagamento') or 'não informada'}"
    ]

    if parcelas > 1:
        valor_parcela = transacao["valor"] / parcelas
        impacto = calcular_impacto_parcelado(transacao)
        linhas.extend([f"Parcelas: {parcelas}x de aproximadamente {formatar_moeda(valor_parcela)}", "", "Impacto futuro desta compra:"])
        for mes, valor in sorted(impacto.items())[:12]:
            atual = contexto["parcelas_futuras"].get(mes, 0)
            novo = atual + valor
            linhas.append(f"- {mes}: parcelas atuais {formatar_moeda(atual)} → com compra {formatar_moeda(novo)}")
    else:
        linhas.extend(["Parcelas: não parcelado", "", f"Impacto imediato no saldo do mês: -{formatar_moeda(transacao['valor'])}"])

    linhas.extend(["", "Situação atual do mês:", f"- Receitas: {formatar_moeda(receitas)}", f"- Despesas: {formatar_moeda(despesas)}", f"- Saldo atual: {formatar_moeda(saldo_atual)}"])

    alertas = []
    if transacao["categoria"] == "Outros":
        alertas.append("a categoria ficou como Outros; seria melhor categorizar antes de registrar")
    if transacao["valor"] >= 1000:
        alertas.append("o valor total é alto")
    if parcelas > 6:
        alertas.append("o parcelamento é longo")
    if receitas > 0 and parcelas > 1:
        parcela = transacao["valor"] / parcelas
        peso = (parcela / receitas) * 100
        if peso >= 10:
            alertas.append(f"a parcela representa {peso:.1f}% da renda mensal registrada")

    linhas.append("")
    if alertas:
        linhas.append("Alertas:")
        for alerta in alertas:
            linhas.append(f"⚠️ {alerta}")
        linhas.append("")

    if parcelas > 1 and transacao["valor"] >= 1000:
        linhas.append("Recomendação: eu só faria essa compra se ela for necessária ou planejada.")
    elif transacao["categoria"] == "Outros":
        linhas.append("Recomendação: categorize melhor antes de registrar.")
    elif receitas > 0 and saldo_atual > 0:
        linhas.append("Recomendação: a compra parece possível, mas acompanhe o impacto nos próximos meses.")
    else:
        linhas.append("Recomendação: falta receita/saldo registrado para avaliar com segurança.")

    linhas.extend(["", "Nada foi registrado no banco."])
    return "\n".join(linhas)


def gerar_diagnostico_financeiro(contexto: dict):
    receitas = contexto["receitas"]
    despesas = contexto["despesas"]
    despesas_registradas = contexto.get("despesas_registradas", 0)
    compromissos_previstos = contexto.get("compromissos_previstos", 0)
    saldo = receitas - despesas
    categorias = contexto["categorias"]
    metas = contexto["metas_status"]
    parcelas_futuras = contexto["parcelas_futuras"]
    metas_estouradas = [m for m in metas if m["status"] == "acima"]
    risco, motivos = avaliar_risco_mes(receitas, despesas, parcelas_futuras, metas_estouradas)

    linhas = [
        f"🧠 Diagnóstico financeiro de {contexto['ano_mes']}",
        "",
        f"Risco do mês: {risco}",
        "",
        "Resumo projetado do mês:",
        f"- Receitas registradas: {formatar_moeda(receitas)}",
        f"- Despesas/compromissos previstos: {formatar_moeda(despesas)}",
        f"- Saldo projetado: {formatar_moeda(saldo)}"
    ]

    if compromissos_previstos or despesas_registradas:
        linhas.extend([
            "",
            "Composição das despesas:",
            f"- Fixos/parcelas previstos: {formatar_moeda(compromissos_previstos)}",
            f"- Despesas avulsas lançadas: {formatar_moeda(despesas_registradas)}"
        ])

    if receitas > 0:
        linhas.append(f"- Consumo da renda: {(despesas / receitas) * 100:.1f}%")
    elif despesas > 0:
        linhas.append("- Consumo da renda: não calculado, porque ainda não há receita registrada no mês")

    linhas.append("")

    if motivos:
        linhas.append("Motivos:")
        for motivo in motivos:
            linhas.append(f"- {motivo}")
        linhas.append("")

    if categorias:
        linhas.append("Maiores categorias previstas:")
        for indice, categoria in enumerate(categorias[:5], start=1):
            linhas.append(f"{indice}. {categoria['categoria']}: {formatar_moeda(categoria['total'])}")
        linhas.append("")

    if metas:
        linhas.append("Metas:")
        for meta in metas:
            marcador = "🔴" if meta["status"] == "acima" else "🟡" if meta["status"] == "atenção" else "🟢"
            linhas.append(f"{marcador} {meta['categoria']}: {formatar_moeda(meta['gasto'])} de {formatar_moeda(meta['limite'])}")
        linhas.append("")

    if parcelas_futuras:
        linhas.append("Próximos meses já previstos:")
        for mes, valor in sorted(parcelas_futuras.items())[:6]:
            linhas.append(f"- {mes}: {formatar_moeda(valor)}")
        linhas.append("")

    linhas.append("Ação recomendada:")
    if receitas <= 0 and despesas > 0:
        linhas.append("- Ainda não há receita registrada para cobrir os compromissos do mês. Registre salário/entradas assim que caírem para recalcular o status.")
    elif risco.startswith("🔴"):
        linhas.append("- Não crie novas parcelas agora. Priorize preservar caixa e revisar os maiores compromissos do mês.")
    elif risco.startswith("🟠"):
        linhas.append("- Evite compras parceladas novas e revise as maiores categorias.")
    elif risco.startswith("🟡"):
        linhas.append("- Mantenha controle semanal e acompanhe metas próximas do limite.")
    else:
        linhas.append("- O mês está saudável com base nas receitas e despesas previstas até agora.")

    return "\n".join(linhas)


def gerar_fechamento_semanal(transacoes_semana: list):
    if not transacoes_semana:
        return "📅 Fechamento semanal\n\nNão encontrei transações nos últimos 7 dias."

    receitas = sum(t["valor"] for t in transacoes_semana if t["tipo"] == "receita")
    despesas = sum(t["valor"] for t in transacoes_semana if t["tipo"] == "despesa")
    saldo = receitas - despesas
    categorias = {}

    for t in transacoes_semana:
        if t["tipo"] != "despesa":
            continue
        categoria = t["categoria"]
        categorias[categoria] = categorias.get(categoria, 0) + t["valor"]

    linhas = ["📅 Fechamento semanal", "", f"Receitas: {formatar_moeda(receitas)}", f"Despesas: {formatar_moeda(despesas)}", f"Saldo da semana: {formatar_moeda(saldo)}", ""]

    if categorias:
        linhas.append("Gastos por categoria:")
        for categoria, valor in sorted(categorias.items(), key=lambda item: item[1], reverse=True):
            linhas.append(f"- {categoria}: {formatar_moeda(valor)}")
        linhas.append("")

    linhas.append("Leitura:")
    if saldo < 0:
        linhas.append("- A semana fechou negativa. Vale revisar os gastos recentes.")
    elif despesas > 0:
        linhas.append("- A semana teve movimentação, mas fechou positiva ou controlada.")
    else:
        linhas.append("- Semana sem despesas registradas.")

    return "\n".join(linhas)


def gerar_fechamento_mensal(contexto: dict):
    receitas = contexto["receitas"]
    despesas = contexto["despesas"]
    despesas_registradas = contexto.get("despesas_registradas", 0)
    compromissos_previstos = contexto.get("compromissos_previstos", 0)
    saldo = receitas - despesas
    categorias = contexto["categorias"]
    metas = contexto["metas_status"]
    parcelas_futuras = contexto["parcelas_futuras"]

    nota = 10

    if receitas <= 0 and despesas > 0:
        nota -= 5

    if saldo < 0:
        nota -= 3

    if receitas > 0:
        consumo = (despesas / receitas) * 100
        if consumo >= 100:
            nota -= 4
        elif consumo >= 90:
            nota -= 3
        elif consumo >= 75:
            nota -= 2
        elif consumo >= 60:
            nota -= 1

    for meta in metas:
        if meta["status"] == "acima":
            nota -= 1

    if parcelas_futuras:
        nota -= 1

    nota = max(0, min(10, nota))

    linhas = [
        f"📌 Fechamento do mês {contexto['ano_mes']}",
        "",
        f"Nota do mês: {nota}/10",
        "",
        "Resultado projetado:",
        f"- Receitas registradas: {formatar_moeda(receitas)}",
        f"- Despesas/compromissos previstos: {formatar_moeda(despesas)}",
        f"- Saldo projetado: {formatar_moeda(saldo)}"
    ]

    if receitas > 0:
        linhas.append(f"- Consumo da renda: {(despesas / receitas) * 100:.1f}%")
    elif despesas > 0:
        linhas.append("- Consumo da renda: não calculado, porque ainda não há receita registrada no mês")

    linhas.extend([
        "",
        "Composição das despesas:",
        f"- Fixos/parcelas previstos: {formatar_moeda(compromissos_previstos)}",
        f"- Despesas avulsas lançadas: {formatar_moeda(despesas_registradas)}",
        ""
    ])

    if categorias:
        linhas.append("Principais gastos previstos:")
        for indice, categoria in enumerate(categorias[:5], start=1):
            linhas.append(f"{indice}. {categoria['categoria']}: {formatar_moeda(categoria['total'])}")
        linhas.append("")

    if metas:
        linhas.append("Metas:")
        for meta in metas:
            if meta["status"] == "acima":
                linhas.append(f"🔴 {meta['categoria']}: acima da meta em {formatar_moeda(abs(meta['restante']))}")
            elif meta["status"] == "atenção":
                linhas.append(f"🟡 {meta['categoria']}: atenção, usou {meta['percentual']:.1f}%")
            else:
                linhas.append(f"🟢 {meta['categoria']}: dentro da meta")
        linhas.append("")

    if parcelas_futuras:
        linhas.append("Próximos meses já previstos:")
        for mes, valor in sorted(parcelas_futuras.items())[:6]:
            linhas.append(f"- {mes}: {formatar_moeda(valor)}")
        linhas.append("")

    linhas.append("Ações recomendadas:")

    if receitas <= 0 and despesas > 0:
        linhas.append("- Registrar as entradas do mês assim que caírem, principalmente salário e benefícios.")
        linhas.append("- Até a receita entrar, trate o mês como pressionado: não crie novas parcelas.")
    elif nota <= 4:
        linhas.append("- Cortar novas compras parceladas.")
        linhas.append("- Revisar as duas maiores categorias de gasto.")
        linhas.append("- Evitar despesas não essenciais até recompor saldo.")
    elif nota <= 7:
        linhas.append("- Acompanhar metas semanalmente.")
        linhas.append("- Evitar novas parcelas longas.")
        linhas.append("- Priorizar manter saldo positivo.")
    else:
        linhas.append("- Manter o padrão atual.")
        linhas.append("- Considerar separar parte do saldo para reserva/investimento.")
        linhas.append("- Continuar registrando gastos para manter previsibilidade.")

    return "\n".join(linhas)
