from datetime import datetime
from thefuzz import fuzz
import pytz # Importe a biblioteca pytz
from babel.dates import format_datetime # Importe format_datetime do Babel
from bson.objectid import ObjectId
import re

class ChatService:

    def __init__(self):
        # Defina o fuso horário local aqui (Ex: São Paulo)
        self.timezone_sp = pytz.timezone('America/Sao_Paulo')
        self.numero_para_digito = {
            "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3,
            "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8,
            "nove": 9, "dez": 10
        }
        self.quantidade_pattern = r"\b(\d+)\b|\b(" + "|".join(re.escape(k) for k in self.numero_para_digito.keys()) + r")\b"
    
    def _mensagem_similar(self, mensagem, padroes, limiar=70):
        mensagem = mensagem.lower()
        for padrao in padroes:
            score_partial = fuzz.partial_ratio(mensagem, padrao.lower())
            score_ratio = fuzz.ratio(mensagem, padrao.lower())
            score_token_set = fuzz.token_set_ratio(mensagem, padrao.lower()) # Adicionado para robustez
            
            if score_partial >= limiar or score_ratio >= limiar or score_token_set >= limiar:
                return True
        return False

    def _contem_item_do_cardapio(self, mensagem, cardapio_data):
        if not isinstance(cardapio_data, list):
            return False 
        
        nomes_produtos = [p['nome'].lower() for p in cardapio_data if 'nome' in p]
        
        for nome_produto in nomes_produtos:
            # Usando token_set_ratio e partial_ratio para maior flexibilidade
            if fuzz.partial_ratio(mensagem, nome_produto) >= 80 or \
               fuzz.token_sort_ratio(mensagem, nome_produto) >= 80 or \
               fuzz.token_set_ratio(mensagem, nome_produto) >= 80: # Adicionado token_set_ratio
                return True
        return False

    def _responder_status_pedido_aberto(self, pedido_em_aberto_doc):
        if pedido_em_aberto_doc and pedido_em_aberto_doc.get("itens"):
            itens_formatados = [item.capitalize() for item in pedido_em_aberto_doc['itens']]
            return f"📝 Seu pedido em andamento: {', '.join(itens_formatados)}. Deseja adicionar algo mais ou finalizar?"
        else:
            return "Você ainda não iniciou um pedido."

    def _intencao_ver_status_pedido_aberto(self, mensagem):
        padroes = ["qual meu pedido atual", "meu pedido agora", "o que estou pedindo", "meu carrinho atual", "ver meu pedido em andamento"]
        return self._mensagem_similar(mensagem, padroes, limiar=75)

    def processar_mensagem(self, usuario_id, mensagem, 
                             pedido_em_aberto_doc, 
                             todos_os_pedidos_finalizados, 
                             cardapio_data, 
                             pedidos_em_aberto_collection, 
                             pedidos_collection):

        mensagem_processada = mensagem.lower().strip()

        print(f"DEBUG Processar Mensagem: Mensagem: '{mensagem_processada}'")
        print(f"DEBUG Processar Mensagem: Pedido em aberto DOC: {pedido_em_aberto_doc}")
        print(f"DEBUG Processar Mensagem: Pedidos finalizados: {todos_os_pedidos_finalizados}")


        if self._intencao_consultar_pedidos(mensagem_processada):
            print("DEBUG: Intenção 'consultar pedidos finalizados' detectada.")
            return self._consultar_pedidos(usuario_id, todos_os_pedidos_finalizados)

        if self._intencao_ver_status_pedido_aberto(mensagem_processada):
            print("DEBUG: Intenção 'ver status pedido aberto' detectada.")
            return self._responder_status_pedido_aberto(pedido_em_aberto_doc)

        if self._intencao_finalizar_pedido(mensagem_processada):
            print("DEBUG: Intenção 'finalizar pedido' detectada.")
            return self._finalizar_pedido(usuario_id, pedido_em_aberto_doc, pedidos_em_aberto_collection, pedidos_collection)

        if self._contem_item_do_cardapio(mensagem_processada, cardapio_data) or \
           self._intencao_fazer_pedido(mensagem_processada):
            print("DEBUG: Intenção 'fazer/registrar pedido' ou 'contem item cardápio' detectada.")
            return self._registrar_pedido(usuario_id, mensagem_processada, pedido_em_aberto_doc, cardapio_data, pedidos_em_aberto_collection)

        if self._mensagem_similar(mensagem_processada, ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "tudo bem", "oi tudo bem", "como vai", "tudo em ordem", "saudações", "eae", "fala"], limiar=75):
            print("DEBUG: Intenção 'saudação' detectada.")
            return "Olá! 👋 Como posso te ajudar hoje?"

        if self._mensagem_similar(mensagem_processada, ["obrigado", "valeu", "agradecido", "muito obrigado", "obrigada", "grato", "agradeço"], limiar=80):
            print("DEBUG: Intenção 'agradecimento' detectada.")
            return "De nada! 😊 Se precisar de algo, é só chamar."
        
        if self._intencao_ver_cardapio(mensagem_processada):
            print("DEBUG: Intenção 'ver cardápio' detectada.")
            return self._responder_cardapio(cardapio_data)
        
        print("DEBUG: Nenhuma intenção específica detectada. Usando fallback.")
        return "Desculpe, não entendi sua mensagem. Você pode tentar reformular ou digitar 'cardápio' para ver o que temos disponível."

    def _intencao_ver_cardapio(self, mensagem):
        padroes = [
            "cardapio", "cardápio", "menu", "catalogo", "lista de pratos", 
            "o que tem", "o que vocês têm", "o que voces tem", "o que está disponível",
            "o que posso pedir", "quero comer", "almoço", "jantar", "refeição", "lanche", 
            "comida", "pratos", "opções", "qual o cardapio", "meu cardapio", "ver o menu",
            "cardapio do dia", "cardapio completo", "mostrar cardapio", "quero ver o cardapio",
            "manda o cardapio"
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
                return "Atualmente o cardapio está vazio. 😢"

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
            "colocar no pedido", "escolher", "vou querer", "me traga", "quero fazer um pedido",
            "pdiddy"
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
                print(f"DEBUG Finalizar Pedido: Nenhum pedido em aberto ou sem itens para o usuario_id: {usuario_id}")
                return "Você ainda não iniciou um pedido ou não há itens para finalizar."

            # Extrai os nomes dos itens para a mensagem de resposta
            # Usa uma list comprehension para pegar apenas o 'nome' de cada dicionário de item
            nomes_dos_itens_para_resposta = [item['nome'] for item in pedido_em_aberto_doc['itens']]

            pedido_final = {
                "usuario_id": usuario_id,
                "itens": pedido_em_aberto_doc["itens"], # Aqui, continua sendo a lista de dicionários!
                "data": datetime.utcnow(), 
                "status": "recebido"
            }
            
            pedidos_collection.insert_one(pedido_final)
            print(f"DEBUG Finalizar Pedido: Pedido finalizado salvo na coleção 'pedidos': {pedido_final}")
            
            pedidos_em_aberto_collection.delete_one({"_id": pedido_em_aberto_doc["_id"]})
            print(f"DEBUG Finalizar Pedido: Pedido em aberto deletado da coleção 'pedidos_em_aberto' para _id: {pedido_em_aberto_doc['_id']}")

            # Usa a lista de nomes extraídos para a resposta
            return f"✅ Pedido finalizado com os itens: {', '.join(nomes_dos_itens_para_resposta)}. Em breve entraremos em contato para confirmar."

        except Exception as e:
            print(f"ERRO ao finalizar pedido: {e}")
            return "❌ Ocorreu um erro ao finalizar seu pedido. Tente novamente."
        
    def _extrair_quantidade_e_item(self, mensagem, cardapio_map_por_nome):
        original_mensagem = mensagem.lower().strip()
        temp_mensagem = original_mensagem
        itens_detectados_com_quantidade = []

        print(f"DEBUG: _extrair_quantidade_e_item - Mensagem original: '{original_mensagem}'")

        sorted_cardapio_names = sorted(cardapio_map_por_nome.keys(), key=len, reverse=True)

        for nome_produto_cardapio in sorted_cardapio_names:
            item_cardapio_data = cardapio_map_por_nome[nome_produto_cardapio]

            if nome_produto_cardapio in temp_mensagem or \
               fuzz.token_set_ratio(temp_mensagem, nome_produto_cardapio) >= 75:

                print(f"DEBUG: Item '{nome_produto_cardapio}' (do cardápio) detectado potencialmente em '{temp_mensagem}'.")

                quantidade = 1 

                item_pos = temp_mensagem.find(nome_produto_cardapio)

                start_index = max(0, item_pos - 20)
                end_index = min(len(temp_mensagem), item_pos + len(nome_produto_cardapio) + 20)
                search_window = temp_mensagem[start_index:end_index]

                print(f"DEBUG: Janela de busca para quantidade: '{search_window}'")

                # AQUI É ONDE ELE USA self.quantidade_pattern
                qtd_match = re.search(self.quantidade_pattern, search_window) # <--- O ERRO ESTÁ RELACIONADO A ESSE ACESSO

                if qtd_match:
                    if qtd_match.group(1): 
                        try:
                            quantidade = int(qtd_match.group(1))
                            print(f"DEBUG: Quantidade (dígito) detectada: {quantidade}")
                        except ValueError:
                            pass
                    elif qtd_match.group(2): 
                        quantidade_str = qtd_match.group(2)
                        quantidade = self.numero_para_digito.get(quantidade_str, 1)
                        print(f"DEBUG: Quantidade (palavra) detectada: {quantidade_str} -> {quantidade}")

                itens_detectados_com_quantidade.append({
                    "nome_cardapio": item_cardapio_data['nome'],
                    "item_completo_cardapio": item_cardapio_data,
                    "quantidade": quantidade
                })

                temp_mensagem = temp_mensagem.replace(nome_produto_cardapio, "", 1).strip()
                print(f"DEBUG: Mensagem após remover item '{nome_produto_cardapio}': '{temp_mensagem}'")

                if qtd_match:
                    matched_qty_string = qtd_match.group(0) 
                    temp_mensagem = temp_mensagem.replace(matched_qty_string, "", 1).strip()
                    print(f"DEBUG: Mensagem após remover quantidade '{matched_qty_string}': '{temp_mensagem}'")

        return itens_detectados_com_quantidade

    def _registrar_pedido(self, usuario_id, mensagem, pedido_em_aberto_doc, cardapio_data, pedidos_em_aberto_collection):
        try:
            itens_para_adicionar_ao_banco = []
            resposta_itens_adicionados_ao_usuario = [] # Para a mensagem de resposta ao usuário

            # Mapeia o cardápio por nome (lower case) para fácil acesso
            cardapio_map_por_nome = {item['nome'].lower(): item for item in cardapio_data if 'nome' in item}

            # Usa a nova função para extrair itens com suas quantidades
            itens_encontrados = self._extrair_quantidade_e_item(mensagem, cardapio_map_por_nome)

            if not itens_encontrados:
                print(f"DEBUG Registrar Pedido: Nenhum item do cardápio detectado na mensagem: '{mensagem}'")
                return ("Não consegui identificar os itens do seu pedido. "
                        "Por favor, diga exatamente o que deseja pedir, "
                        "por exemplo: 'quero um sanduíche natural e um suco'.")

            for item_info in itens_encontrados:
                item_cardapio = item_info["item_completo_cardapio"]
                quantidade = item_info["quantidade"]

                item_formatado = {
                    "_id": ObjectId(), 
                    "nome": item_cardapio['nome'],
                    "preco": item_cardapio['preco'],
                    "quantidade": quantidade
                }
                itens_para_adicionar_ao_banco.append(item_formatado)
                resposta_itens_adicionados_ao_usuario.append(f"{quantidade}x {item_cardapio['nome']}")


            if pedido_em_aberto_doc:
                itens_existentes = pedido_em_aberto_doc.get("itens", [])
                itens_existentes_map = {item['nome'].lower(): item for item in itens_existentes}

                for novo_item_obj in itens_para_adicionar_ao_banco:
                    if novo_item_obj['nome'].lower() in itens_existentes_map:
                        # Item já existe, atualiza a quantidade. Você pode somar ou substituir.
                        # Somando as quantidades se o item já está no pedido:
                        itens_existentes_map[novo_item_obj['nome'].lower()]['quantidade'] += novo_item_obj['quantidade']
                    else:
                        # Novo item, adiciona à lista
                        itens_existentes.append(novo_item_obj)
                
                pedidos_em_aberto_collection.update_one(
                    {"_id": pedido_em_aberto_doc["_id"]},
                    {"$set": {"itens": itens_existentes, "data_atualizacao": datetime.utcnow()}}
                )
                print(f"DEBUG Registrar Pedido: Pedido em aberto atualizado para usuario_id: {usuario_id}, itens: {itens_existentes}")
            else:
                pedidos_em_aberto_collection.insert_one(
                    {"usuario_id": usuario_id, "itens": itens_para_adicionar_ao_banco, "data_inicio": datetime.utcnow()}
                )
                print(f"DEBUG Registrar Pedido: Novo pedido em aberto criado para usuario_id: {usuario_id}, itens: {itens_para_adicionar_ao_banco}")
            
            return f"✅ Adicionei ao seu pedido: {', '.join(resposta_itens_adicionados_ao_usuario)}. Deseja pedir mais alguma coisa?"

        except Exception as e:
            print(f"ERRO ao registrar pedido: {str(e)}")
            return "❌ Ocorreu um erro ao processar seu pedido. Tente novamente."
                
    def _intencao_consultar_pedidos(self, mensagem):
        padroes = [
            "meus pedidos", "meu histórico de pedidos", "pedidos anteriores",
            "o que eu já pedi", "histórico de pedidos", "consultar pedidos",
            "ver meus pedidos", "lista de pedidos", "qual meu histórico de pedidos", "pedidos feitos"
        ]
        return self._mensagem_similar(mensagem, padroes, limiar=75)

    def _consultar_pedidos(self, usuario_id, pedidos_list):
        try:
            usuario_pedidos = pedidos_list

            if not usuario_pedidos:
                print(f"DEBUG Consultar Pedidos: Nenhum pedido finalizado encontrado para usuario_id: {usuario_id}")
                return "Você ainda não fez nenhum pedido."

            resposta = "Seu histórico de pedidos:\n\n"
            for pedido in usuario_pedidos:
                data_obj = pedido.get('data', datetime.utcnow()) 
                
                # Garante que data_obj é um objeto datetime aware (com timezone)
                if isinstance(data_obj, datetime) and data_obj.tzinfo is None:
                    # Se for naive (sem timezone), assume que é UTC (como é salvo)
                    data_obj = pytz.utc.localize(data_obj)
                
                # Converte para o fuso horário de São Paulo
                data_local = data_obj.astimezone(self.timezone_sp)
                
                # Formata a data e hora em português
                data_formatada = format_datetime(data_local, format='short', locale='pt_BR')
                
                # --- MUDANÇA AQUI: EXTRAIR NOME E QUANTIDADE DOS ITENS ---
                itens_para_exibir = []
                # Garante que 'itens' é uma lista e contém dicionários antes de iterar
                if isinstance(pedido.get('itens'), list):
                    for item in pedido['itens']:
                        if isinstance(item, dict) and 'nome' in item and 'quantidade' in item:
                            itens_para_exibir.append(f"{item['quantidade']}x {item['nome']}")
                        elif isinstance(item, str): # Tratamento para dados antigos/inconsistentes
                            itens_para_exibir.append(item)
                        else:
                            print(f"AVISO: Item de pedido mal formatado no histórico: {item}")
                            itens_para_exibir.append("Item Desconhecido")
                else:
                    print(f"AVISO: Campo 'itens' do pedido não é uma lista: {pedido.get('itens')}")
                    itens_para_exibir.append("Itens indisponíveis")

                itens_str = ", ".join(itens_para_exibir)
                # --- FIM DA MUDANÇA ---
                
                status_str = pedido.get('status', 'desconhecido')
                resposta += f"📅 {data_formatada}: {itens_str} (Status: {status_str})\n"
            print(f"DEBUG Consultar Pedidos: Retornando histórico para usuario_id: {usuario_id}")
            return resposta.strip()

        except Exception as e:
            print(f"ERRO ao consultar pedidos: {e}")
            return "Ocorreu um erro ao consultar seu histórico de pedidos. Tente novamente mais tarde."

chat_service = ChatService()