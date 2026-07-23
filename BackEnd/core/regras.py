"""Regras de negócio acadêmicas compartilhadas entre camadas.

Constantes daqui não pertencem a nenhuma camada específica (services, infra):
são regra acadêmica pura. Centralizar evita que a mesma regra divirja — por
exemplo, o serviço decidir o rótulo "Regular"/"Risco" com um limiar e o PDF
pintar a linha de verde/vermelho com outro.
"""

# Frequência mínima (%) para o aluno ser considerado "Regular" — abaixo disso,
# "Risco". Usado tanto para o rótulo textual quanto para a cor no PDF.
LIMITE_FREQUENCIA = 75
