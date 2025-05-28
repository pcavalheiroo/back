import bcrypt

# A senha que você usará para o administrador (a mesma que você digitará no frontend)
senha_texto_puro = "admin123" 

# Gerar um salt e o hash da senha
senha_hash_bytes = bcrypt.hashpw(senha_texto_puro.encode('utf-8'), bcrypt.gensalt())

# Decodificar o hash para string para salvar no MongoDB
senha_hash_str = senha_hash_bytes.decode('utf-8')

print(f"Senha original: {senha_texto_puro}")
print(f"Hash bcrypt (COPIE ESTE COM CUIDADO): {senha_hash_str}")

# Teste de verificação (opcional, apenas para confirmar que o hash funciona)
if bcrypt.checkpw(senha_texto_puro.encode('utf-8'), senha_hash_bytes):
    print("Teste de verificação: OK! O hash funciona.")
else:
    print("Teste de verificação: FALHOU! Algo deu errado com o hash.")