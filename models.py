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

def extrair_nome_item(mensagem):
    palavras_chave = ["explica", "o que tem", "quero", "sobre"]
    for chave in palavras_chave:
        if chave in mensagem.lower():
            return mensagem.lower().split(chave)[-1].strip()
    return mensagem.strip()                                         

def buscar_item_cardapio(nome):
    item = cardapio.find_one({"nome": {"$regex": nome, "$options": "i"}})
    if item:
        return {"nome": item["nome"], "preco": item["preco"], "categoria": item["categoria"]}
    return None

# --- Funcoes dos usuarios ---
def autenticar_usuario(email, senha):
    return usuarios.find_one({"email": email, "senha": senha})                          

def salvar_pedido(usuario_id, nome_item):
    item = buscar_item_cardapio(nome_item)
    if not item:
        return False
    pedidos.insert_one({
        "usuario_id": usuario_id,
        "pedido": item["nome"],
        "preco": item["preco"],
        "categoria": item["categoria"],
        "data": datetime.utcnow()
    })
    return True


def obter_pedidos(usuario_id):
    registros = pedidos.find({"usuario_id": usuario_id})
    return [f"{r['pedido']}" for r in registros]

def obter_historico_mensagens(usuario_id, limite=10):
    mensagens = database["mensagens"].find({"usuario_id": usuario_id}).sort("data", -1).limit(limite)
    return list(mensagens)[::-1]  # Invertemos para manter ordem cronológica
