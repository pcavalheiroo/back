from db.connection import database
import re
from datetime import datetime
from thefuzz import fuzz

class ChatService:

    def __init__(self):
        pass
    
    def _mensagem_similar(self, mensagem, padroes, limiar=80):
        for padrao in padroes:
            score = fuzz.partial_ratio(mensagem, padrao)
            if score >= limiar:
                return True
        return False


    def processar_mensagem(self, usuario_id, mensagem):
        mensagem = mensagem.lower().strip()

        if self._intencao_ver_cardapio(mensagem):
            return self._responder_cardapio()

        if self._intencao_fazer_pedido(mensagem):
            return self._registrar_pedido(usuario_id, mensagem, continuar=True)

        # Se houver um pedido em andamento, verificar se é continuação
        pedido_em_andamento = database.pedidos_em_aberto.find_one({"usuario_id": usuario_id})
        if pedido_em_andamento:
            return self._registrar_pedido(usuario_id, mensagem, continuar=True)
        
        if self._intencao_finalizar_pedido(mensagem):
            return self._finalizar_pedido(usuario_id)

        if self._mensagem_similar(mensagem, ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
            return "Olá! 👋 Como posso te ajudar hoje?"

        if self._mensagem_similar(mensagem, ["obrigado", "valeu", "agradecido"]):
            return "De nada! 😊 Se precisar de algo, é só chamar."


        return "Desculpe, não entendi sua mensagem. Você pode tentar reformular ou digitar 'cardápio' para ver o que temos disponível."

    def _intencao_ver_cardapio(self, mensagem):
        padroes = [
            "cardapio", "cardápio", "menu",
            "o que tem", "o que vocês têm", "o que voces tem",
            "o que posso pedir", "quero comer", "almoço",
            "jantar", "refeição", "lanche", "comida"
        ]
        return self._mensagem_similar(mensagem, padroes)

    def _responder_cardapio(self):
        try:
            itens = list(database.cardapio.find(
                {"disponibilidade": True},
                {"_id": 0}
            ).sort([("categoria", 1), ("nome", 1)]))

            if not itens:
                return "Atualmente o cardápio está vazio. 😢"

            categorias = {}
            for item in itens:
                categoria = item.get("categoria", "Outros").capitalize()
                nome = item.get("nome", "Item sem nome")
                preco = item.get("preco", "preço indisponível")
                if isinstance(preco, (int, float)):
                    preco = f"R${preco:.2f}"
                categorias.setdefault(categoria, []).append(f"- {nome} ({preco})")

            resposta = "🍽️ Aqui está o nosso cardápio:\n\n"
            for cat, lista_itens in categorias.items():
                resposta += f"📌 *{cat}*\n" + "\n".join(lista_itens) + "\n\n"

            return resposta.strip()

        except Exception as e:
            print(f"Erro ao montar cardápio: {e}")
            return "Houve um problema ao acessar o cardápio. Tente novamente mais tarde. 😕"

    def _intencao_fazer_pedido(self, mensagem):
        padroes = [
            "quero pedir", "fazer um pedido", "quero isso",
            "gostaria de", "me vê", "pode ser", "pedido", "quero"
        ]
        return self._mensagem_similar(mensagem, padroes)

    
    def _intencao_finalizar_pedido(self, mensagem):
        padroes = [
            "só isso", "so isso", "só", "so", "mais nada",
            "finalizar", "fechar pedido", "concluído", "concluido",
            "pedido concluído", "pedido concluido", "concluir", "terminar"
        ]
        return self._mensagem_similar(mensagem, padroes)

    
    def _finalizar_pedido(self, usuario_id):
        try:
            sessao = database.pedidos_em_aberto.find_one({"usuario_id": usuario_id})
            if not sessao or not sessao.get("itens"):
                return "Você ainda não iniciou um pedido ou não há itens para finalizar."

            pedido = {
                "usuario_id": usuario_id,
                "itens": sessao["itens"],
                "data": datetime.utcnow(),
                "status": "recebido"
            }
            database.pedidos.insert_one(pedido)
            database.pedidos_em_aberto.delete_one({"usuario_id": usuario_id})

            return f"✅ Pedido finalizado com os itens: {', '.join(sessao['itens'])}. Em breve entraremos em contato para confirmar."

        except Exception as e:
            print(f"Erro ao finalizar pedido: {e}")
            return "❌ Ocorreu um erro ao finalizar seu pedido. Tente novamente."


    def _registrar_pedido(self, usuario_id, mensagem, continuar=False):
        try:
            # Verifica se o usuário quer finalizar o pedido
            if any(f in mensagem for f in ["só isso", "pedido concluído", "finalizar", "mais nada", "pode fechar"]):
                sessao = database.pedidos_em_aberto.find_one({"usuario_id": usuario_id})
                if sessao and sessao.get("itens"):
                    pedido_final = {
                        "usuario_id": usuario_id,
                        "itens": sessao["itens"],
                        "data": datetime.utcnow(),
                        "status": "recebido"
                    }
                    database.pedidos.insert_one(pedido_final)
                    database.pedidos_em_aberto.delete_one({"usuario_id": usuario_id})
                    return f"✅ Pedido concluído com os itens: {', '.join(sessao['itens'])}. Obrigado pelo seu pedido!"
                else:
                    return "Você ainda não adicionou itens ao seu pedido."

            # Se quiser ver o que está no pedido atual
            if "qual meu pedido" in mensagem or "meu pedido" in mensagem:
                sessao = database.pedidos_em_aberto.find_one({"usuario_id": usuario_id})
                if sessao and sessao.get("itens"):
                    return f"📝 Seu pedido até agora: {', '.join(sessao['itens'])}. Deseja adicionar algo mais ou finalizar?"
                else:
                    return "Você ainda não iniciou um pedido."

            # Buscar nomes de produtos no banco
            produtos_cursor = database.cardapio.find({"disponibilidade": True}, {"nome": 1, "_id": 0})
            nomes_produtos = [p['nome'].lower() for p in produtos_cursor]

            mensagem_lower = mensagem.lower()
            palavras = re.findall(r'\w+', mensagem_lower)

            itens_detectados = []
            itens_pedidos = []

            for nome_produto in nomes_produtos:
                for palavra in palavras:
                    score = fuzz.ratio(palavra, nome_produto)
                    if score >= 75:
                        itens_detectados.append(nome_produto)
                        break  # Evita repetir o mesmo produto

            if not itens_detectados:
                return ("Não consegui identificar os itens do seu pedido. "
                        "Por favor, diga exatamente o que deseja pedir, "
                        "por exemplo: 'quero um sanduíche natural e um suco'.")

            # Atualiza ou cria a sessão de pedido no banco temporário
            sessao = database.pedidos_em_aberto.find_one({"usuario_id": usuario_id})
            if sessao:
                itens_existentes = sessao.get("itens", [])
                novos_itens = itens_existentes + [item for item in itens_detectados if item not in itens_existentes]
                database.pedidos_em_aberto.update_one(
                    {"usuario_id": usuario_id},
                    {"$set": {"itens": novos_itens}}
                )
            else:
                if continuar:
                    # Sessão já iniciada — adicionar ao pedido em aberto
                    database.pedidos_em_aberto.update_one(
                        {"usuario_id": usuario_id},
                        {"$push": {"itens": {"$each": itens_pedidos}}},
                        upsert=True
                    )
                    return f"Adicionei {', '.join(itens_pedidos)} ao seu pedido. Deseja mais alguma coisa?"

                else:
                    # Iniciar nova sessão de pedido
                    database.pedidos_em_aberto.update_one(
                        {"usuario_id": usuario_id},
                        {"$set": {"itens": itens_pedidos}},
                        upsert=True
                    )
                    return f"✅ Pedido iniciado com: {', '.join(itens_pedidos)}. Deseja mais alguma coisa?"

            return f"✅ Adicionei ao seu pedido: {', '.join(itens_detectados)}. Deseja pedir mais alguma coisa?"

        except Exception as e:
            print(f"Erro ao registrar pedido: {str(e)}")
            return "❌ Ocorreu um erro ao processar seu pedido. Tente novamente."
        
# Instância única do serviço
chat_service = ChatService()
