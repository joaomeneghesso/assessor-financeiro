"""Identidade de versões pela auditoria existente; nenhuma inferência por nome."""
import json
from datetime import date


def periodos_sobrepostos(a, b):
    def limites(row):
        inicio = date.fromisoformat(row['data_inicio'])
        fim = date.fromisoformat(row['data_fim']) if row.get('data_fim') else date.max
        if fim < inicio:
            raise ValueError('O término do fixo não pode ser anterior ao início.')
        return inicio, fim
    ai, af = limites(dict(a))
    bi, bf = limites(dict(b))
    return ai <= bf and bi <= af


def ids_da_serie(conn, ident):
    pais = {}
    for child, payload in conn.execute("SELECT entidade_id,dados_antes FROM auditoria_eventos "
                                      "WHERE entidade='compromissos' AND operacao='nova_condicao' ORDER BY id"):
        try:
            parent = json.loads(payload)['origem_id']
            pais[int(child)] = int(parent)
        except (ValueError, TypeError, KeyError):
            raise ValueError('A auditoria de versões precisa de conferência antes de editar a vigência.')
    def raiz(item):
        seen = set()
        while item in pais:
            if item in seen:
                raise ValueError('Há um ciclo na auditoria de versões. Nenhuma alteração foi feita.')
            seen.add(item)
            item = pais[item]
        return item
    target = raiz(int(ident))
    return {item for item in {int(ident), *pais.keys(), *pais.values()} if raiz(item)==target}


def garantir_sem_sobreposicao(conn, ident, candidate):
    candidate = dict(candidate)
    if candidate.get('tipo') != 'fixo' or not candidate.get('ativo'):
        return
    ids = ids_da_serie(conn, ident) - {int(ident)}
    if not ids:
        return
    names = [row[1] for row in conn.execute('PRAGMA table_info(compromissos)')]
    for values in conn.execute('SELECT * FROM compromissos WHERE tipo=\'fixo\' AND ativo=1'):
        other = dict(zip(names, values))
        if other['id'] in ids and periodos_sobrepostos(candidate, other):
            raise ValueError(f'A alteração sobrepõe a versão #C{other["id"]} deste fixo. Edite a condição vigente ou escolha datas sem sobreposição. Nada foi alterado.')
