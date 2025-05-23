import cv2
import time
import os

def capture_image(aluno_id: str | None = None) -> str | None:
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Erro: Não foi possível acessar a câmera.")
        return None

    # Define resolução (opcional)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1980)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    ret, frame = cap.read()
    cap.release()

    if ret:
        timestamp = int(time.time())
        nome_base = f"captura_{aluno_id or timestamp}.jpg"

        output_dir = "imagens"
        os.makedirs(output_dir, exist_ok=True)

        image_filename = os.path.join(output_dir, nome_base)
        cv2.imwrite(image_filename, frame)
        print(f"Imagem salva como {image_filename}")
        return image_filename
    else:
        print("Erro ao capturar imagem.")
        return None
