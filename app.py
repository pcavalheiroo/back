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

# ----------------------------------------------------------------------------

@app.route("/admins/login", methods=["POST"])
def admin_login():
    try:
        dados = request.get_json()
        email = dados.get("email")
        senha = dados.get("senha")

        print(f"DEBUG BACKEND: Tentativa de login admin - Email: {email}, Senha Recebida (nao hash): {senha}")

        admin = database.admins.find_one({"email": email})
        if not admin:
            print(f"DEBUG BACKEND: Admin com email '{email}' NAO ENCONTRADO.")
            return jsonify({"erro": "Credenciais de administrador inválidas"}), 401

        senha_hash_admin = admin.get("senha")
        print(f"DEBUG BACKEND: Hash do DB (parcial): {senha_hash_admin[:10]}...") # Imprime só o começo do hash por segurança

        if senha_hash_admin is None:
            print("DEBUG BACKEND: Campo 'senha' ausente para o admin no DB.")
            return jsonify({"erro": "Erro de configuração do administrador"}), 500

        # Converta a senha recebida para bytes e o hash do DB para bytes (se ainda não for)
        senha_recebida_bytes = senha.encode('utf-8')
        senha_hash_db_bytes = senha_hash_admin.encode('utf-8') if isinstance(senha_hash_admin, str) else senha_hash_admin

        print(f"DEBUG BACKEND: Chamando bcrypt.checkpw com senha_recebida_bytes e senha_hash_db_bytes.")
        valido = bcrypt.checkpw(senha_recebida_bytes, senha_hash_db_bytes)
        
        if valido:
            print(f"DEBUG BACKEND: Senha VALIDADA com sucesso para email: {email}.")
            admin["_id"] = str(admin["_id"])
            admin.pop("senha", None)
            return jsonify(admin), 200
        else:
            print(f"DEBUG BACKEND: Senha INAVALIDA para email: {email}. bcrypt.checkpw retornou False.")
            return jsonify({"erro": "Credenciais de administrador inválidas"}), 401

    except Exception as e:
        print(f"ERRO CRÍTICO no login do administrador: {str(e)}") # Log mais detalhado
        return jsonify({"erro": "Erro interno no servidor"}), 500
    
# --- Rotas de Gerenciamento de Usuário (Administrador) ---
    
@app.route('/admin/usuarios/todos', methods=['GET'])
# @admin_required # Em um sistema real, adicione um decorador de autenticação de admin
def get_all_users_admin():
    try:
        users = list(database.usuarios.find({}, {"senha": 0})) # Não retorna a senha hashed
        for user in users:
            user['_id'] = str(user['_id'])
        return jsonify(users), 200
    except Exception as e:
        print(f"ERRO ao buscar todos os usuários: {str(e)}")
        return jsonify({"erro": "Erro interno ao buscar usuários"}), 500

@app.route('/admin/usuarios', methods=['POST'])
# @admin_required
def add_user_admin():
    try:
        dados = request.get_json()
        email = dados.get('email')
        senha = dados.get('senha')
        role = dados.get('role', 'user') # Padrão 'user' se não especificado

        if not email or not senha:
            return jsonify({"erro": "Email e senha são obrigatórios"}), 400
        
        # Validação do e-mail (reutiliza a função existente)
        is_valido, mensagem_erro = validar_email(email)
        if not is_valido:
            return jsonify({"erro": mensagem_erro}), 400 

        if database.usuarios.find_one({"email": email}):
            return jsonify({"erro": "Usuário já existe"}), 409

        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        database.usuarios.insert_one({
            "email": email,
            "senha": senha_hash,
            "role": role, # Salva o papel do usuário (user/admin)
            "criado_em": datetime.utcnow()
        })
        return jsonify({"mensagem": "Usuário adicionado com sucesso!", "email": email, "role": role}), 201
    except Exception as e:
        print(f"ERRO ao adicionar usuário: {str(e)}")
        return jsonify({"erro": "Erro interno ao adicionar usuário"}), 500

@app.route('/admin/usuarios/<user_id>', methods=['DELETE'])
# @admin_required
def delete_user_admin(user_id):
    try:
        result = database.usuarios.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count > 0:
            return jsonify({"mensagem": "Usuário excluído com sucesso!"}), 200
        else:
            return jsonify({"erro": "Usuário não encontrado"}), 404
    except Exception as e:
        print(f"ERRO ao excluir usuário: {str(e)}")
        return jsonify({"erro": "Erro interno ao excluir usuário"}), 500

