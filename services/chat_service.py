# C:\Users\Pedro\Documents\GitHub\back\services\chat_service.py

from datetime import datetime
from thefuzz import fuzz

class ChatService:

    def __init__(self):
        pass
    
    def _mensagem_similar(self, mensagem, padroes, limiar=70):
        mensagem = mensagem.lower()
        for padrao in padroes:
            score_partial = fuzz.partial_ratio(mensagem, padrao.lower())
            score_ratio = fuzz.ratio(mensagem, padrao.lower())
            
            if score_partial >= limiar or score_ratio >= limiar:
                return True
        return False

    def _contem_item_do_cardapio(self, mensagem, cardapio_data):
        if not isinstance(cardapio_data, list):
            return False 
        
        nomes_produtos = [p['nome'].lower() for p in cardapio_data if 'nome' in p]
        
        for nome_produto in nomes_produtos:
            if fuzz.partial_ratio(mensagem, nome_produto) >= 80 or fuzz.token_sort_ratio(mensagem, nome_produto) >= 80:
                return True
        return False

    # NOVO MÉTODO: Responde sobre o status do pedido EM ABERTO
    def _responder_status_pedido_aberto(self, pedido_em_aberto_doc):
        if pedido_em_aberto_doc and pedido_em_aberto_doc.get("itens"):
            return f"📝 Seu pedido em andamento: {', '.join(pedido_em_aberto_doc['itens'])}. Deseja adicionar algo mais ou finalizar?"
        else:
            return "Você ainda não iniciou um pedido."

    # NOVA INTENÇÃO: Para frases como "qual meu pedido", "meu carrinho"
    def _intencao_ver_status_pedido_aberto(self, mensagem):
        padroes = ["qual meu pedido", "meu pedido", "o que eu pedi", "ver meu pedido", "itens do pedido", "meu carrinho"]
        return self._mensagem_similar(mensagem, padroes, limiar=75)


    # MÉTODO PRINCIPAL DE PROCESSAMENTO DA MENSAGEM
    def processar_mensagem(self, usuario_id, mensagem, 
                           pedido_em_aberto_doc, # Documento do pedido em aberto (ou None)
                           todos_os_pedidos_finalizados, # Lista de pedidos finalizados do usuário
                           cardapio_data, # Lista de itens do cardápio
                           pedidos_em_aberto_collection, # Coleção MongoDB 'pedidos_em_aberto'
                           pedidos_collection): # Coleção MongoDB 'pedidos'

        mensagem_processada = mensagem.lower().strip()

        # 1. Priorize saudações e agradecimentos
        if self._mensagem_similar(mensagem_processada, ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "tudo bem", "oi tudo bem", "como vai", "tudo em ordem", "saudações", "eae", "fala"], limiar=75):
            return "Olá! 👋 Como posso te ajudar hoje?"

        if self._mensagem_similar(mensagem_processada, ["obrigado", "valeu", "agradecido", "muito obrigado", "obrigada", "grato", "agradeço"], limiar=80):
            return "De nada! 😊 Se precisar de algo, é só chamar."
        
        # 2. Finalização de pedido (ALTA PRIORIDADE)
        if self._intencao_finalizar_pedido(mensagem_processada):
            return self._finalizar_pedido(usuario_id, pedido_em_aberto_doc, pedidos_em_aberto_collection, pedidos_collection)

        # 3. Consultar histórico de pedidos (MEUS PEDIDOS) - ALTA PRIORIDADE PARA EVITAR CONFLITO
        if self._intencao_consultar_pedidos(mensagem_processada):
            return self._consultar_pedidos(usuario_id, todos_os_pedidos_finalizados)

        # 4. Consultar status do pedido EM ABERTO (MEU PEDIDO / MEU CARRINHO) - PRIORIDADE ANTES DE FAZER NOVOS PEDIDOS
        if self._intencao_ver_status_pedido_aberto(mensagem_processada):
            return self._responder_status_pedido_aberto(pedido_em_aberto_doc)

        # 5. Lógica de registro/adição de pedido (detecção de item do cardápio ou intenção de fazer pedido)
        #    Isso deve vir DEPOIS de verificar as intenções de consulta de pedido/histórico.
        #    A verificação 'pedidos_em_aberto is not None' foi removida daqui, pois a intenção é só registrar.
        if self._contem_item_do_cardapio(mensagem_processada, cardapio_data) or \
           self._intencao_fazer_pedido(mensagem_processada):
            return self._registrar_pedido(usuario_id, mensagem_processada, pedido_em_aberto_doc, cardapio_data, pedidos_em_aberto_collection)

        # 6. Ver cardápio
        if self._intencao_ver_cardapio(mensagem_processada):
            return self._responder_cardapio(cardapio_data)
        
        # 7. Fallback
        return "Desculpe, não entendi sua mensagem. Você pode tentar reformular ou digitar 'cardápio' para ver o que temos disponível."

    def _intencao_ver_cardapio(self, mensagem):
        padroes = [
            "cardapio", "cardápio", "menu", "catalogo", "lista de pratos", 
            "o que tem", "o que vocês têm", "o que voces tem", "o que está disponível",
            "o que posso pedir", "quero comer", "almoço", "jantar", "refeição", "lanche", 
            "comida", "pratos", "opções", "qual o cardapio", "meu cardapio", "ver o menu",
            "cardapio do dia", "cardapio completo", "mostrar cardapio"
        ]
        return self._mensagem_similar(mensagem, padroes, limiar=70) 

    def _responder_cardapio(self, cardapio_data):
        try:
            if not isinstance(cardapio_data, list) or not cardapio_data:
                return "Atualmente o cardápio está vazio. 😢"

            categorias = {}
            for item in cardapio_data:
                if 'categoria' not in item or 'nome' not in item:
                    continue
                categoria = item.get("categoria", "Outros").capitalize()
                nome = item.get("nome", "Item sem nome")
                preco = item.get("preco", "preço indisponível")
                if isinstance(preco, (int, float)):
                    preco = f"R${preco:.2f}"
                categorias.setdefault(categoria, []).append(f"- {nome} ({preco})")

            if not categorias:
                return "Atualmente o cardápio está vazio. 😢"

            resposta = "🍽️ Aqui está o nosso cardápio:\n\n"
            for cat, lista_itens in categorias.items():
                resposta += f"📌 *{cat}*\n" + "\n".join(lista_itens) + "\n\n"

            return resposta.strip()

        except Exception as e:
            print(f"Erro ao montar cardápio: {e}")
            return "Houve um problema ao acessar o cardápio. Tente novamente mais tarde. 😕"

    def _intencao_fazer_pedido(self, mensagem):
        padroes = [
            "quero pedir", "fazer um pedido", "quero isso", "gostaria de", 
            "me vê", "pode ser", "pedido", "quero", "pedir", "adicionar ao pedido",
            "colocar no pedido", "escolher", "vou querer", "me traga"
        ]
        return self._mensagem_similar(mensagem, padroes, limiar=70)

    def _intencao_finalizar_pedido(self, mensagem):
        padroes = [
            "só isso", "so isso", "só", "so", "mais nada", "encerrar",
            "finalizar", "fechar pedido", "concluído", "concluido",
            "pedido concluído", "pedido concluido", "concluir", "terminar",
            "pode fechar", "está bom assim", "pronto", "acabou", "já está bom", "finalizar agora"
        ]
        return self._mensagem_similar(mensagem, padroes, limiar=75)
            
    def _finalizar_pedido(self, usuario_id, pedido_em_aberto_doc, pedidos_em_aberto_collection, pedidos_collection):
        try:
            if not pedido_em_aberto_doc or not pedido_em_aberto_doc.get("itens"):
                return "Você ainda não iniciou um pedido ou não há itens para finalizar."

            pedido_final = {
                "usuario_id": usuario_id,
                "itens": pedido_em_aberto_doc["itens"],
                "data": datetime.utcnow(),
                "status": "recebido"
            }
            
            pedidos_collection.insert_one(pedido_final)
            
            pedidos_em_aberto_collection.delete_one({"_id": pedido_em_aberto_doc["_id"]})

            return f"✅ Pedido finalizado com os itens: {', '.join(pedido_em_aberto_doc['itens'])}. Em breve entraremos em contato para confirmar."

        except Exception as e:
            print(f"Erro ao finalizar pedido: {e}")
            return "❌ Ocorreu um erro ao finalizar seu pedido. Tente novamente."

    def _registrar_pedido(self, usuario_id, mensagem, pedido_em_aberto_doc, cardapio_data, pedidos_em_aberto_collection):
        try:
            # REMOVIDO: A verificação de "qual meu pedido" para evitar conflito.
            # Essa funcionalidade agora é tratada por _intencao_ver_status_pedido_aberto

            nomes_produtos = [p['nome'].lower() for p in cardapio_data if 'nome' in p]

            itens_detectados = []

            for nome_produto in nomes_produtos:
                if fuzz.ratio(mensagem, nome_produto) >= 85:
                    itens_detectados.append(nome_produto)
                elif fuzz.partial_ratio(mensagem, nome_produto) >= 75:
                    itens_detectados.append(nome_produto)
                elif fuzz.token_sort_ratio(mensagem, nome_produto) >= 70:
                     itens_detectados.append(nome_produto)

            itens_detectados = list(set(itens_detectados))

            if not itens_detectados:
                return ("Não consegui identificar os itens do seu pedido. "
                        "Por favor, diga exatamente o que deseja pedir, "
                        "por exemplo: 'quero um sanduíche natural e um suco'.")

            if pedido_em_aberto_doc:
                itens_existentes = pedido_em_aberto_doc.get("itens", [])
                novos_itens = itens_existentes + [item for item in itens_detectados if item not in itens_existentes]
                pedidos_em_aberto_collection.update_one(
                    {"_id": pedido_em_aberto_doc["_id"]},
                    {"$set": {"itens": novos_itens, "data_atualizacao": datetime.utcnow()}}
                )
            else:
                pedidos_em_aberto_collection.insert_one(
                    {"usuario_id": usuario_id, "itens": itens_detectados, "data_inicio": datetime.utcnow()}
                )
            
            return f"✅ Adicionei ao seu pedido: {', '.join(itens_detectados)}. Deseja pedir mais alguma coisa?"

        except Exception as e:
            print(f"Erro ao registrar pedido: {str(e)}")
            return "❌ Ocorreu um erro ao processar seu pedido. Tente novamente."
                
    def _intencao_consultar_pedidos(self, mensagem):
        padroes = [
            "meus pedidos", "meu histórico de pedidos", "pedidos anteriores",
            "o que eu já pedi", "histórico de pedidos", "consultar pedidos",
            "ver meus pedidos", "lista de pedidos"
        ]
        return self._mensagem_similar(mensagem, padroes, limiar=75)

    def _consultar_pedidos(self, usuario_id, pedidos_list):
        try:
            usuario_pedidos = pedidos_list

            if not usuario_pedidos:
                return "Você ainda não fez nenhum pedido."

            resposta = "Seu histórico de pedidos:\n\n"
            for pedido in usuario_pedidos:
                data_obj = pedido.get('data', datetime.utcnow()) 
                if isinstance(data_obj, datetime):
                    data_formatada = data_obj.strftime("%d/%m/%Y %H:%M:%S")
                else:
                    data_formatada = str(data_obj) 
                
                itens_str = ", ".join(pedido.get('itens', []))
                status_str = pedido.get('status', 'desconhecido')
                resposta += f"📅 {data_formatada}: {itens_str} (Status: {status_str})\n"

            return resposta.strip()

        except Exception as e:
            print(f"Erro ao consultar pedidos: {e}")
            return "Ocorreu um erro ao consultar seu histórico de pedidos. Tente novamente mais tarde."

# Instância única do serviço
chat_service = ChatService()