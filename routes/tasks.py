"""
routes/tasks.py — Blueprint de gerenciamento de tarefas do FaceVault.

Todas as rotas exigem autenticação via @login_required.
Cada operação valida a propriedade da tarefa antes de executar
(impede que um usuário acesse tarefas de outro).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from models import db, Task
from forms import TaskForm

# Blueprint de tarefas sem prefixo de URL
tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/')
@login_required
def index():
    """
    Dashboard principal: lista todas as tarefas do usuário autenticado
    ordenadas por prioridade decrescente e depois por data de criação.
    """
    # Filtra apenas as tarefas do usuário logado, mais urgentes primeiro
    tasks = (Task.query
             .filter_by(user_id=current_user.id)
             .order_by(Task.completed.asc(),      # Pendentes antes das concluídas
                       Task.priority.desc(),      # Alta prioridade no topo
                       Task.id.desc())            # Mais recentes primeiro em caso de empate
             .all())

    return render_template('index.html', tasks=tasks)


@tasks_bp.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """
    GET  — Exibe o formulário de criação de tarefa.
    POST — Valida e persiste a nova tarefa vinculada ao usuário logado.
    """
    form = TaskForm()

    if form.validate_on_submit():
        # Cria a tarefa associada ao usuário autenticado
        task = Task(
            title=form.title.data,
            description=form.description.data,
            priority=form.priority.data,
            user_id=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('tasks.index'))

    return render_template('create_task.html', form=form, task=None)


@tasks_bp.route('/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    """
    Carrega a tarefa pelo ID, valida a propriedade e salva as alterações.
    Retorna 404 se a tarefa não existir e 403 se pertencer a outro usuário.
    """
    # Busca a tarefa ou retorna 404 automaticamente
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)

    # Bloqueia acesso a tarefas de outros usuários
    if task.user_id != current_user.id:
        abort(403)

    # Pré-preenche o formulário com os dados atuais da tarefa
    form = TaskForm(obj=task)

    if form.validate_on_submit():
        # Atualiza apenas os campos editáveis
        task.title       = form.title.data
        task.description = form.description.data
        task.priority    = form.priority.data
        db.session.commit()
        flash('Tarefa atualizada com sucesso!', 'success')
        return redirect(url_for('tasks.index'))

    return render_template('create_task.html', form=form, task=task)


@tasks_bp.route('/tasks/toggle/<int:task_id>')
@login_required
def toggle_task(task_id):
    """Alterna o status da tarefa entre pendente ↔ concluída."""
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)

    # Verifica propriedade antes de modificar
    if task.user_id != current_user.id:
        abort(403)

    # Inverte o estado atual de conclusão
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for('tasks.index'))


@tasks_bp.route('/tasks/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    """Remove a tarefa permanentemente após validar a propriedade."""
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)

    # Impede deleção de tarefas de outros usuários
    if task.user_id != current_user.id:
        abort(403)

    db.session.delete(task)
    db.session.commit()
    flash('Tarefa removida.', 'info')
    return redirect(url_for('tasks.index'))


@tasks_bp.route('/tasks/toggle_ajax/<int:task_id>', methods=['POST'])
@login_required
def toggle_task_ajax(task_id):
    """Toggle via AJAX — retorna JSON sem redirecionar."""
    from flask import jsonify
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'not found'}), 404
    if task.user_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    task.completed = not task.completed
    db.session.commit()
    return jsonify({'completed': task.completed, 'task_id': task_id})
