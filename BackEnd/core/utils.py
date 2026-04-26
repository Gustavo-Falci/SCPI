import re

def formatar_nome_para_external_id(nome: str) -> str:
    """
    Formata o nome do aluno para o padrão aceito pelo AWS Rekognition.
    Remove acentos, caracteres especiais e substitui espaços por underlines.
    Ex: 'João da Silva' -> 'Joao_da_Silva'
    """
    # Remove espaços extras e substitui por _
    nome_formatado = re.sub(r'\s+', '_', nome.strip())
    # Remove tudo que não for letra, número, _ . - ou :
    nome_formatado = re.sub(r'[^a-zA-Z0-9_.\-:]', '', nome_formatado)
    return nome_formatado
