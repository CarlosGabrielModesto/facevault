# Exporta as funções públicas do serviço facial para uso nos blueprints
from .face_service import (
    base64_to_numpy,
    save_face_image,
    detect_and_validate_face,
    verify_faces,
    analyze_face_quality,
)
