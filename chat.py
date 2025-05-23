from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from models import listar_cardapio, buscar_item_cardapio, salvar_pedido, obter_pedidos
import os
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis do .env

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.4,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1"
)


def chat(usuario_id, mensagem):
    if "cardapio" in mensagem.lower():
        itens = listar_cardapio()
        return "\n".join([f"{i['nome']} - R$ {i['preco']}" for i in itens])

    elif "explica" in mensagem.lower() or "o que tem" in mensagem.lower():
        nome = mensagem.split("explica")[-1].strip()
        item = buscar_item_cardapio(nome)
        if item:
            return f"{item['nome']} custa R$ {item['preco']} e faz parte da categoria {item['categoria']}."
        return "Não encontrei esse item no cardápio."

    elif "quero" in mensagem.lower() or "pedido" in mensagem.lower():
        salvar_pedido(usuario_id, mensagem)
        return f"Pedido registrado: {mensagem}"

    elif "meu pedido" in mensagem.lower():
        pedidos = obter_pedidos(usuario_id)
        return "\n".join(pedidos) if pedidos else "Você ainda não fez pedidos."

    else:
        system_message = SystemMessage(content="Você é um assistente da cantina escolar. Ajude os clientes com dúvidas sobre o cardápio e pedidos.")
        messages = [system_message, HumanMessage(content=mensagem)]
        resposta = llm.invoke(messages).content
        return resposta

