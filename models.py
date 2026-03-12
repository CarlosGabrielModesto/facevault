from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Instância global do SQLAlchemy — inicializada no app factory via db.init_app(app)
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    Modelo de usuário com autenticação facial via OpenCV.

    Campos de controle:
      is_admin   — permite acesso ao painel de administração
      is_active  — conta ativa/inativa (controlada pelo admin)
    """

    id             = db.Column(db.Integer, primary_key=True)
    nome           = db.Column(db.String(150), nullable=False)
    sobrenome      = db.Column(db.String(150), nullable=False)
    email          = db.Column(db.String(150), unique=True, nullable=False)

    # CPF: identificador principal no fluxo de login
    cpf            = db.Column(db.String(11), unique=True, nullable=False)
    celular        = db.Column(db.String(15), nullable=False)
    data_nascimento= db.Column(db.Date, nullable=False)
    genero         = db.Column(db.String(20), nullable=False)

    # Caminho da imagem facial salva no disco — referência para verify_faces()
    face_image_path= db.Column(db.String(300), nullable=False)

    # True = usuário tem acesso ao painel /admin
    is_admin       = db.Column(db.Boolean, default=False, nullable=False)

    # False = conta bloqueada pelo administrador (login negado)
    is_active      = db.Column(db.Boolean, default=True, nullable=False)

    # Tema visual escolhido pelo usuário: vault | obsidian | cyber | terminal
    tema           = db.Column(db.String(20), default='vault', nullable=False)

    criado_em      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em  = db.Column(db.DateTime, default=datetime.utcnow,
                               onupdate=datetime.utcnow, nullable=False)

    # Cascade: remove tarefas ao deletar o usuário
    tasks = db.relationship('Task', backref='owner', lazy=True,
                            cascade='all, delete-orphan')

    # Flask-Login usa get_id() para serializar a sessão
    def get_id(self):
        return str(self.id)

    @property
    def nome_completo(self):
        return f"{self.nome} {self.sobrenome}"

    @property
    def status_label(self):
        """Rótulo textual do status da conta."""
        return 'Ativa' if self.is_active else 'Bloqueada'

    def __repr__(self):
        return f'<User {self.nome_completo} admin={self.is_admin}>'


class Task(db.Model):
    """Tarefa com prioridade, status e vínculo ao usuário dono."""

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)

    # False = pendente | True = concluída
    completed   = db.Column(db.Boolean, default=False, nullable=False)

    # 1=Baixa | 2=Média | 3=Alta
    priority    = db.Column(db.Integer, default=2, nullable=False)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # FK para o usuário dono desta tarefa
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def priority_label(self):
        return {1: 'Baixa', 2: 'Média', 3: 'Alta'}.get(self.priority, 'Média')

    @property
    def priority_color(self):
        return {1: 'low', 2: 'medium', 3: 'high'}.get(self.priority, 'medium')

    def __repr__(self):
        return f'<Task {self.title}>'
