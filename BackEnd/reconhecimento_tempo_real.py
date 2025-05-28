# Importações de bibliotecas necessárias
from config import AWS_REGION, COLLECTION_ID
from datetime import datetime
from botocore.exceptions import ClientError
from aws_clientes import rekognition_client
import cv2
import time
import json
import csv
import os
import logging
import threading
import sys 

logger = logging.getLogger(__name__)

# Diretório base do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Timestamp atual para nomear arquivos de log e relatórios
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

# Criação e configuração do diretório de logs
log_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, f"log_{timestamp}.log")

# Configuração do logger (arquivo e console)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)


# Lista para armazenar os alunos reconhecidos
alunos_reconhecidos = []

# Dicionário que guarda o timestamp do último reconhecimento por FaceId
faceid_ultimo_reconhecimento = {}
TEMPO_ESPERA = 10  # Tempo em segundos para evitar reconhecer o mesmo rosto repetidamente

# Criação do diretório onde os relatórios serão salvos
PASTA_RELATORIOS = os.path.join(BASE_DIR, "Relatorios")
os.makedirs(PASTA_RELATORIOS, exist_ok=True)

# Variáveis globais compartilhadas entre as threads
nomes_para_exibir = []  # Nomes a serem mostrados no vídeo
ultimo_envio = 0        # Controle de tempo do último envio ao Rekognition
frame_atual = None      # Armazena o último frame capturado
rodando = True          # Controle de execução do loop principal


# Função para verificar a conexão com AWS Rekognition e a existência da coleção
def verificar_setup_aws_rekognition(client_rek, collection_id_to_check, region_name_config):
    """
    Verifica a conexão com o AWS Rekognition, as permissões básicas
    e se a coleção especificada existe.
    Retorna True se tudo estiver OK, False caso contrário.
    """
    if not client_rek:
        logger.info("Cliente Rekognition não inicializado. Verificação de setup cancelada.")
        return False
    logger.info("Verificando setup do AWS Rekognition...")

    try:
        # 1. Teste de Conexão e Permissões Básicas: Listar Coleções
        logger.info("Tentando listar coleções para testar a conexão e permissões básicas...")
        response_list = client_rek.list_collections()

        logger.info(f"Conexão bem-sucedida! Coleções Rekognition existentes: {response_list.get('CollectionIds', [])}")

        # 2. Teste de Existência da Coleção Específica
        logger.info(f"Verificando se a coleção '{collection_id_to_check}' existe...")
        client_rek.describe_collection(CollectionId=collection_id_to_check)

        logger.info(f"Coleção '{collection_id_to_check}' encontrada e acessível.")
        
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f"ERRO DE CLIENTE AWS: {error_code} - {error_message}")

        if error_code == 'UnrecognizedClientException':
            logger.error("Causa provável: As credenciais da AWS (access key, secret key) estão inválidas, ausentes ou a região está mal configurada.")
            logger.error("Verifique seu arquivo ~/.aws/credentials, ~/.aws/config ou variáveis de ambiente AWS (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION).")

        elif error_code == 'AccessDeniedException':
            logger.error("Causa provável: O usuário IAM não tem as permissões necessárias.")
            logger.error("Certifique-se de que o usuário/role IAM associado às suas credenciais tem permissões para 'rekognition:ListCollections' e 'rekognition:DescribeCollection'.")
            logger.error(f"Detalhes da negação de acesso: {error_message}")

        elif error_code == 'ResourceNotFoundException':
            logger.error(f"Causa provável: A coleção Rekognition '{collection_id_to_check}' não existe na região '{region_name_config}'.")
            logger.error("Verifique se o nome da coleção e a região AWS estão corretos e se a coleção foi criada no Amazon Rekognition.")

        elif error_code == 'InvalidSignatureException' or error_code == 'SignatureDoesNotMatch':
            logger.error("Causa provável: Chave de acesso secreta (Secret Access Key) inválida. Verifique suas credenciais AWS.")

        elif error_code == 'ThrottlingException':
            logger.error("Causa provável: Muitas requisições para a AWS. Tente novamente mais tarde.")

        elif error_code == 'InvalidParameterException' and 'Unable to parse region' in error_message:
             logger.error(f"Causa provável: Região AWS '{region_name_config}' inválida ou mal formatada. Verifique a configuração da região.")

        else:
            logger.error(f"Um erro inesperado do cliente AWS ocorreu durante a verificação: {error_message}")

        return False
    
    except Exception as e: # Captura outras exceções (ex: BotoCoreError para problemas de endpoint/rede)
        logger.error(f"ERRO GERAL durante a verificação do setup AWS: {e}")
        logger.error("Verifique sua conexão de rede e as configurações de endpoint da AWS, se aplicável.")

        return False

