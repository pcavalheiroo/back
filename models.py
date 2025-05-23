import os
from pymongo import MongoClient
from datetime import datetime

mongodb_url = os.getenv("MONGODB_URL")
client = MongoClient(mongodb_url)
database = client["polichat"]
usuarios = database["usuarios"]
cardapio = database["cardapio"]
pedidos = database["pedidos"]

# --- Funcoes do cardapio ---
def listar_cardapio():
    itens = cardapio.find({"disponivel": True})
    return [{"nome": i["nome"], "preco": i["preco"], "categoria": i["categoria"]} for i in itens]

def buscar_item_cardapio(nome):
    item = cardapio.find_one({"nome": {"$regex": nome, "$options": "i"}})
    if item:
        return {"nome": item["nome"], "preco": item["preco"], "categoria": item["categoria"]}
    return None

# --- Funcoes dos usuarios ---
def autenticar_usuario(email, senha):
    return usuarios.find_one({"email": email, "senha": senha})

pedidos = database["pedidos"]

def salvar_pedido(usuario_id, pedido):
    pedidos.insert_one({
        "usuario_id": usuario_id,
        "pedido": pedido,
        "data": datetime.utcnow()
    })

def obter_pedidos(usuario_id):
    registros = pedidos.find({"usuario_id": usuario_id})
    return [r["pedido"] for r in registros]