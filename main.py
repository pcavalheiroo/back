from flask import Flask, request, jsonify
from flask_cors import CORS
from models import autenticar_usuario, autenticar_visitante, cadastrar_usuario
from chat import chat
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    senha = data.get("senha")
    visitante = data.get("codigo_acesso")

    if visitante:
        user = autenticar_visitante(visitante)
        if user:
            return jsonify({"status": "ok", "usuario_id": str(user["_id"]), "tipo": "visitante"})
        return jsonify({"status": "erro", "mensagem": "Código inválido."}), 401

    if email and senha:
        user = autenticar_usuario(email, senha)
        if user:
            return jsonify({"status": "ok", "usuario_id": str(user["_id"]), "tipo": user["tipo"]})
        return jsonify({"status": "erro", "mensagem": "Credenciais inválidas."}), 401

    return jsonify({"status": "erro", "mensagem": "Dados ausentes."}), 400

@app.route("/chat", methods=["POST"])
def endpoint_chat():
    data = request.json
    usuario_id = data.get("usuario_id")
    mensagem = data.get("mensagem")

    if not usuario_id or not mensagem:
        return jsonify({"erro": "Dados incompletos"}), 400

    resposta = chat(usuario_id, mensagem)
    return jsonify({"resposta": resposta})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
