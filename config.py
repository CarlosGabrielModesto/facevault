import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configurações base compartilhadas por todos os ambientes."""

    # Chave secreta para sessões e tokens CSRF — sempre defina via variável de ambiente em produção
    SECRET_KEY = os.environ.get('SECRET_KEY', 'facevault-dev-secret-change-in-production')

    # URI do banco SQLite armazenado na pasta instance/ (excluída do git)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'facevault.db')}"
    )

    # Desativa o sistema de eventos do SQLAlchemy para economizar memória
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Diretório de imagens faciais (excluído do git via .gitignore)
    CAPTURED_IMAGES_DIR = os.path.join(BASE_DIR, 'captured_images')

    # Modelo DeepFace para reconhecimento facial
    # ArcFace = maior precisão | VGG-Face = mais rápido
    DEEPFACE_MODEL = os.environ.get('DEEPFACE_MODEL', 'ArcFace')

    # Métrica de distância entre embeddings faciais
    # cosine = mais precisa para embeddings normalizados
    DEEPFACE_DISTANCE_METRIC = os.environ.get('DEEPFACE_DISTANCE_METRIC', 'cosine')

    # Backend de detecção do rosto na imagem antes da análise
    # opencv = mais rápido | retinaface = mais preciso
    DEEPFACE_DETECTOR = os.environ.get('DEEPFACE_DETECTOR', 'opencv')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
