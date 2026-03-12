"""
face_service.py — Reconhecimento facial com OpenCV puro (LBPH).
Compatível com Python 3.14+. Sem TensorFlow, sem dlib, sem compilação.

Pipeline:
  1. Detecção   → Haar Cascade com parâmetros rígidos (rejeita mãos/objetos)
  2. Validação  → garante proporção e tamanho mínimo do rosto detectado
  3. Recorte    → região do rosto isolada e normalizada
  4. Comparação → LBPH Face Recognizer (algoritmo real de reconhecimento facial)

Por que LBPH em vez de pixel embedding:
  - Pixel embedding compara textura bruta → qualquer objeto similar passa
  - LBPH analisa padrões locais de intensidade → específico para rostos humanos
  - É o algoritmo de reconhecimento facial padrão do OpenCV
"""

import os
import base64
import logging
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from flask import current_app

logger = logging.getLogger(__name__)

# ── Configurações ──────────────────────────────────────────────────────────

FACE_SIZE = (200, 200)        # LBPH funciona melhor com imagens maiores

# Threshold de confiança do LBPH:
#   - LBPH retorna "distância" (menor = mais parecido, 0 = idêntico)
#   - Abaixo de 70 → mesma pessoa (match seguro)
#   - Entre 70-100 → zona de incerteza
#   - Acima de 100 → pessoa diferente
# Usamos 75 como limite — conservador mas funcional para demo
LBPH_THRESHOLD = 75.0

CROP_MARGIN       = 0.20
HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

# ── Detector (carregado uma vez na inicialização) ──────────────────────────

def _load_detector() -> cv2.CascadeClassifier:
    detector = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    if detector.empty():
        raise RuntimeError(f'Haar Cascade não encontrado: {HAAR_CASCADE_PATH}')
    logger.info('Haar Cascade carregado com sucesso.')
    return detector

_detector = _load_detector()


# ── Utilitários ────────────────────────────────────────────────────────────

def base64_to_numpy(base64_str: str) -> np.ndarray:
    """Converte string base64 da webcam em array NumPy BGR."""
    try:
        raw_bytes = base64.b64decode(base64_str.split(',')[1])
        np_array  = np.frombuffer(raw_bytes, np.uint8)
        image     = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('Imagem inválida ou corrompida.')
        return image
    except Exception as e:
        logger.error(f'Erro base64_to_numpy: {e}')
        raise ValueError(f'Imagem inválida: {e}')


