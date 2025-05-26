from datetime import datetime
from ..connection import database

def salvar_mensagem(usuario_id: str, mensagem: str, origem: str):
    return database.mensagens.insert_one({
        "usuario_id": usuario_id,
        "mensagem": mensagem,
        "origem": origem,
        "data": datetime.utcnow()
    })

def obter_historico(usuario_id: str, limite: int = 50):
    return list(database.mensagens.find(
        {"usuario_id": usuario_id},
        sort=[("data", 1)]  # Ordem cronológica
    ).limit(limite))