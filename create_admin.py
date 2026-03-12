"""
create_admin.py — Script para criar o usuário administrador do FaceVault.

Execute UMA VEZ após a primeira instalação:
    python create_admin.py

O admin usa a mesma autenticação facial dos usuários comuns.
Após criar, faça o cadastro normal e marque como admin via este script.
"""

from app import create_app
from models import db, User
from datetime import date
import os

app = create_app('development')

with app.app_context():
    # Verifica se já existe um admin
    existing = User.query.filter_by(is_admin=True).first()
    if existing:
        print(f"Admin já existe: {existing.nome_completo} ({existing.email})")
        print("Para redefinir, delete o banco em instance/facevault.db e execute novamente.")
    else:
        print("=== Criação do Usuário Administrador ===")
        print("O admin usará autenticação facial — cadastre via /register e depois")
        print("execute este script para promovê-lo a administrador.\n")

        email = input("E-mail do usuário a promover a admin: ").strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            print(f"Usuário '{email}' não encontrado.")
            print("Cadastre o usuário primeiro em /register e depois execute este script.")
        else:
            user.is_admin = True
            db.session.commit()
            print(f"\n✅ {user.nome_completo} agora é administrador!")
            print(f"Acesse o painel em: http://localhost:5000/admin")