# Função que envia a imagem para o Rekognition e processa os rostos detectados
def processar_rekognition():
    global frame_atual, ultimo_envio

    if not rekognition_client: # Adiciona verificação
        logger.error("Cliente Rekognition não está disponível na thread processar_rekognition.")
        return #Sinalizar erro para a thread principal

    while rodando:
        # Aguarda até que seja hora de processar um novo frame
        if frame_atual is None or time.time() - ultimo_envio < 1:
            time.sleep(0.05)
            continue

        ultimo_envio = time.time()
        nomes_para_exibir.clear()
        frame_para_processar = frame_atual # Copia para evitar problemas de concorrência

        try:
            # Codifica o frame atual em JPEG para envio
            _, buffer = cv2.imencode('.jpg', frame_para_processar)
            image_bytes = buffer.tobytes()

            # Chama o Rekognition para procurar rostos conhecidos
            response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': image_bytes},
                MaxFaces=5,
                FaceMatchThreshold=85
            )

            # Processa as faces encontradas
            if response['FaceMatches']:
                agora = time.time()

                for match in response['FaceMatches']:
                    face_id = match['Face']['FaceId']
                    aluno_id = match['Face']['ExternalImageId']

                    # Ignora se já foi reconhecido recentemente
                    if agora - faceid_ultimo_reconhecimento.get(face_id, 0) < TEMPO_ESPERA:
                        continue

                    # Atualiza o tempo de reconhecimento e registra o aluno
                    faceid_ultimo_reconhecimento[face_id] = agora
                    nomes_para_exibir.append(aluno_id)
                    logger.info(f"Aluno reconhecido: {aluno_id}")

                    # Adiciona o aluno à lista se ainda não estiver
                    if aluno_id not in [aluno["id"] for aluno in alunos_reconhecidos]:
                        alunos_reconhecidos.append({
                            "id": aluno_id,
                            "horario": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
            else:
                logger.info("Nenhum rosto conhecido encontrado no frame atual.")

        except rekognition_client.exceptions.InvalidParameterException:
            logger.info("Nenhum rosto detectado no frame pelo Rekognition. Continuando...")

        except ClientError as e: # Tratamento de erros do cliente AWS mais específico
            error_code = e.response['Error']['Code']
            logger.error(f"Erro do cliente AWS ao chamar Rekognition (search_faces_by_image): {error_code} - {e.response['Error']['Message']}")
            # Adicionar lógica para lidar com throttling ou outros erros recuperáveis se necessário
            time.sleep(2) # Pausa para evitar sobrecarregar em caso de erro persistente

        except Exception as e:
            logger.error(f"Erro inesperado ao chamar o Rekognition: {e}")
            time.sleep(2) 

        time.sleep(0.1) # Pequena pausa na thread de processamento

# Função principal que captura os frames da câmera em tempo real
def reconhecer_em_tempo_real():
    global frame_atual, rodando

    # Inicia a captura da câmera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logger.warning("Câmera 0 não disponível. Tentando câmera 1...")
        cap = cv2.VideoCapture(1)

    if cap.isOpened():
        logger.info("Câmera inicializada com sucesso.")

    else:
        logger.error("Erro ao abrir a câmera. Verifique se está conectada e não em uso por outro programa.")
        return
    

    # Define resolução (opcional)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    # logger.info(f"Resolução da câmera definida para: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")


    # Inicia a thread para processar o Rekognition paralelamente
    rekognition_thread = threading.Thread(target=processar_rekognition, daemon=True)
    rekognition_thread.start()

    # Loop principal de captura e exibição do vídeo
    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            logger.error("Erro ao capturar frame da câmera. Encerrando.")
            rodando = False # Sinaliza para a thread de processamento encerrar
            break

        # Atualiza o frame atual para ser processado
        frame_atual = frame.copy() # Garante que a thread de rekognition use uma cópia estável

        # (Descomentar se quiser exibir os nomes no vídeo)
        # y_offset = 30
        # for nome in nomes_para_exibir: # Usar uma cópia para evitar problemas de concorrência se nomes_para_exibir for modificado
        #     cv2.putText(frame, f"Reconhecido: {nome}", (10, y_offset),
        #                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        #     y_offset += 30

        # Exibe a imagem da câmera em tempo real
        cv2.imshow("Reconhecimento Facial - Pressione 'ESC' para sair", frame)

        # Sai se a tecla ESC for pressionada
        key = cv2.waitKey(1) & 0xFF
        if key == 27: # Tecla ESC
            rodando = False
            logger.info("Tecla ESC pressionada. Encerrando aplicação...")
            break
        
        time.sleep(0.05) # Ajuste conforme necessário para equilibrar responsividade e uso de CPU

    # Espera a thread de Rekognition finalizar (opcional, pois é daemon)
    if rekognition_thread.is_alive():
        logger.info("Aguardando a thread de processamento do Rekognition finalizar...")
        rekognition_thread.join(timeout=5.0) # Espera até 5 segundos

        if rekognition_thread.is_alive():
            logger.warning("Thread de Rekognition não finalizou a tempo.")

    # Libera recursos e gera relatórios ao finalizar
    cap.release()
    cv2.destroyAllWindows()
    logger.info("Câmera liberada e janelas destruídas.")
    
    if alunos_reconhecidos:
        gerar_relatorio_csv()
        gerar_relatorio_json()

    else:
        logger.info("Nenhum aluno foi reconhecido para gerar relatórios.")

# Gera o relatório de presença no formato CSV
def gerar_relatorio_csv():
    filename = os.path.join(PASTA_RELATORIOS, f"relatorio_presenca_{timestamp}.csv")

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["ID do Aluno", "Horário de Reconhecimento"])

            for aluno in alunos_reconhecidos:
                writer.writerow([aluno["id"], aluno["horario"]])
        logger.info(f"Relatório CSV salvo como {filename}")

    except IOError as e:
        logger.error(f"Erro ao salvar relatório CSV: {e}")

# Gera o relatório de presença no formato JSON
def gerar_relatorio_json():
    # Usar o timestamp no nome do arquivo JSON também pode ser útil se quiser manter históricos
    filename = os.path.join(PASTA_RELATORIOS, f"relatorio_presenca_{timestamp}.json") 

    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(alunos_reconhecidos, file, indent=4, ensure_ascii=False)
        logger.info(f"Relatório JSON salvo como {filename}")

    except IOError as e:
        logger.error(f"Erro ao salvar relatório JSON: {e}")

# Ponto de entrada do script
if __name__ == "__main__":
    logger.info("Iniciando aplicação de reconhecimento facial em tempo real...")

    # Verifica a conexão e configuração da AWS antes de prosseguir
    if not rekognition_client: # Verifica se o cliente global foi carregado
         logger.error("Cliente Rekognition não pôde ser inicializado. Verifique aws_clients.py e as configurações.")
         sys.exit(1)

    # A função verificar_setup_aws_rekognition agora usa o rekognition_client importado
    if not verificar_setup_aws_rekognition(rekognition_client, COLLECTION_ID, AWS_REGION):
        logger.error("Falha crítica na verificação do setup da AWS. A aplicação será encerrada.")
        sys.exit(1) # Encerra o script se a verificação falhar

    logger.info("Setup da AWS verificado com sucesso. Iniciando reconhecimento...")
    reconhecer_em_tempo_real()
    logger.info("Aplicação encerrada.")