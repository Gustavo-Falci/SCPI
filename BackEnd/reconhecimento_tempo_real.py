import cv2
import time
import threading
import logging
import os
from datetime import datetime

# Nossos módulos refatorados
from config import COLLECTION_ID, AWS_REGION
from aws_clientes import rekognition_client
from database import get_db_cursor
from utils import formatar_nome_para_external_id

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SistemaReconhecimento:
    def __init__(self):
        self.rodando = False
        self.frame_atual = None
        self.ultimo_reconhecimento = {} # Cache para não spamar o banco {face_id: timestamp}
        self.texto_na_tela = "Aguardando..."
        self.cor_texto = (0, 255, 255) # Amarelo (BGR)
        
        # Configurações
        self.INTERVALO_ENVIO_AWS = 1.5  # Segundos entre envios para AWS
        self.TEMPO_COOLDOWN_ALUNO = 15  # Segundos para registrar o mesmo aluno de novo
        self.CAM_INDEX = 0 # Tente 1 se o 0 for a webcam integrada e você quiser a USB
        
        # Thread lock para evitar conflito de leitura/escrita no frame
        self.lock = threading.Lock()

        self.CAM_INDEX = 0

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self.lock = threading.Lock()

    def _registrar_presenca(self, external_image_id):
        """Registra no banco usando nossa nova estrutura otimizada."""
        try:
            # Importamos aqui para evitar ciclo se estivesse no topo, 
            # mas como db_operacoes usa database, tudo bem.
            from db_operacoes import registrar_presenca_por_face
            
            sucesso = registrar_presenca_por_face(external_image_id)
            if sucesso:
                self.texto_na_tela = f"PRESENCA: {external_image_id}"
                self.cor_texto = (0, 255, 0) # Verde
            else:
                self.texto_na_tela = f"Reconhecido (Sem chamada): {external_image_id}"
                self.cor_texto = (0, 165, 255) # Laranja
                
            # Limpa o texto após 3 segundos (feito via timer simples na thread de video)
            threading.Timer(3.0, self._resetar_texto).start()
            
        except Exception as e:
            logger.error(f"Erro ao registrar presença: {e}")

    def _resetar_texto(self):
        self.texto_na_tela = "Monitorando..."
        self.cor_texto = (255, 255, 255)

    def _thread_aws_rekognition(self):
        """Loop inteligente: Só envia para AWS se o PC detectar um rosto antes."""
        ultimo_envio = 0
        
        while self.rodando:
            agora = time.time()
            
            # 1. Controle de tempo
            if agora - ultimo_envio < self.INTERVALO_ENVIO_AWS:
                time.sleep(0.1)
                continue
            
            # 2. Obter frame
            with self.lock:
                if self.frame_atual is None: continue
                img_para_processar = self.frame_atual.copy()

            # --- NOVO: FILTRAGEM LOCAL (CUSTO ZERO) ---
            # Converte para escala de cinza (o detector local funciona melhor assim)
            gray = cv2.cvtColor(img_para_processar, cv2.COLOR_BGR2GRAY)
            
            # Detecta rostos na imagem
            # scaleFactor=1.1, minNeighbors=5 são ajustes padrões para precisão
            rostos_detectados = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            
            # Se a lista de rostos for vazia, NÃO envia para AWS
            if len(rostos_detectados) == 0:
                # Opcional: Atualiza texto na tela para debug
                # self.texto_na_tela = "Nenhum rosto detectado (Local)"
                time.sleep(0.2)
                continue 
            
            # Se chegou aqui, TEM rosto. Vamos gastar crédito da AWS para saber QUEM É.
            # ------------------------------------------

            # 3. Codificar e Enviar (Código original mantido abaixo)
            ret, buffer = cv2.imencode('.jpg', img_para_processar)
            if not ret: continue
            image_bytes = buffer.tobytes()
            
            ultimo_envio = agora # Reseta o timer apenas se enviou de verdade
            
            try:
                response = rekognition_client.search_faces_by_image(
                    CollectionId=COLLECTION_ID,
                    Image={'Bytes': image_bytes},
                    MaxFaces=1,
                    FaceMatchThreshold=85
                )

                if response['FaceMatches']:
                    match = response['FaceMatches'][0]
                    face_id = match['Face']['FaceId']
                    aluno_external_id = match['Face']['ExternalImageId']
                    
                    ultimo_rec = self.ultimo_reconhecimento.get(face_id, 0)
                    if agora - ultimo_rec > self.TEMPO_COOLDOWN_ALUNO:
                        logger.info(f"🎯 Reconhecido: {aluno_external_id}")
                        self.ultimo_reconhecimento[face_id] = agora
                        t_banco = threading.Thread(target=self._registrar_presenca, args=(aluno_external_id,))
                        t_banco.start()
            
            except Exception as e:
                logger.error(f"Erro AWS: {e}")

    def iniciar(self):
        """Inicia a captura de vídeo e as threads."""
        self.rodando = True
        
        # Inicia Câmera
        # CAP_DSHOW ajuda no Windows a iniciar a câmera mais rápido
        cap = cv2.VideoCapture(self.CAM_INDEX, cv2.CAP_DSHOW) 
        
        if not cap.isOpened():
            logger.error("❌ Não foi possível abrir a câmera.")
            return

        # Configura resolução (Opcional, mas ajuda performance)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Inicia Thread da AWS
        t_aws = threading.Thread(target=self._thread_aws_rekognition)
        t_aws.daemon = True # Morre se o programa principal fechar
        t_aws.start()

        logger.info("🎥 Sistema iniciado. Pressione 'ESC' para sair.")
        print(f"📡 Conectado à AWS Region: {AWS_REGION}")
        print(f"📂 Coleção: {COLLECTION_ID}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Falha ao receber frame da câmera.")
                    break

                # Atualiza o frame global para a thread da AWS ler
                with self.lock:
                    self.frame_atual = frame

                # --- DESENHO NA TELA (UI) ---
                # Cria uma barra preta semitransparente no topo para o texto
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (640, 50), (0, 0, 0), -1)
                alpha = 0.6
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

                # Escreve o status
                cv2.putText(frame, self.texto_na_tela, (10, 35), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.cor_texto, 2)

                # Mostra janela
                cv2.imshow('SCPI - Reconhecimento Facial', frame)

                # Sai com ESC
                if cv2.waitKey(1) == 27:
                    break
        
        finally:
            self.rodando = False
            cap.release()
            cv2.destroyAllWindows()
            logger.info("Sistema encerrado.")

if __name__ == "__main__":
    app = SistemaReconhecimento()
    app.iniciar()