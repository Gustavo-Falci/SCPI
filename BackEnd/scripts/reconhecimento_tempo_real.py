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
from core.config import COLLECTION_ID, FACE_MATCH_THRESHOLD_SALA
from infra.aws_clientes import rekognition_client
from scripts.confirmacao_burst import ConfirmadorBurst, Decisao, ResultadoFrame
from scripts.anti_spoofing import DetectorTextura

load_dotenv(find_dotenv())
_API_URL = os.getenv("SCPI_API_URL", "https://api.scpi.me").rstrip("/")
_SERVICE_TOKEN = os.getenv("CAMERA_SERVICE_TOKEN", "")
_CAMERA_SALA = os.getenv("CAMERA_SALA", "")
_CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# --- Liveness passivo (burst X-de-Y + pose) — ver spec 2026-07-15 ---
_BURST_FRAMES = int(os.getenv("BURST_FRAMES", "5"))
_BURST_MIN_MATCHES = int(os.getenv("BURST_MIN_MATCHES", "3"))
_BURST_DURACAO_S = float(os.getenv("BURST_DURACAO_S", "2"))
# Pose-variance (hypot) — ADVISORY quando textura ligada; gate só no fallback.
_LIVENESS_POSE_STD_MIN = float(os.getenv("LIVENESS_POSE_STD_MIN", "3.0"))

# --- Anti-spoofing por TEXTURA (modelo CNN local) — ver spec 2026-07-19 ---
# Gate de vida primário. facenox best_model.onnx NÃO-quantizado (1.9 MB).
_ENABLE_TEXTURE = (os.getenv("ENABLE_TEXTURE", "1").strip().lower()
                   not in ("0", "false", "no", ""))
