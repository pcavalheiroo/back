from flask import Flask, request, jsonify
from flask_cors import CORS
from db.connection import database
from datetime import datetime
import os
from dotenv import load_dotenv
from services.chat_service import chat_service
import bcrypt

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Rotas Usuários ---

@app.route("/usuarios/login", methods=["POST"])
def login():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        email = dados.get("email")
        senha = dados.get("senha")

        if not email or not senha:
            return jsonify({"erro": "Email e senha são obrigatórios"}), 400

        usuario = database.usuarios.find_one({"email": email})
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        senha_hash = usuario.get("senha")

        if senha_hash is None:
            return jsonify({"erro": "Senha não cadastrada para usuário"}), 500

        # senha_hash pode estar como bytes ou string
        if isinstance(senha_hash, bytes):
            valido = bcrypt.checkpw(senha.encode('utf-8'), senha_hash)
        else:
            valido = bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))

        if valido:
            usuario["_id"] = str(usuario["_id"])
            usuario.pop("senha", None)
            return jsonify(usuario), 200

        return jsonify({"erro": "Senha incorreta"}), 401

    except Exception as e:
        print(f"Erro no login: {str(e)}")
        return jsonify({"erro": "Erro interno no servidor"}), 500

@app.route("/usuarios/cadastro", methods=["POST"])
def cadastrar_usuario():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        email = dados.get("email")
        senha = dados.get("senha")

        if not email or not senha:
            return jsonify({"erro": "Email e senha obrigatórios"}), 400

        if database.usuarios.find_one({"email": email}):
            return jsonify({"erro": "Usuário já existe"}), 409

        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        database.usuarios.insert_one({
            "email": email,
            "senha": senha_hash,
            "criado_em": datetime.utcnow()
        })

        return jsonify({"mensagem": "Usuário cadastrado com sucesso"}), 201

    except Exception as e:
        print(f"Erro no cadastro: {str(e)}")
        return jsonify({"erro": "Erro interno no servidor"}), 500

# --- Rotas do Chat ---

@app.route("/chat", methods=["POST"])
def enviar_mensagem():
    try:
        dados = request.get_json()
        usuario_id = dados.get("usuario_id")
        mensagem = dados.get("mensagem")

        if not usuario_id or not mensagem:
            return jsonify({"erro": "Dados incompletos"}), 400

        if 'mensagens' not in database.list_collection_names():
            database.create_collection('mensagens')
            print("Coleção 'mensagens' criada")

        resposta = chat_service.processar_mensagem(usuario_id, mensagem)

        result_usuario = database.mensagens.insert_one({
            "usuario_id": usuario_id,
            "mensagem": mensagem,
            "origem": "usuario",
            "data": datetime.utcnow()
        })

        result_bot = database.mensagens.insert_one({
            "usuario_id": usuario_id,
            "mensagem": resposta,
            "origem": "bot",
            "data": datetime.utcnow()
        })

        print(f"Mensagens salvas - Usuário: {result_usuario.inserted_id}, Bot: {result_bot.inserted_id}")

        return jsonify({"resposta": resposta}), 200

    except Exception as e:
        print(f"ERRO GRAVE em /chat: {str(e)}")
        return jsonify({"erro": "Erro interno no servidor"}), 500

@app.route("/chat/historico", methods=["GET"])
def historico_mensagens():
    try:
        usuario_id = request.args.get("usuario_id")
        if not usuario_id:
            return jsonify({"erro": "ID do usuário é obrigatório"}), 400

        historico = list(database.mensagens.find(
            {"usuario_id": usuario_id},
            sort=[("data", 1)],
            limit=100
        ))

        return jsonify([
            {
                "_id": str(msg["_id"]),
                "mensagem": msg["mensagem"],
                "origem": msg["origem"],
                "data": msg["data"].isoformat()
            } for msg in historico
        ]), 200

    except Exception as e:
        print(f"Erro ao buscar histórico: {str(e)}")
        return jsonify({"erro": "Erro ao carregar histórico"}), 500

@app.route("/chat/limpar_historico", methods=["DELETE"])
def limpar_historico():
    try:
        usuario_id = request.args.get("usuario_id")
        if not usuario_id:
            return jsonify({"erro": "ID do usuário é obrigatório"}), 400

        resultado = database.mensagens.delete_many({"usuario_id": usuario_id})

        return jsonify({
            "mensagem": "Histórico limpo com sucesso",
            "deletados": resultado.deleted_count
        }), 200

    except Exception as e:
        print(f"Erro ao limpar histórico: {str(e)}")
        return jsonify({"erro": "Falha ao limpar histórico"}), 500

# --- Rota do Cardápio ---

@app.route('/cardapio', methods=['GET'])
def get_cardapio():
    try:
        if 'cardapio' not in database.list_collection_names():
            return jsonify({"erro": "Cardápio não disponível"}), 404

        itens = list(database.cardapio.find(
            {"disponibilidade": True},
            {"_id": 0}
        ).sort([("categoria", 1), ("nome", 1)]))

        if not itens:
            return jsonify({"aviso": "Cardápio vazio"}), 200

        print(f"Retornando {len(itens)} itens do cardápio")
        return jsonify(itens), 200

    except Exception as e:
        print(f"ERRO no cardápio: {str(e)}")
        return jsonify({"erro": "Erro interno ao buscar cardápio"}), 500

# --- Inicialização ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
