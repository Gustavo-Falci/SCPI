# BackEnd/capture_camera.py
import cv2
import logging # Adicionado para melhor feedback

logger = logging.getLogger(__name__)

def capture_frame_as_jpeg_bytes() -> bytes | None:
    """
    Captura um frame da câmera e retorna os bytes da imagem codificada em JPEG.

    Returns:
        bytes: Os bytes da imagem JPEG, ou None em caso de erro.
    """
    cap = cv2.VideoCapture(0)  # Ou o índice correto da sua câmera

    if not cap.isOpened():
        logger.error("Erro: Não foi possível acessar a câmera.")
        return None

    # Define resolução (opcional, descomente e ajuste se necessário)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    ret, frame = cap.read()
    cap.release() # Libera a câmera imediatamente após a captura

    if ret and frame is not None:

        try:
            # Codifica o frame capturado para o formato JPEG em memória
            is_success, buffer = cv2.imencode(".jpg", frame)
            
            if is_success:
                logger.info("Frame capturado e codificado para JPEG com sucesso.")
                return buffer.tobytes()
            
            else:
                logger.error("Erro ao codificar frame para JPEG.")
                return None
            
        except Exception as e:
            logger.error(f"Exceção ao codificar frame para JPEG: {e}", exc_info=True)
            return None
    else:
        logger.error("Erro ao capturar frame da câmera.")
        return None

if __name__ == '__main__':
    # Configuração de logging para teste direto
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    
    image_bytes = capture_frame_as_jpeg_bytes()
    if image_bytes:
        print(f"Imagem capturada com sucesso ({len(image_bytes)} bytes).")
        # Para testar, você poderia salvar esses bytes em um arquivo:
        # with open("teste_captura_bytes.jpg", "wb") as f:
        #     f.write(image_bytes)
        # print("Imagem de teste salva como teste_captura_bytes.jpg")
    else:
        print("Falha ao capturar imagem.")