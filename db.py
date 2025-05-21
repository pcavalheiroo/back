from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")

# Banco de dados
cantina_db = client["cantina_escolar"]
usuarios_db = client["usuarios_escolar"]
visitantes_db = client["usuarios_visitantes"]

# Colecoes
cardapio_collection = cantina_db["cardapio"]
pedidos_collection = cantina_db["pedidos"]
usuarios_collection = usuarios_db["usuarios"]
visitantes_collection = visitantes_db["visitas"]