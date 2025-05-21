from db import cardapio_collection, usuarios_collection, visitantes_collection

# --- Funcoes do cardapio ---
def listar_cardapio():
    itens = cardapio_collection.find({"disponivel": True})
    return [{"nome": i["nome"], "preco": i["preco"], "categoria": i["categoria"]} for i in itens]

def buscar_item_cardapio(nome):
    item = cardapio_collection.find_one({"nome": {"$regex": nome, "$options": "i"}})
    if item:
        return {"nome": item["nome"], "preco": item["preco"], "categoria": item["categoria"]}
    return None

# --- Funcoes dos usuarios ---
def autenticar_usuario(email, senha):
    return usuarios_collection.find_one({"email": email, "senha": senha})

def autenticar_visitante(codigo):
    return visitantes_collection.find_one({"codigo_acesso": codigo})

# --- Pedido simples em memoria por exemplo ---
pedidos = {}  # {usuario_id: [pedido1, pedido2]}

def salvar_pedido(usuario_id, pedido):
    if usuario_id in pedidos:
        pedidos[usuario_id].append(pedido)
    else:
        pedidos[usuario_id] = [pedido]

def obter_pedidos(usuario_id):
    return pedidos.get(usuario_id, [])