# 0.08 calibrado em campo no frame RAW (foto ~0.003, rosto real ~0.16-0.69).
# No JPEG a separação era mais folgada (0.20); o raw derruba o score do rosto.
_TEXTURE_LIVENESS_MIN = float(os.getenv("TEXTURE_LIVENESS_MIN", "0.08"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SistemaReconhecimento:
    def __init__(self):
        if not _CAMERA_SALA:
            raise ValueError("CAMERA_SALA não definido. Configure a variável de ambiente antes de iniciar.")

        self.rodando = False
        self.frame_atual = None

        self.COOLDOWN_ENTRE_BURSTS = 1.5  # segundos entre bursts (era o intervalo de envio contínuo)
        self.confirmador = ConfirmadorBurst(
            min_matches=_BURST_MIN_MATCHES,
            pose_std_min=_LIVENESS_POSE_STD_MIN,
            texture_min=_TEXTURE_LIVENESS_MIN,
            gate="textura" if _ENABLE_TEXTURE else "pose",
        )
        self.CAM_INDEX = _CAMERA_INDEX

        self.chamada_id_atual = None
        self.presentes_chamada: set = set()

        self.lock = threading.Lock()
        self._aws_pool = ThreadPoolExecutor(max_workers=4)
        self._api_pool = ThreadPoolExecutor(max_workers=2)
        # `or` cobre env presente-porém-vazia (FACE_MODEL_PATH=) — mesmo
        # comportamento do _env_int de infra/database.py.
        model_path = (os.getenv("FACE_MODEL_PATH") or "").strip() or str(
            pathlib.Path(__file__).resolve().parent / "models" / "face_detection_yunet_2023mar.onnx"
        )
        if not os.path.exists(model_path):
            raise ValueError(
                f"Modelo YuNet não encontrado em {model_path}. "
                "Baixe-o conforme ops de setup (opencv_zoo) ou defina FACE_MODEL_PATH."
            )
        # input size é redefinido por frame em _crops_de_rostos
        self.face_detector = cv2.FaceDetectorYN.create(model_path, "", (320, 320), 0.6)

        # Detector de textura (gate de vida). Fail-closed: se ENABLE_TEXTURE e o
        # modelo faltar/não carregar, o boot falha — não se roda sem anti-spoof.
        self.detector_textura = None
        if _ENABLE_TEXTURE:
            texture_path = (os.getenv("TEXTURE_MODEL_PATH") or "").strip() or str(
                pathlib.Path(__file__).resolve().parent / "models" / "best_model.onnx"
            )
            if not os.path.exists(texture_path):
                raise ValueError(
                    f"Modelo de textura não encontrado em {texture_path}. Baixe o "
                    "facenox best_model.onnx NÃO-quantizado (1.9 MB) ou defina "
                    "TEXTURE_MODEL_PATH. Para rodar sem textura: ENABLE_TEXTURE=0."
                )
            self.detector_textura = DetectorTextura(texture_path, _TEXTURE_LIVENESS_MIN)
            logger.info(f"🧬 Anti-spoofing de textura ativo (limiar={_TEXTURE_LIVENESS_MIN}).")
        else:
            logger.warning("⚠️  ENABLE_TEXTURE=0 — sem gate de textura; fallback para pose (paliativo).")

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

    def _analisar_crop(self, face_bytes, chamada_id_referencia, textura=None):
        """SearchFaces + (se match novo) DetectFaces p/ pose. Retorna ResultadoFrame|None.
        `textura` = score de vida do crop (calculado local antes do envio)."""
        try:
            response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=FACE_MATCH_THRESHOLD_SALA,
            )
            if not response['FaceMatches']:
                return None
            external_id = response['FaceMatches'][0]['Face']['ExternalImageId']

            with self.lock:
                if self.chamada_id_atual != chamada_id_referencia:
                    return None
                if external_id in self.presentes_chamada:
                    # Já registrado: não gasta DetectFaces nem entra no burst.
                    return None

            yaw = pitch = None
            try:
                detalhe = rekognition_client.detect_faces(
                    Image={'Bytes': face_bytes},
                    Attributes=['DEFAULT'],
                )
                if detalhe.get('FaceDetails'):
                    pose = detalhe['FaceDetails'][0].get('Pose', {})
                    yaw = pose.get('Yaw')
                    pitch = pose.get('Pitch')
            except Exception as e:
                # Sem pose => frame conta só p/ consenso; decisão vira PENDENTE
                # se nenhum frame do burst tiver pose (fail-safe, não fail-open).
                logger.debug(f"DetectFaces falhou (segue sem pose): {e}")

            return ResultadoFrame(external_id=external_id, yaw=yaw, pitch=pitch, textura=textura)

        except botocore.exceptions.ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"]["Message"]
            if code == "InvalidParameterException" and "no faces" in msg.lower():
                logger.debug("Detector local falso positivo: sem rosto válido no crop.")
            else:
                logger.error(f"Erro AWS (crop): {code} - {msg}")
            return None
        except Exception as e:
            logger.error(f"Erro AWS (crop): {e}")
            return None

    def _crops_de_rostos(self, frame):
        """Detecta rostos (YuNet). Devolve lista de (bbox, jpeg_bytes):
        bbox=(x,y,w,h) cru do YuNet (p/ o detector de textura), jpeg do crop
        com margem 0.2 (p/ a AWS)."""
        h_img, w_img = frame.shape[:2]
        self.face_detector.setInputSize((w_img, h_img))
        _, faces = self.face_detector.detect(frame)
        if faces is None:
            return []
        crops = []
        for f in faces:
            x, y, w, h = (int(v) for v in f[:4])
            margin = int(0.2 * max(w, h))
            x1, y1 = max(0, x - margin), max(0, y - margin)
            x2, y2 = min(w_img, x + w + margin), min(h_img, y + h + margin)
            if x2 <= x1 or y2 <= y1:
                continue
            ret, buffer = cv2.imencode('.jpg', frame[y1:y2, x1:x2])
            if ret:
                crops.append(((x, y, w, h), buffer.tobytes()))
        return crops

    def _thread_processamento_visual(self):
        fim_cooldown = 0.0

        while self.rodando:
            try:
                with self.lock:
                    chamada_atual = self.chamada_id_atual
                    frame = self.frame_atual

                if chamada_atual is None:
                    time.sleep(0.5)
                    continue
                if frame is None or time.time() < fim_cooldown:
                    time.sleep(0.03)
                    continue

                # Gatilho do burst: existe rosto no frame atual?
                if not self._crops_de_rostos(frame):
                    time.sleep(0.03)
                    continue

                # ---- Burst: Y frames ao longo de BURST_DURACAO_S ----
                intervalo = _BURST_DURACAO_S / max(1, _BURST_FRAMES)
                futures = []
                for _ in range(_BURST_FRAMES):
                    with self.lock:
                        frame_i = self.frame_atual
                        chamada_i = self.chamada_id_atual
                    if frame_i is None or chamada_i != chamada_atual:
                        break
                    for bbox, crop in self._crops_de_rostos(frame_i):
                        # Textura pontuada localmente (crop no frame BGR, sem re-decode).
                        tex = None
                        if self.detector_textura is not None:
                            try:
                                tex = self.detector_textura.score(frame_i, bbox)
                            except Exception as e:
                                logger.debug(f"Score de textura falhou (segue None): {e}")
                        futures.append(
                            self._aws_pool.submit(self._analisar_crop, crop, chamada_atual, tex)
                        )
                    time.sleep(intervalo)

                resultados = []
                for fut in futures:
                    try:
                        r = fut.result(timeout=15)
                        if r is not None:
                            resultados.append(r)
                    except Exception as e:
                        logger.error(f"Erro aguardando análise de crop: {e}")

                # ---- Decisão por aluno ----
                for external_id, av in self.confirmador.avaliar_detalhado(resultados).items():
                    if av.decisao is Decisao.REGISTRAR:
                        with self.lock:
                            if self.chamada_id_atual != chamada_atual:
                                continue
                            if external_id in self.presentes_chamada:
                                continue
                            self.presentes_chamada.add(external_id)
                        # Loga textura (gate) + magnitude (advisory) p/ calibração.
                        gate = self.confirmador.gate
                        logger.info(
                            f"🎯 Confirmado ({gate}): {external_id} "
                            f"[matches={av.matches}, texture_max={av.texture_max}, "
                            f"tex_limiar={_TEXTURE_LIVENESS_MIN}, magnitude={av.magnitude}, "
                            f"pose_limiar={_LIVENESS_POSE_STD_MIN}]"
                        )
                        self._api_pool.submit(self._registrar_presenca, external_id)
                    elif av.decisao is Decisao.PENDENTE:
                        gate = self.confirmador.gate
                        motivo = "textura baixa — possível foto" if gate == "textura" \
                            else "magnitude baixa — possível foto ou pessoa parada"
                        logger.info(
                            f"⏳ Pendente (consenso ok, {motivo}): {external_id} "
                            f"[matches={av.matches}, texture_max={av.texture_max}, "
                            f"tex_limiar={_TEXTURE_LIVENESS_MIN}, magnitude={av.magnitude}, "
                            f"pose_limiar={_LIVENESS_POSE_STD_MIN}]"
                        )
                    else:
                        logger.info(
                            f"Descartado (consenso insuficiente): {external_id} "
                            f"[matches={av.matches} < {_BURST_MIN_MATCHES}]"
                        )

                fim_cooldown = time.time() + self.COOLDOWN_ENTRE_BURSTS

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
                            logger.error(
                                f"❌ Não foi possível abrir a câmera no índice {self.CAM_INDEX}. "
                                f"Ajuste CAMERA_INDEX se o dispositivo estiver em outro índice."
                            )
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

                    # Invariante: frame_atual é sempre REBIND de um array novo do
                    # cap.read(); nunca mutar in-place — a thread de processamento
                    # segura referências a ele sem copiar.
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
    
    import faulthandler, signal, datetime, traceback
    faulthandler.enable()

    def _log_sinal(signum, frame):
        with open("sigint_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n=== sinal {signum} @ {datetime.datetime.now()} ===\n")
            traceback.print_stack(frame, file=f)
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _log_sinal)
    try:
        signal.signal(signal.SIGBREAK, _log_sinal)  # Ctrl+Break do Windows
    except (AttributeError, ValueError):
        pass

    app = SistemaReconhecimento()
    try:
        app.iniciar()
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário (Ctrl+C). Encerrando…")