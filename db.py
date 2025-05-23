from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URL"))
db = client["polichat"]

# Coleções que o models.py espera
cardapio_collection = db["cardapio"]
usuarios_collection = db["usuarios"]
visitantes_collection = db["visitantes"]
