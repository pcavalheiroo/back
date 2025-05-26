# db/connection.py
from pymongo import MongoClient, ASCENDING
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.client = MongoClient(
            os.getenv("MONGODB_URL"),
            server_api=ServerApi('1'),
            connectTimeoutMS=5000,
            socketTimeoutMS=30000
        )
        self.db = self.client["polichat"]
        self._create_indexes()
        
    def _create_indexes(self):
        self.db.mensagens.create_index([("usuario_id", ASCENDING), ("data", ASCENDING)])
        self.db.usuarios.create_index("email", unique=True)

# Exporta a instância do banco de dados
database = Database().db