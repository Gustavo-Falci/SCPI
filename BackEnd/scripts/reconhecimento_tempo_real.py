import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import cv2
import time
import threading
import logging
import os
import requests
import botocore.exceptions
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv, find_dotenv
from core.config import COLLECTION_ID, AWS_REGION
from infra.aws_clientes import rekognition_client

load_dotenv(find_dotenv())
_API_URL = os.getenv("EXPO_PUBLIC_API_URL", "http://localhost:8000")
_SERVICE_TOKEN = os.getenv("CAMERA_SERVICE_TOKEN", "")
_CAMERA_SALA = os.getenv("CAMERA_SALA", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SistemaReconhecimento:
    def __init__(self):
        if not _CAMERA_SALA:
            raise ValueError("CAMERA_SALA não definido. Configure a variável de ambiente antes de iniciar.")

        self.rodando = False
        self.frame_atual = None

        self.INTERVALO_ENVIO_AWS = 1.5
        self.CAM_INDEX = 0

        self.chamada_id_atual = None
        self.presentes_chamada: set = set()

        self.lock = threading.Lock()
        self._aws_pool = ThreadPoolExecutor(max_workers=4)
        self._api_pool = ThreadPoolExecutor(max_workers=2)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def _sincronizar_chamada(self):
        try:
            resp = requests.get(
                f"{_API_URL}/chamadas/aberta/sala/{_CAMERA_SALA}",
                headers={"x-service-token": _SERVICE_TOKEN},
                timeout=5,
            )
            chamada_id = resp.json().get("chamada_id") if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro ao sincronizar chamada: {e}")
            return

        with self.lock:
            if chamada_id != self.chamada_id_atual:
                anteriores = len(self.presentes_chamada)
                self.chamada_id_atual = chamada_id
                self.presentes_chamada.clear()
                if chamada_id:
                    logger.info(f"📋 Nova chamada detectada: {chamada_id} — {anteriores} presentes resetados.")
                else:
                    logger.info(f"📋 Nenhuma chamada aberta em {_CAMERA_SALA} — {anteriores} presentes resetados.")

    def _registrar_presenca(self, external_image_id):
        try:
            resp = requests.post(
                f"{_API_URL}/chamadas/registrar_presenca_camera",
                json={"external_image_id": external_image_id},
                headers={"x-service-token": _SERVICE_TOKEN},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"API retornou {resp.status_code} para {external_image_id}: {resp.text}")
        except Exception as e:
            logger.error(f"Erro ao registrar presença via API: {e}")

    def _enviar_para_aws(self, face_bytes, chamada_id_referencia):
        """Função separada para lidar com a AWS sem travar o OpenCV"""
        try:
            response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=85,
            )

            if not response['FaceMatches']:
                return

            match = response['FaceMatches'][0]
            aluno_external_id = match['Face']['ExternalImageId']

            with self.lock:
                # Evita registrar se a chamada mudou enquanto a AWS processava
                if self.chamada_id_atual != chamada_id_referencia:
                    return
                if aluno_external_id in self.presentes_chamada:
                    return
                self.presentes_chamada.add(aluno_external_id)

            logger.info(f"🎯 Reconhecido: {aluno_external_id}")
            self._api_pool.submit(self._registrar_presenca, aluno_external_id)

        except botocore.exceptions.ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"]["Message"]
            if code == "InvalidParameterException" and "no faces" in msg.lower():
                logger.debug("Haar falso positivo ignorado: sem rosto válido no crop.")
            else:
                logger.error(f"Erro AWS (face individual): {code} - {msg}")
        except Exception as e:
            logger.error(f"Erro AWS (face individual): {e}")

    def _thread_processamento_visual(self):
        ultimo_envio = 0

        while self.rodando:
            try:
                with self.lock:
                    chamada_atual = self.chamada_id_atual
                    frame = self.frame_atual

                if chamada_atual is None:
                    time.sleep(0.5)
                    continue

                if frame is None:
                    time.sleep(0.01)
                    continue

                img_para_processar = frame.copy()
                gray = cv2.cvtColor(img_para_processar, cv2.COLOR_BGR2GRAY)
                rostos_detectados = self.face_cascade.detectMultiScale(gray, 1.1, 5)

                if len(rostos_detectados) == 0:
                    time.sleep(0.03)
                    continue

                agora = time.time()
                if agora - ultimo_envio < self.INTERVALO_ENVIO_AWS:
                    time.sleep(0.03)
                    continue

                ultimo_envio = agora
                with self.lock:
                    chamada_id_captura = self.chamada_id_atual

                h_img, w_img = img_para_processar.shape[:2]
                for (x, y, w, h) in rostos_detectados:
                    margin = int(0.2 * max(w, h))
                    x1 = max(0, x - margin)
                    y1 = max(0, y - margin)
                    x2 = min(w_img, x + w + margin)
                    y2 = min(h_img, y + h + margin)

                    face_crop = img_para_processar[y1:y2, x1:x2]
                    ret, buffer = cv2.imencode('.jpg', face_crop)
                    if not ret:
                        continue
                    face_bytes = buffer.tobytes()

                    self._aws_pool.submit(self._enviar_para_aws, face_bytes, chamada_id_captura)

            except Exception as e:
                logger.error(f"Erro no loop de processamento visual: {e}")
                time.sleep(0.1)

    def iniciar(self):
        self.rodando = True
        cap = None
        t_proc = None
        ultima_sync = 0
        INTERVALO_SYNC = 5

        logger.info(f"🔍 Monitorando chamadas em {_CAMERA_SALA}. Câmera desligada até chamada aberta.")

        try:
            while self.rodando:
                agora = time.time()

                if agora - ultima_sync >= INTERVALO_SYNC:
                    self._sincronizar_chamada()
                    ultima_sync = agora

                if self.chamada_id_atual is not None:
                    # Câmera deve estar ligada
                    if cap is None or not cap.isOpened():
                        cap = cv2.VideoCapture(self.CAM_INDEX, cv2.CAP_DSHOW)
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        if not cap.isOpened():
                            logger.error("❌ Não foi possível abrir a câmera.")
                            time.sleep(5)
                            continue
                        logger.info("📷 Câmera ligada.")

                    # Nome da thread atualizado
                    if t_proc is None or not t_proc.is_alive():
                        t_proc = threading.Thread(target=self._thread_processamento_visual)
                        t_proc.daemon = True
                        t_proc.start()

                    ret, frame = cap.read()
                    if not ret:
                        logger.error("Falha ao receber frame da câmera.")
                        time.sleep(1)
                        continue

                    with self.lock:
                        self.frame_atual = frame

                    time.sleep(0.01)
                else:
                    # Câmera deve estar desligada
                    if cap is not None and cap.isOpened():
                        cap.release()
                        cap = None
                        with self.lock:
                            self.frame_atual = None
                        logger.info("📷 Câmera desligada — sem chamada aberta.")

                    time.sleep(1)

        finally:
            self.rodando = False
            self._aws_pool.shutdown(wait=False)
            self._api_pool.shutdown(wait=False)
            if cap is not None:
                cap.release()
            logger.info("Sistema de reconhecimento encerrado.")


if __name__ == "__main__":
    app = SistemaReconhecimento()
    app.iniciar()