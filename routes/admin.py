"""
routes/admin.py — Painel de administração do FaceVault.

Funcionalidades:
  - Listar todos os usuários com filtro e busca
  - Ativar / desativar contas de usuários
  - Promover / rebaixar administradores
  - Excluir usuários (com proteção contra auto-exclusão)
  - Dashboard com estatísticas do sistema

Acesso restrito a usuários com is_admin=True.
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from models import db, User, Task

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Decorator de proteção de acesso ─────────────────────────

def admin_required(f):
    """
    Decorator que bloqueia acesso a qualquer não-administrador.
    Retorna 403 Forbidden em vez de redirecionar para o login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Rotas do painel ─────────────────────────────────────────

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """
    Página principal do admin: estatísticas gerais do sistema e lista de usuários.
    Suporta busca por nome, e-mail ou CPF via query string ?q=
    """
    # Termo de busca opcional
    q = request.args.get('q', '').strip()

    # Monta a query base excluindo o próprio admin logado (para ações)
    query = User.query.order_by(User.criado_em.desc())

    # Filtra por nome, e-mail ou CPF se houver termo de busca
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                User.nome.ilike(like),
                User.sobrenome.ilike(like),
                User.email.ilike(like),
                User.cpf.ilike(like),
            )
        )

    users = query.all()

    # Estatísticas do sistema para o dashboard de admin
    stats = {
        'total_users':   User.query.count(),
        'active_users':  User.query.filter_by(is_active=True).count(),
        'blocked_users': User.query.filter_by(is_active=False).count(),
        'admin_users':   User.query.filter_by(is_admin=True).count(),
        'total_tasks':   Task.query.count(),
        'done_tasks':    Task.query.filter_by(completed=True).count(),
    }

    return render_template('admin/dashboard.html', users=users, stats=stats, q=q)


@admin_bp.route('/toggle_active/<int:user_id>')
@login_required
@admin_required
def toggle_active(user_id):
    """
    Ativa ou bloqueia a conta de um usuário.
    Impede que o admin bloqueie a própria conta.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Protege o admin de bloquear a si mesmo
    if user.id == current_user.id:
        flash('Você não pode bloquear sua própria conta.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # Inverte o estado atual
    user.is_active = not user.is_active
    db.session.commit()

    action = 'ativada' if user.is_active else 'bloqueada'
    flash(f'Conta de {user.nome_completo} foi {action}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/toggle_admin/<int:user_id>')
@login_required
@admin_required
def toggle_admin(user_id):
    """
    Promove um usuário comum a admin, ou rebaixa um admin a usuário.
    Impede que o admin rebaixe a si mesmo.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Impede auto-rebaixamento
    if user.id == current_user.id:
        flash('Você não pode alterar seu próprio nível de acesso.', 'warning')
        return redirect(url_for('admin.dashboard'))

    user.is_admin = not user.is_admin
    db.session.commit()

    role = 'Administrador' if user.is_admin else 'Usuário'
    flash(f'{user.nome_completo} agora é {role}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    """
    Remove permanentemente um usuário e todas as suas tarefas.
    Impede auto-exclusão do admin logado.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Impede auto-exclusão
    if user.id == current_user.id:
        flash('Você não pode excluir sua própria conta pelo painel admin.', 'warning')
        return redirect(url_for('admin.dashboard'))

    nome = user.nome_completo
    db.session.delete(user)
    db.session.commit()

    flash(f'Usuário {nome} foi removido permanentemente.', 'info')
    return redirect(url_for('admin.dashboard'))
