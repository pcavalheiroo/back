from ..connection import database

def listar_itens():
    return list(database.cardapio.find({"disponivel": True}))

def verificar_item(nome: str):
    return database.cardapio.find_one({
        "nome": {"$regex": f"^{nome}$", "$options": "i"},
        "disponivel": True
    })