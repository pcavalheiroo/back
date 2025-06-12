
# ⚙️ Chatbot Poliedro — Back-end

API RESTful desenvolvida com Node.js e Express para gerenciamento de usuários, pedidos e cardápio de uma cantina escolar, com autenticação segura via JWT e integração com MongoDB.

🔗 Repositório do Front-end: [chatbot-poliedro](https://github.com/pcavalheiroo/chatbot-poliedro)

## 📦 Tecnologias utilizadas

- [Node.js](https://nodejs.org/)
- [Express](https://expressjs.com/)
- [MongoDB + Mongoose](https://mongoosejs.com/)
- [JWT (JSON Web Tokens)](https://jwt.io/)
- [Dotenv](https://www.npmjs.com/package/dotenv)
- [Bcrypt](https://www.npmjs.com/package/bcrypt)

## 🧱 Estrutura de Pastas

```
back/
├── db/              # Lógicas das rotas
    └── models/      # Modelos do MongoDB
├── services/        # Serviços da aplicação
├── app.py           # Ponto de execução e rotas
└── .env             # Variáveis de ambiente
```

## 🚀 Funcionalidades

- Autenticação com token JWT
- Cadastro e login de usuários
- Consulta e gerenciamento de pedidos
- Consulta e atualização do cardápio
- Middleware de segurança para proteger rotas

## 🛠️ Instalação e Execução

```bash
# Clonar o repositório
git clone https://github.com/pcavalheiroo/back

# Instalar dependências
npm install

# Criar .env com variáveis:
# MONGODB_URI=...
# JWT_SECRET=...

# Rodar localmente
npm run dev
```

## 🔐 Segurança

- Senhas criptografadas com bcrypt
- Token JWT com expiração
- Middlewares de autenticação para rotas protegidas

## 📬 API Endpoints

```
POST   /auth/login           → Login do usuário
POST   /auth/register        → Registro do usuário
GET    /cardapio             → Buscar itens do cardápio
POST   /pedidos              → Criar novo pedido
GET    /pedidos/:userId      → Ver pedidos do usuário
...
```

---

## 👨‍💻 Autor

Pedro Cavalheiro  
📧 pdrocavalheiro@gmail.com 
🔗 [github.com/pcavalheiroo](https://github.com/pcavalheiroo)
