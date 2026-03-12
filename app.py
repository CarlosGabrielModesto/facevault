"""
app.py — Application Factory do FaceVault.
"""

import os
import logging
from flask import Flask, redirect, url_for
from flask_login import LoginManager

from config import config
from models import db, User


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
    os.makedirs(app.config['CAPTURED_IMAGES_DIR'], exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Registra todos os blueprints
    from routes.auth    import auth_bp
    from routes.tasks   import tasks_bp
    from routes.admin   import admin_bp
    from routes.profile import profile_bp
    from routes.setup   import setup_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(setup_bp)

    with app.app_context():
        db.create_all()
        # Migração automática: adiciona coluna 'tema' se não existir
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE user ADD COLUMN tema VARCHAR(20) DEFAULT 'vault' NOT NULL"
                ))
                conn.commit()
        except Exception:
            pass  # Coluna já existe — ignora

    # ── First-Run Wizard ──────────────────────────────────────
    # Se não existir nenhum usuário, redireciona automaticamente para o setup
    @app.before_request
    def check_first_run():
        from flask import request as req
        # Permite acesso ao setup e aos estáticos sem redirecionamento
        if req.endpoint in ('setup.setup', 'setup.setup_submit',
                            'static', None):
            return
        # Redireciona para o wizard se o banco estiver vazio
        if not db.session.query(User.id).first():
            return redirect(url_for('setup.setup'))

    return app


if __name__ == '__main__':
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)
    app.run(host='0.0.0.0', port=5000, debug=(env == 'development'))
