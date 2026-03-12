"""
routes/setup.py — First-Run Wizard do FaceVault.

Cria o primeiro administrador do sistema de forma visual e segura.
Inspirado em WordPress, Gitea e Nextcloud.

Regra de segurança:
  - Acessível APENAS se não existir nenhum usuário no banco
  - Após o primeiro admin ser criado, a rota retorna 404 permanentemente
  - O admin criado aqui tem is_admin=True automaticamente
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from models import db, User
from services import base64_to_numpy, save_face_image, detect_and_validate_face

setup_bp = Blueprint('setup', __name__)


def _system_has_users() -> bool:
    """Retorna True se já existe pelo menos um usuário no banco."""
    return db.session.query(User.id).first() is not None


@setup_bp.route('/setup', methods=['GET'])
def setup():
    """
    Exibe o wizard de configuração inicial.
    Se já existir algum usuário, retorna 404 — setup nunca mais é acessível.
    """
    # Bloqueia acesso após o primeiro usuário ser criado
    if _system_has_users():
        abort(404)

    return render_template('setup.html')


@setup_bp.route('/setup', methods=['POST'])
def setup_submit():
    """
    Endpoint JSON que finaliza o setup criando o primeiro admin.
    Recebe os dados do formulário + imagem facial via JavaScript.
    """
    # Dupla verificação: bloqueia se já existe usuário (evita race condition)
    if _system_has_users():
        return jsonify({'status': 'failure', 'message': 'Setup já foi concluído.'})

    try:
        data = request.get_json(force=True)

        # Valida campos obrigatórios presentes no payload
        required = ['nome', 'sobrenome', 'email', 'cpf', 'celular',
                    'data_nascimento', 'genero', 'face_data']
        for field in required:
            if not data.get(field):
                return jsonify({'status': 'failure',
                                'message': f'Campo obrigatório ausente: {field}'})

        # Verifica se o rosto está presente e válido na imagem
        face_image = base64_to_numpy(data['face_data'])
        if not detect_and_validate_face(face_image):
            return jsonify({'status': 'failure',
                            'message': 'Nenhum rosto detectado. Posicione seu rosto com boa iluminação.'})

        # Converte a data de nascimento
        try:
            birth_date = datetime.strptime(data['data_nascimento'], '%d/%m/%Y').date()
        except ValueError:
            return jsonify({'status': 'failure', 'message': 'Data inválida. Use dd/mm/aaaa.'})

        # Salva a imagem facial como referência permanente
        face_path = save_face_image(face_image, data['email'])

        # Cria o primeiro usuário com privilégio de administrador
        admin = User(
            nome=data['nome'],
            sobrenome=data['sobrenome'],
            email=data['email'],
            cpf=data['cpf'],
            celular=data['celular'],
            data_nascimento=birth_date,
            genero=data['genero'],
            face_image_path=face_path,
            is_admin=True,    # Primeiro usuário é sempre admin
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()

        return jsonify({'status': 'success',
                        'message': 'Administrador criado! Redirecionando para o login...'})

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Erro no setup: {e}')
        return jsonify({'status': 'failure', 'message': 'Erro interno. Tente novamente.'})
