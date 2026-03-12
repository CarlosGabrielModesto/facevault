"""
routes/auth.py — Blueprint de autenticação do FaceVault.
Login em 3 etapas: CPF → Celular → Reconhecimento facial (LBPH)
"""

import os
from datetime import datetime

from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, jsonify, current_app)
from flask_login import login_user, logout_user, login_required

from models import db, User
from forms import RegisterForm
from services import base64_to_numpy, save_face_image, detect_and_validate_face, verify_faces

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('E-mail já cadastrado.', 'danger')
            return redirect(url_for('auth.login'))
        if User.query.filter_by(cpf=form.cpf.data).first():
            flash('CPF já cadastrado.', 'danger')
            return render_template('register.html', form=form)
        return render_template('register_capture.html',
                               email=form.email.data,
                               nome=form.nome.data,
                               sobrenome=form.sobrenome.data,
                               cpf=form.cpf.data,
                               celular=form.celular.data,
                               data_nascimento=form.data_nascimento.data,
                               genero=form.genero.data)
    return render_template('register.html', form=form)


@auth_bp.route('/register_capture', methods=['POST'])
def register_capture():
    """
    Finaliza o cadastro salvando a imagem facial de referência.
    Exige que um rosto seja detectado — rejeita imagens sem rosto.
    """
    try:
        data       = request.get_json(force=True)
        face_image = base64_to_numpy(data['face_data'])

        # Exige rosto detectável — sem rosto, sem cadastro
        if not detect_and_validate_face(face_image):
            return jsonify({
                'status': 'failure',
                'message': 'Nenhum rosto detectado. Centralize seu rosto na câmera com boa iluminação.'
            })

        try:
            birth_date = datetime.strptime(data['data_nascimento'], '%d/%m/%Y').date()
        except ValueError:
            return jsonify({'status': 'failure', 'message': 'Data inválida. Use dd/mm/aaaa.'})

        face_path = save_face_image(face_image, data['email'])

        is_first_user = User.query.count() == 0

        new_user = User(
            nome=data['nome'],
            sobrenome=data['sobrenome'],
            email=data['email'],
            cpf=data['cpf'],
            celular=data['celular'],
            data_nascimento=birth_date,
            genero=data['genero'],
            face_image_path=face_path,
            is_admin=is_first_user
        )
        db.session.add(new_user)
        db.session.commit()

        msg = ('Cadastro realizado! Você é o administrador do sistema.'
               if is_first_user else 'Cadastro realizado com sucesso!')
        return jsonify({'status': 'success', 'message': msg})

    except Exception as e:
        current_app.logger.error(f'Erro em register_capture: {e}')
        return jsonify({'status': 'failure', 'message': 'Erro interno. Tente novamente.'})


@auth_bp.route('/verify_cpf', methods=['POST'])
def verify_cpf():
    """Etapa 1: verifica se o CPF existe e se a conta está ativa."""
    cpf  = request.get_json(force=True).get('cpf', '').strip()
    user = User.query.filter_by(cpf=cpf).first()

    if not user:
        return jsonify({'status': 'failure',
                        'message': 'CPF não encontrado. Cadastre-se primeiro.'})

    if not user.is_active:
        return jsonify({'status': 'failure',
                        'message': 'Conta desativada. Entre em contato com o administrador.'})

    return jsonify({'status': 'success'})


@auth_bp.route('/verify_celular', methods=['POST'])
def verify_celular():
    """Etapa 2: verifica se o celular corresponde ao CPF informado."""
    data = request.get_json(force=True)
    user = User.query.filter_by(
        cpf=data.get('cpf', '').strip(),
        celular=data.get('celular', '').strip()
    ).first()

    if user:
        return jsonify({'status': 'success'})

    return jsonify({'status': 'failure',
                    'message': 'Celular não corresponde ao CPF informado.'})


@auth_bp.route('/login_capture', methods=['POST'])
def login_capture():
    """
    Etapa 3: reconhecimento facial via LBPH.

    Fluxo de segurança:
      1. Busca o usuário pelo CPF da sessão
      2. Verifica se a conta está ativa
      3. Verifica se o arquivo de referência existe no disco
      4. Exige que um rosto seja detectado na imagem ao vivo
      5. Compara com LBPH — rejeita se distância >= LBPH_THRESHOLD
    """
    try:
        data       = request.get_json(force=True)
        live_image = base64_to_numpy(data['face_data'])
        cpf        = data.get('cpf', '').strip()

        # ── Busca e validações do usuário ─────────────────────────────────
        user = User.query.filter_by(cpf=cpf).first()

        if not user:
            current_app.logger.warning(f'Login: CPF não encontrado — {cpf}')
            return jsonify({'status': 'failure', 'message': 'Usuário não encontrado.'})

        if not user.is_active:
            current_app.logger.warning(f'Login bloqueado: conta inativa — {user.email}')
            return jsonify({'status': 'failure',
                            'message': 'Conta desativada. Contate o administrador.'})

        # Verifica se a imagem de referência existe antes de tentar comparar
        ref_path = os.path.normpath(user.face_image_path)
        if not os.path.isfile(ref_path):
            current_app.logger.error(
                f'Imagem de referência ausente para {user.email}: {ref_path}'
            )
            return jsonify({'status': 'failure',
                            'message': 'Erro na referência facial. Recadastre sua imagem no perfil.'})

        # ── Reconhecimento facial LBPH ────────────────────────────────────
        is_match, similarity = verify_faces(live_image, ref_path)

        if is_match:
            login_user(user, remember=False)
            current_app.logger.info(
                f'✓ Login aprovado: {user.email} | similarity={similarity:.4f}'
            )
            dest = url_for('admin.dashboard') if user.is_admin else url_for('tasks.index')
            return jsonify({'status': 'success', 'redirect': dest})

        # Informa o score no log para facilitar ajuste do threshold
        current_app.logger.warning(
            f'✗ Login negado: {user.email} | similarity={similarity:.4f} '
            f'(precisa >= {1.0 - 75.0/150.0:.2f})'
        )
        return jsonify({
            'status': 'failure',
            'message': 'Rosto não reconhecido. Posicione-se melhor e tente novamente.'
        })

    except Exception as e:
        current_app.logger.error(f'Erro em login_capture: {e}', exc_info=True)
        return jsonify({'status': 'failure',
                        'message': 'Erro no reconhecimento. Tente novamente.'})


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com sucesso.', 'success')
    return redirect(url_for('auth.login'))
