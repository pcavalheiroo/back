from chat import chat
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import os
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime

# Carregar variáveis de ambiente do .env
load_dotenv()

# Inicializar app
app = Flask(__name__)
CORS(app)

# Conectar ao MongoDB
mongodb_url = os.getenv("MONGODB_URL")
client = MongoClient(mongodb_url)
database = client["polichat"]
usuarios = database["usuarios"]

# Função para remover senha do JSON
def usuario_to_json(usuario):
    usuario["_id"] = str(usuario["_id"])
    usuario.pop("senha", None)
    return usuario

# Rota de criação de usuário
@app.route("/usuarios/cadastro", methods=["POST"])
def cadastrar_usuario():
    dados = request.get_json()
    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return jsonify({"erro": "Email e senha obrigatórios"}), 400

    # Verifica se o usuário já existe
    if usuarios.find_one({"email": email}):
        return jsonify({"erro": "Usuário já existe"}), 409

    # Criptografa a senha e converte para string
    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    usuarios.insert_one({
        "email": email,
        "senha": senha_hash
    })

    return jsonify({"mensagem": "Usuário cadastrado com sucesso"}), 201

# Rota de login
@app.route("/usuarios/login", methods=["POST"])
def login():
    dados = request.get_json()
    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return jsonify({"erro": "Email e senha obrigatórios"}), 400

    usuario = usuarios.find_one({"email": email})
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    senha_hash = usuario.get("senha")

    # Caso a senha esteja armazenada como string, converte para bytes
    if isinstance(senha_hash, str):
        senha_hash = senha_hash.encode("utf-8")

    if bcrypt.checkpw(senha.encode("utf-8"), senha_hash):
        return jsonify({"mensagem": "Login bem-sucedido"}), 200
    else:
        return jsonify({"erro": "Senha incorreta"}), 401

# Listar todos os usuários
@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    todos = list(usuarios.find())
    return jsonify([usuario_to_json(u) for u in todos]), 200

# Buscar usuário por ID
@app.route("/usuarios/<id>", methods=["GET"])
def buscar_usuario(id):
    try:
        usuario = usuarios.find_one({"_id": ObjectId(id)})
        if usuario:
            return jsonify(usuario_to_json(usuario)), 200
        return jsonify({"erro": "Usuário não encontrado"}), 404
    except:
        return jsonify({"erro": "ID inválido"}), 400

# Atualizar tipo do usuário
@app.route("/usuarios/<id>", methods=["PUT"])
def atualizar_usuario(id):
    dados = request.get_json()
    tipo = dados.get("tipo")

    if not tipo:
        return jsonify({"erro": "Campo 'tipo' obrigatório"}), 400

    resultado = usuarios.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"tipo": tipo}}
    )

    if resultado.matched_count == 0:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    usuario = usuarios.find_one({"_id": ObjectId(id)})
    return jsonify(usuario_to_json(usuario)), 200

# Deletar usuário
@app.route("/usuarios/<id>", methods=["DELETE"])
def deletar_usuario(id):
    resultado = usuarios.delete_one({"_id": ObjectId(id)})
    if resultado.deleted_count == 0:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify({"mensagem": "Usuário deletado com sucesso"}), 200

# Rota do Chatbot
@app.route("/chat", methods=["POST"])
def chat_route():
    dados = request.get_json()
    usuario_id = dados.get("usuario_id")
    mensagem = dados.get("mensagem")

    if not usuario_id or not mensagem:
        return jsonify({"erro": "Campos 'usuario_id' e 'mensagem' são obrigatórios"}), 400

    resposta = chat(usuario_id, mensagem)

    # Salva a mensagem do usuário e a resposta do bot no banco
    database["mensagens"].insert_many([
        {"usuario_id": usuario_id, "mensagem": mensagem, "origem": "usuario", "data": datetime.utcnow()},
        {"usuario_id": usuario_id, "mensagem": resposta, "origem": "bot", "data": datetime.utcnow()}
    ])

    return jsonify({"resposta": resposta}), 200

# Iniciar servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)