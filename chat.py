from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from models import listar_cardapio, buscar_item_cardapio, salvar_pedido, obter_pedidos, obter_historico_mensagens, extrair_nome_item
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.4,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1"
)

# chat.py
def chat(usuario_id, mensagem):
    mensagem_lower = mensagem.lower()
    
    # Cardápio completo
    if "cardapio" in mensagem_lower or "menu" in mensagem_lower or "opções" in mensagem_lower:
        itens = listar_cardapio()
        if not itens:
            return "No momento não há itens disponíveis no cardápio."
        return "\n".join([f"{i['nome']} - R$ {i['preco']:.2f}" for i in itens])

    # Informações sobre um item
    elif "explica" in mensagem_lower or "o que tem" in mensagem_lower or "sobre" in mensagem_lower:
        nome = extrair_nome_item(mensagem)
        item = buscar_item_cardapio(nome)
        if item:
            return f"ℹ️ {item['nome']}:\n\n• Preço: R$ {item['preco']:.2f}\n• Categoria: {item['categoria']}"
        return "Não encontrei esse item no cardápio. Digite 'cardápio' para ver as opções."

    # Fazer pedido
    elif "quero" in mensagem_lower or "pedido" in mensagem_lower or "pedir" in mensagem_lower:
        nome = extrair_nome_item(mensagem)
        item = buscar_item_cardapio(nome)
        if item:
            salvar_pedido(usuario_id, item['nome'])
            return f"✅ Pedido registrado: {item['nome']}\n\nObrigado pelo seu pedido!"
        return "Desculpe, esse item não está disponível. Digite 'cardápio' para ver as opções."

    # Ver pedidos
    elif "meu pedido" in mensagem_lower or "meus pedidos" in mensagem_lower:
        pedidos = obter_pedidos(usuario_id)
        if pedidos:
            return "📦 Seus pedidos:\n\n• " + "\n• ".join(pedidos)
        return "Você ainda não fez nenhum pedido."

    # Resposta padrão com LLM
    else:
        system_message = SystemMessage(content=(
            "Você é um assistente da cantina escolar chamado PoliChat. "
            "Seja prestativo e amigável. Ajude com:\n"
            "- Cardápio e opções\n"
            "- Informações sobre itens\n"
            "- Registro de pedidos\n"
            "- Histórico de pedidos\n\n"
            "Se não souber a resposta, sugira que o usuário peça o cardápio."
        ))
        
        historico = obter_historico_mensagens(usuario_id)
        messages = [system_message]
        for msg in historico:
            if msg["origem"] == "usuario":
                messages.append(HumanMessage(content=msg["mensagem"]))
            else:
                messages.append(AIMessage(content=msg["mensagem"]))

        messages.append(HumanMessage(content=mensagem))
        resposta = llm.invoke(messages).content
        return resposta