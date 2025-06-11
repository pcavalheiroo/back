import pymongo
from dotenv import load_dotenv
import os

load_dotenv()

def apagar_todos_os_dados(uri, nome_banco, nome_collection):
    # Conecta ao MongoDB
    cliente = pymongo.MongoClient(uri)
    db = cliente[nome_banco]
    collection = db[nome_collection]
    
    # Apaga todos os documentos da collection
    resultado = collection.delete_many({})
    print(f"{resultado.deleted_count} documentos apagados da collection '{nome_collection}'.")

# Exemplo de uso:
if __name__ == "__main__":
    # Substitua pelos seus dados de conexão
    uri = os.getenv("MONGODB_URL")
    nome_banco = "polichat"
    nome_collection = "mensagens"
    
    apagar_todos_os_dados(uri, nome_banco, nome_collection)