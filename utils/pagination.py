from flask import request
def paginate_query(query, schema_item_to_dict):
    try:
        pagina = int(request.args.get('pagina', 1))
        tamanho = int(request.args.get('tamanho', 10))
    except ValueError:
        pagina = 1
        tamanho = 10
    if pagina < 1: pagina = 1
    if tamanho < 1: tamanho = 10
    total = query.count()
    items = query.offset((pagina-1)*tamanho).limit(tamanho).all()
    dados = [schema_item_to_dict(i) for i in items]
    paginas = (total + tamanho - 1) // tamanho
    return {
        'dados': dados,
        'pagina': pagina,
        'tamanho': tamanho,
        'total': total,
        'paginas': paginas
    }