@app.route('/admin/usuarios/<user_id>', methods=['PUT']) # Opcional: para editar senha, role, etc.
# @admin_required
def update_user_admin(user_id):
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400
        
        update_fields = {}
        if 'email' in dados:
            # Validação do novo e-mail se for alterado
            is_valido, mensagem_erro = validar_email(dados['email'])
            if not is_valido:
                return jsonify({"erro": mensagem_erro}), 400
            # Evita alterar para um email que já existe (exceto se for o próprio usuário)
            if database.usuarios.find_one({"email": dados['email'], "_id": {"$ne": ObjectId(user_id)}}):
                return jsonify({"erro": "Email já em uso por outro usuário"}), 409
            update_fields['email'] = dados['email']
        
        if 'senha' in dados:
            senha_hash = bcrypt.hashpw(dados['senha'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            update_fields['senha'] = senha_hash
        
        if 'role' in dados:
            if dados['role'] not in ['user', 'admin']: # Tipos de role permitidos
                return jsonify({"erro": "Role inválido"}), 400
            update_fields['role'] = dados['role']

        if not update_fields:
            return jsonify({"mensagem": "Nenhum campo para atualizar"}), 200

        result = database.usuarios.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

        if result.modified_count > 0:
            return jsonify({"mensagem": "Usuário atualizado com sucesso!"}), 200
        else:
            return jsonify({"erro": "Usuário não encontrado ou nenhum dado para atualizar"}), 404
    except Exception as e:
        print(f"ERRO ao atualizar usuário: {str(e)}")
        return jsonify({"erro": "Erro interno ao atualizar usuário"}), 500
    
# --- Rotas de Gerenciamento de Cardápio (Administrador) ---

@app.route('/admin/cardapio', methods=['POST'])
# @admin_required # Em um sistema real, adicione um decorador de autenticação de admin
def add_menu_item():
    try:
        dados = request.get_json()
        required_fields = ['nome', 'preco', 'categoria', 'descricao', 'disponibilidade']
        if not all(field in dados for field in required_fields):
            return jsonify({"erro": "Campos obrigatórios faltando"}), 400
        
        # Opcional: Validação de tipos para preco (float) e disponibilidade (boolean)

        result = database.cardapio.insert_one(dados)
        return jsonify({"mensagem": "Item adicionado com sucesso!", "item_id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"ERRO ao adicionar item do cardápio: {str(e)}")
        return jsonify({"erro": "Erro interno ao adicionar item do cardápio"}), 500

@app.route('/admin/cardapio/<item_id>', methods=['PUT'])
# @admin_required
def update_menu_item(item_id):
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        result = database.cardapio.update_one({"_id": ObjectId(item_id)}, {"$set": dados})

        if result.modified_count > 0:
            return jsonify({"mensagem": "Item atualizado com sucesso!"}), 200
        else:
            return jsonify({"erro": "Item não encontrado ou nenhum dado para atualizar"}), 404
    except Exception as e:
        print(f"ERRO ao atualizar item do cardápio: {str(e)}")
        return jsonify({"erro": "Erro interno ao atualizar item do cardápio"}), 500

@app.route('/admin/cardapio/<item_id>', methods=['DELETE'])
# @admin_required
def delete_menu_item(item_id):
    try:
        result = database.cardapio.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count > 0:
            return jsonify({"mensagem": "Item excluído com sucesso!"}), 200
        else:
            return jsonify({"erro": "Item não encontrado"}), 404
    except Exception as e:
        print(f"ERRO ao excluir item do cardápio: {str(e)}")
        return jsonify({"erro": "Erro interno ao excluir item do cardápio"}), 500

@app.route('/admin/cardapio/todos', methods=['GET'])
# @admin_required
def get_all_menu_items():
    try:
        itens = list(database.cardapio.find({}).sort([("categoria", 1), ("nome", 1)]))
        for item in itens:
            item['_id'] = str(item['_id'])
        return jsonify(itens), 200
    except Exception as e:
        print(f"ERRO ao buscar todos os itens do cardápio: {str(e)}")
        return jsonify({"erro": "Erro interno ao buscar itens do cardápio"}), 500

# --- Rotas de Gerenciamento de Pedidos (Administrador) ---

@app.route('/admin/pedidos/todos', methods=['GET'])
# @admin_required
def get_all_orders():
    try:
        pedidos_cursor = database.pedidos.find().sort("data", -1)
        pedidos_formatados = []
        for pedido in pedidos_cursor:
            pedido['_id'] = str(pedido['_id'])
            if 'data' in pedido and isinstance(pedido['data'], datetime):
                pedido['data_pedido'] = pedido['data'].isoformat() + 'Z' # Garante UTC
            else:
                pedido['data_pedido'] = datetime.utcnow().isoformat() + 'Z' # Fallback
            
            # Garante que os itens são dicionários (tratamento para dados inconsistentes)
            processo_itens = []
            total_calculado_pedido = 0 # <-- NOVO: Inicializa o total para este pedido
            for item in pedido.get('itens', []):
                if isinstance(item, dict):
                    item['_id'] = str(item.get('_id', ObjectId()))
                    # Garante que preco e quantidade são números válidos para o cálculo
                    item_preco = float(item.get('preco', 0.00))
                    item_quantidade = int(item.get('quantidade', 1))
                    
                    total_calculado_pedido += (item_preco * item_quantidade) # <-- NOVO: Calcula o total
                    processo_itens.append(item)
                else:
                    print(f"AVISO: Item de pedido mal formatado encontrado: {item} no pedido {pedido['_id']}")
                    processo_itens.append({"nome": str(item), "quantidade": 1, "preco": 0.00, "_id": str(ObjectId())})
            
            pedido['itens'] = processo_itens
            pedido['total'] = total_calculado_pedido # <-- NOVO: Adiciona o total calculado ao pedido
            
            # Opcional: Buscar nome/email do usuário para o pedido
            usuario = database.usuarios.find_one({"_id": ObjectId(pedido['usuario_id'])})
            pedido['usuario_info'] = {"nome": usuario.get("email"), "id": str(usuario["_id"])} if usuario else {"nome": "Desconhecido", "id": pedido['usuario_id']}

            pedidos_formatados.append(pedido)
            
        return jsonify(pedidos_formatados), 200
    except Exception as e:
        print(f"ERRO ao buscar todos os pedidos: {str(e)}")
        return jsonify({"erro": "Erro interno ao buscar todos os pedidos"}), 500

@app.route('/admin/pedidos/<pedido_id>/status', methods=['PUT'])
# @admin_required
def update_order_status(pedido_id):
    try:
        dados = request.get_json()
        novo_status = dados.get('status')
        if not novo_status:
            return jsonify({"erro": "Status é obrigatório"}), 400
        
        allowed_statuses = ['pendente', 'em preparo', 'pronto', 'finalizado', 'cancelado']
        if novo_status not in allowed_statuses:
            return jsonify({"erro": f"Status inválido. Use um de: {', '.join(allowed_statuses)}"}), 400

        result = database.pedidos.update_one(
            {"_id": ObjectId(pedido_id)},
            {"$set": {"status": novo_status, "data_atualizacao_status": datetime.utcnow()}}
        )

        if result.modified_count > 0:
            return jsonify({"mensagem": "Status do pedido atualizado com sucesso!", "novo_status": novo_status}), 200
        else:
            return jsonify({"erro": "Pedido não encontrado ou status já é o mesmo"}), 404
    except Exception as e:
        print(f"ERRO ao atualizar status do pedido: {str(e)}")
        return jsonify({"erro": "Erro interno ao atualizar status do pedido"}), 500

@app.route('/admin/pedidos/<pedido_id>', methods=['DELETE'])
# @admin_required
def delete_order(pedido_id):
    try:
        result = database.pedidos.delete_one({"_id": ObjectId(pedido_id)})
        if result.deleted_count > 0:
            return jsonify({"mensagem": "Pedido excluído com sucesso!"}), 200
        else:
            return jsonify({"erro": "Pedido não encontrado"}), 404
    except Exception as e:
        print(f"ERRO ao excluir pedido: {str(e)}")
        return jsonify({"erro": "Erro interno ao excluir pedido"}), 500 

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