import bcrypt
from bson import ObjectId
from ..connection import database
from datetime import datetime

def criar_usuario(email: str, senha: str):
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return database.usuarios.insert_one({
        "email": email,
        "senha": senha_hash,
        "criado_em": datetime.utcnow()
    })

def autenticar_usuario(email: str, senha: str):
    usuario = database.usuarios.find_one({"email": email})
    if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario["senha"].encode('utf-8')):
        usuario["_id"] = str(usuario["_id"])
        usuario.pop("senha")
        return usuario
    return None