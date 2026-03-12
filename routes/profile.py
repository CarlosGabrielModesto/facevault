"""
routes/profile.py — Edição de perfil do usuário autenticado.

Permite ao usuário atualizar seus dados pessoais (nome, celular, etc.)
e re-capturar a imagem facial de referência.
"""

import os
from datetime import datetime
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, jsonify, current_app)
from flask_login import login_required, current_user
from models import db, User
from services import base64_to_numpy, save_face_image, detect_and_validate_face

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """Exibe a página de edição de perfil do usuário logado."""
    return render_template('profile.html', user=current_user)


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """
    Atualiza os dados pessoais do usuário (sem alterar CPF ou e-mail —
    campos únicos que servem como identificadores de identidade).
    """
    nome       = request.form.get('nome', '').strip()
    sobrenome  = request.form.get('sobrenome', '').strip()
    celular    = request.form.get('celular', '').strip()
    genero     = request.form.get('genero', '').strip()
    dt_nasc    = request.form.get('data_nascimento', '').strip()

    # Valida campos obrigatórios
    if not all([nome, sobrenome, celular, genero, dt_nasc]):
        flash('Todos os campos são obrigatórios.', 'danger')
        return redirect(url_for('profile.profile'))

    # Converte data de nascimento
    try:
        birth_date = datetime.strptime(dt_nasc, '%d/%m/%Y').date()
    except ValueError:
        flash('Data de nascimento inválida. Use dd/mm/aaaa.', 'danger')
        return redirect(url_for('profile.profile'))

    # Atualiza o usuário no banco
    current_user.nome            = nome
    current_user.sobrenome       = sobrenome
    current_user.celular         = celular
    current_user.genero          = genero
    current_user.data_nascimento = birth_date
    current_user.atualizado_em   = datetime.utcnow()

    db.session.commit()
    flash('Perfil atualizado com sucesso!', 'success')
    return redirect(url_for('profile.profile'))


@profile_bp.route('/profile/update_face', methods=['POST'])
@login_required
def update_face():
    """
    Substitui a imagem facial de referência do usuário.
    Remove a imagem anterior do disco antes de salvar a nova.
    """
    try:
        data = request.get_json(force=True)
        face_image = base64_to_numpy(data['face_data'])

        # Valida se há rosto detectável na nova imagem
        if not detect_and_validate_face(face_image):
            return jsonify({'status': 'failure',
                            'message': 'Nenhum rosto detectado. Tente com melhor iluminação.'})

        # Remove a imagem anterior do disco para economizar espaço
        old_path = current_user.face_image_path
        if old_path and os.path.exists(old_path):
            os.remove(old_path)
            current_app.logger.info(f'Imagem antiga removida: {old_path}')

        # Salva a nova imagem e atualiza o registro
        new_path = save_face_image(face_image, current_user.email)
        current_user.face_image_path = new_path
        current_user.atualizado_em   = datetime.utcnow()
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Imagem facial atualizada com sucesso!'})

    except Exception as e:
        current_app.logger.error(f'Erro ao atualizar face: {e}')
        return jsonify({'status': 'failure', 'message': 'Erro interno. Tente novamente.'})


# Temas disponíveis com nome, descrição e cores de preview
TEMAS = {
    'vault': {
        'nome': 'Vault',
        'desc': 'Verde-esmeralda sobre Slate. Segurança e acesso verificado.',
        'cor1': '#10b981',
        'cor2': '#059669',
        'fundo': '#0f172a',
    },
    'obsidian': {
        'nome': 'Obsidian',
        'desc': 'Azul corporativo profundo. Elegante e sofisticado.',
        'cor1': '#2563eb',
        'cor2': '#0891b2',
        'fundo': '#0b1220',
    },
    'cyber': {
        'nome': 'Cyber',
        'desc': 'Sky Blue vibrante com scanner biométrico animado.',
        'cor1': '#0ea5e9',
        'cor2': '#6366f1',
        'fundo': '#0f172a',
    },
    'terminal': {
        'nome': 'Terminal',
        'desc': 'Zinc + Sky. Visual de software profissional e rígido.',
        'cor1': '#0284c7',
        'cor2': '#38bdf8',
        'fundo': '#09090b',
    },
}


@profile_bp.route('/profile/tema', methods=['POST'])
@login_required
def update_tema():
    """Salva o tema escolhido pelo usuário."""
    tema = request.form.get('tema', 'vault')
    if tema not in TEMAS:
        tema = 'vault'
    current_user.tema = tema
    db.session.commit()
    flash(f'Tema "{TEMAS[tema]["nome"]}" aplicado com sucesso!', 'success')
    return redirect(url_for('profile.profile'))