def save_face_image(image: np.ndarray, email: str) -> str:
    """Salva a imagem original no disco. Retorna caminho absoluto normalizado."""
    email_local, email_domain = email.split('@')
    user_dir = os.path.join(
        current_app.config['CAPTURED_IMAGES_DIR'],
        email_domain, email_local
    )
    os.makedirs(user_dir, exist_ok=True)

    filename = f"face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.normpath(os.path.join(user_dir, filename))

    success = cv2.imwrite(filepath, image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success:
        raise RuntimeError(f'Falha ao salvar imagem em: {filepath}')

    logger.info(f'Imagem de referência salva: {filepath}')
    return filepath


# ── Detecção de rosto ──────────────────────────────────────────────────────

def _detect_face_region(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Detecta o rosto humano na imagem com parâmetros rígidos.

    Diferença crítica em relação à versão anterior:
      - minNeighbors=6 (era 3-4): exige muito mais confirmações antes de
        aceitar uma detecção — rejeita mãos, objetos e falsos positivos
      - minSize=(100,100): rejeita detecções pequenas/irrelevantes
      - Validação de proporção: rosto humano tem proporção próxima de 1:1

    Retorna None se não houver rosto humano claro na imagem.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # CLAHE é melhor que equalizeHist para preservar detalhes locais
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray  = clahe.apply(gray)

    # Parâmetros rígidos — evita falsos positivos (mãos, objetos, etc.)
    faces = _detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,      # era 3-4, agora muito mais restritivo
        minSize=(100, 100),  # rejeita detecções pequenas
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    if len(faces) == 0:
        logger.warning('Nenhum rosto detectado (parâmetros rígidos).')
        return None

    # Pega o maior rosto detectado
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    # Validação de proporção: rosto humano deve ser aproximadamente quadrado
    # Rejeita detecções muito alongadas (altura/largura fora de 0.7 a 1.4)
    aspect_ratio = h / w
    if not (0.7 <= aspect_ratio <= 1.4):
        logger.warning(f'Detecção rejeitada: proporção inválida ({aspect_ratio:.2f})')
        return None

    # Recorte com margem
    margin_x = int(w * CROP_MARGIN)
    margin_y = int(h * CROP_MARGIN)
    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)
    x2 = min(image.shape[1], x + w + margin_x)
    y2 = min(image.shape[0], y + h + margin_y)

    face_crop    = gray[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, FACE_SIZE, interpolation=cv2.INTER_AREA)

    return face_resized


# ── API pública ────────────────────────────────────────────────────────────

def detect_and_validate_face(image: np.ndarray) -> bool:
    """Retorna True apenas se um rosto humano claro for detectado."""
    return _detect_face_region(image) is not None


def verify_faces(live_image: np.ndarray, reference_path: str) -> tuple[bool, float]:
    """
    Compara o rosto ao vivo com a imagem de referência usando LBPH.

    LBPH (Local Binary Pattern Histogram) é um algoritmo real de
    reconhecimento facial — analisa padrões locais de textura da pele,
    muito mais específico do que comparação de pixels brutos.

    Retorna (is_match, similarity_0_to_1):
      - is_match: True se a distância LBPH for menor que LBPH_THRESHOLD
      - similarity: float 0-1 convertido da distância LBPH para exibição
    """
    try:
        reference_path = os.path.normpath(reference_path)

        # Verifica existência do arquivo com diagnóstico detalhado
        if not os.path.isfile(reference_path):
            dir_path = os.path.dirname(reference_path)
            arquivos = os.listdir(dir_path) if os.path.isdir(dir_path) else 'diretório não existe'
            logger.error(f'Arquivo de referência não encontrado: "{reference_path}"')
            logger.error(f'Arquivos no diretório: {arquivos}')
            return False, 0.0

        # Carrega a imagem de referência do cadastro
        ref_image = cv2.imread(reference_path)
        if ref_image is None:
            logger.error(f'cv2.imread falhou para: {reference_path}')
            return False, 0.0

        # Detecta e recorta os rostos
        live_face = _detect_face_region(live_image)
        ref_face  = _detect_face_region(ref_image)

        # Rejeita imediatamente se não houver rosto em qualquer uma das imagens
        if live_face is None:
            logger.warning('REJEITADO: nenhum rosto detectado na imagem ao vivo.')
            return False, 0.0

        if ref_face is None:
            logger.warning('REJEITADO: nenhum rosto na imagem de referência.')
            return False, 0.0

        # ── LBPH Face Recognizer ──────────────────────────────────────────
        # Treina com a imagem de referência (label=0 para o usuário)
        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,        # raio do padrão LBP
            neighbors=8,     # pontos vizinhos
            grid_x=8,        # grade horizontal para histograma
            grid_y=8         # grade vertical para histograma
        )
        recognizer.train([ref_face], np.array([0]))

        # Prediz: retorna (label_previsto, distância)
        # distância menor = mais parecido (0 = idêntico)
        label, confidence = recognizer.predict(live_face)

        # Converte distância LBPH para score 0-1 para exibição
        # distância 0   → similarity 1.0 (idêntico)
        # distância 75  → similarity 0.5 (limiar)
        # distância 150 → similarity 0.0 (completamente diferente)
        similarity = max(0.0, 1.0 - (confidence / 150.0))
        is_match   = confidence < LBPH_THRESHOLD

        # Log detalhado visível no terminal
        logger.info('┌─ Verificação LBPH ───────────────────────')
        logger.info(f'│  Distância LBPH : {confidence:.2f}')
        logger.info(f'│  Threshold      : {LBPH_THRESHOLD}')
        logger.info(f'│  Similarity     : {similarity:.4f}')
        logger.info(f'│  Resultado      : {"✓ MATCH" if is_match else "✗ REJEITADO"}')
        logger.info('└──────────────────────────────────────────')

        return is_match, similarity

    except cv2.error as e:
        logger.error(f'Erro OpenCV em verify_faces: {e}', exc_info=True)
        return False, 0.0
    except Exception as e:
        logger.error(f'Erro em verify_faces: {e}', exc_info=True)
        return False, 0.0


def analyze_face_quality(image: np.ndarray) -> dict:
    """Analisa qualidade básica da imagem para feedback ao usuário."""
    try:
        hsv        = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        brightness = float(np.mean(hsv[:, :, 2]))
        label = 'baixo' if brightness < 60 else ('alto' if brightness > 180 else 'adequado')
        return {
            'face_detected':    _detect_face_region(image) is not None,
            'brightness':       label,
            'brightness_value': round(brightness, 1),
        }
    except Exception as e:
        logger.warning(f'analyze_face_quality falhou: {e}')
        return {}
