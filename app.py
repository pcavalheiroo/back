# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from db.connection import database
from datetime import datetime
import os
from dotenv import load_dotenv
from services.chat_service import chat_service
import bcrypt
import re
from bson.objectid import ObjectId

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Rotas Usuários ---

def validar_email(email):
    # Expressão regular para um formato de e-mail básico
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    # Domínios permitidos
    dominios_permitidos = ["@p4ed.com", "@sistemapoliedro.com.br"]

    if not re.match(email_regex, email):
        return False, "Formato de e-mail inválido."

    # Verifica se o e-mail termina com um dos domínios permitidos
    for dominio in dominios_permitidos:
        if email.endswith(dominio):
            return True, None # E-mail válido, sem erro
            
    return False, "E-mail não pertence a um domínio permitido."

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

        # Validação do e-mail
        is_valido, mensagem_erro = validar_email(email)
        if not is_valido:
            return jsonify({"erro": "Credenciais inválidas"}), 401 

        usuario = database.usuarios.find_one({"email": email})
        if not usuario:
            return jsonify({"erro": "Credenciais inválidas"}), 401 # Mensagem genérica por segurança

        senha_hash = usuario.get("senha")

        if senha_hash is None:
            return jsonify({"erro": "Erro de configuração do usuário"}), 500 # Melhor mensagem para este caso

        # senha_hash pode estar como bytes ou string
        if isinstance(senha_hash, bytes):
            valido = bcrypt.checkpw(senha.encode('utf-8'), senha_hash)
        else:
            valido = bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))

        if valido:
            usuario["_id"] = str(usuario["_id"])
            usuario.pop("senha", None)
            return jsonify(usuario), 200

        return jsonify({"erro": "Credenciais inválidas"}), 401 # Mensagem genérica por segurança

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

        # --- ADIÇÃO CRÍTICA AQUI: VALIDAÇÃO DE E-MAIL ---
        is_valido, mensagem_erro = validar_email(email)
        if not is_valido:
            # Retorne um erro específico sobre a validação do e-mail
            return jsonify({"erro": mensagem_erro}), 400 
        # --- FIM DA ADIÇÃO ---

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

        print(f"DEBUG: Mensagem recebida para usuario_id: {usuario_id}")

        if not usuario_id or not mensagem:
            return jsonify({"erro": "Dados incompletos"}), 400

        if 'mensagens' not in database.list_collection_names():
            database.create_collection('mensagens')
            print("Coleção 'mensagens' criada")

        # 1. Obter o pedido em aberto para o usuário específico
        pedido_em_aberto_usuario = database.pedidos_em_aberto.find_one({"usuario_id": usuario_id})

        # 2. Obter todos os pedidos finalizados para o histórico
        todos_os_pedidos_finalizados = list(database.pedidos.find({"usuario_id": usuario_id}))

        # 3. Obter o cardápio disponível
        cardapio_disponivel = list(database.cardapio.find({"disponibilidade": True}))

        # 4. Passar todos os dados necessários para o chat_service.processar_mensagem
        resposta = chat_service.processar_mensagem(
            usuario_id, 
            mensagem, 
            pedido_em_aberto_usuario,
            todos_os_pedidos_finalizados,
            cardapio_disponivel,
            database.pedidos_em_aberto, # Coleção de pedidos em aberto
            database.pedidos            # Coleção de pedidos finalizados
        )

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
        print(f"DEBUG: Requisitando histórico para usuario_id: {usuario_id}")
        if not usuario_id:
            return jsonify({"erro": "ID do usuário é obrigatório"}), 400

        historico = list(database.mensagens.find(
            {"usuario_id": usuario_id},
            sort=[("data", 1)],
            limit=100
        ))
        print(f"DEBUG: Histórico de mensagens encontrado para {usuario_id}: {historico}")

        return jsonify([
            {
                "_id": str(msg["_id"]),
                "mensagem": msg["mensagem"],
                "origem": msg.get("origem") or msg.get("remetente"),
                # Adicione 'Z' ao final para indicar que é UTC
                "data": (msg.get("data") or msg.get("timestamp")).isoformat() + 'Z' # <-- MUDANÇA AQUI
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
            return jsonify({"erro": "Coleção 'cardapio' não encontrada no banco de dados."}), 500

        itens = list(database.cardapio.find(
            {"disponibilidade": True},
            # Inclua todos os campos necessários e o _id!
            {"_id": 1, "nome": 1, "preco": 1, "categoria": 1, "descricao": 1, "disponibilidade": 1} 
        ).sort([("categoria", 1), ("nome", 1)]))

        # É ABSOLUTAMENTE ESSENCIAL converter o ObjectId para string
        for item in itens:
            item['_id'] = str(item['_id'])

        if not itens:
            return jsonify({"aviso": "Cardápio vazio ou sem itens disponíveis."}), 200

        print(f"Retornando {len(itens)} itens do cardapio")
        return jsonify(itens), 200

    except Exception as e:
        print(f"ERRO no cardápio: {str(e)}")
        return jsonify({"erro": "Erro interno ao buscar cardápio"}), 500
    
@app.route('/pedidos/historico', methods=['GET'])
def get_historico_pedidos():
    try:
        usuario_id = request.args.get('usuario_id')
        if not usuario_id:
            return jsonify({"erro": "ID do usuário é obrigatório"}), 400

        cardapio_map = {item['nome']: item for item in database.cardapio.find({"disponibilidade": True})}

        pedidos_cursor = database.pedidos.find(
            {"usuario_id": usuario_id}
        ).sort("data", -1)

        pedidos_formatados = []
        for pedido in pedidos_cursor:
            pedido['_id'] = str(pedido['_id'])
            
            if 'data' in pedido and isinstance(pedido['data'], datetime):
                # Adicione 'Z' ao final para indicar que é UTC
                pedido['data_pedido'] = pedido['data'].isoformat() + 'Z' # <-- MUDANÇA AQUI
            else:
                # Adicione 'Z' ao final para indicar que é UTC
                pedido['data_pedido'] = datetime.utcnow().isoformat() + 'Z'

            total_pedido_calculado = 0
            itens_processados = []

            for item_pedido_original in pedido.get('itens', []):
                # --- ADIÇÃO DE VERIFICAÇÃO DE TIPO AQUI ---
                if not isinstance(item_pedido_original, dict):
                    print(f"AVISO: Item de pedido mal formatado encontrado (não é um dicionário): '{item_pedido_original}' no pedido ID: {pedido['_id']}. Pulando este item.")
                    continue  # Pula este item e vai para o próximo
                # --- FIM DA ADIÇÃO ---

                nome_item = item_pedido_original.get('nome') 
                quantidade_item = item_pedido_original.get('quantidade', 1) 

                preco_item = 0.00
                
                # Sua lógica de busca de preço no cardápio é boa
                if nome_item in cardapio_map:
                    preco_item = cardapio_map[nome_item].get('preco', 0.00)
                else:
                    # Se o item do pedido não está no cardápio, pega o preço direto do item se existir
                    preco_item = item_pedido_original.get('preco', 0.00)

                itens_processados.append({
                    "_id": str(item_pedido_original.get('_id', ObjectId())),
                    "nome": nome_item,
                    "preco": preco_item,
                    "quantidade": quantidade_item
                })
                total_pedido_calculado += (preco_item * quantidade_item)

            pedido['total'] = total_pedido_calculado
            pedido['itens'] = itens_processados
            
            pedidos_formatados.append(pedido)

        if not pedidos_formatados:
            return jsonify({"aviso": "Nenhum pedido encontrado para este usuário."}), 200

        print(f"DEBUG: Retornando {len(pedidos_formatados)} pedidos formatados para o usuário {usuario_id}")
        return jsonify(pedidos_formatados), 200

    except Exception as e:
        print(f"ERRO ao buscar histórico de pedidos: {str(e)}")
        return jsonify({"erro": "Erro interno ao buscar histórico de pedidos"}), 500

# --- Inicialização ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))