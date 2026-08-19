# DPIA — Data Protection Impact Assessment
## SCPI — Sistema de Controle de Presença Inteligente

**Versão:** 1.0  
**Data:** 2026-05-14  
**Responsável:** <!-- PREENCHER NOME -->  
**Status:** TCC — parcialmente implementado; roadmap para produção documentado abaixo.

---

## 1. Descrição do Tratamento

O SCPI realiza reconhecimento facial de alunos para automatizar o controle de presença em aulas. O sistema captura imagens via app mobile, indexa vetores biométricos no AWS Rekognition, e armazena imagens originais no AWS S3. Durante chamadas, a câmera da sala reconhece alunos em tempo real.

**Tecnologias:** FastAPI (backend), Expo/React Native (mobile), HTML/JS (portal), PostgreSQL (banco), AWS Rekognition + S3 (biometria).

---

## 2. Mapeamento de Dados e Fluxos

| Dado | Origem | Destino | Retenção |
|------|--------|---------|----------|
| Nome, e-mail, RA | Cadastro admin | PostgreSQL | Vínculo + 5 anos |
| Imagem facial (foto) | App mobile (upload) | AWS S3 (us-east-1) | Até revogação |
| Vetor biométrico | AWS Rekognition (indexação) | AWS Rekognition Collection | Até revogação |
| face_id, external_image_id, s3_path | AWS Rekognition response | PostgreSQL (Colecao_Rostos) | Até revogação |
| Timestamp de presença | Reconhecimento em tempo real | PostgreSQL (Presencas) | 5 anos |
| Logs de auditoria | Eventos do sistema | Arquivo local (BackEnd/logs/) | 90 dias |
| Token de push | App mobile | PostgreSQL (PushTokens) | Ativo |

---

## 3. Base Legal por Tratamento

| Tratamento | Base Legal LGPD |
|-----------|----------------|
| Dados cadastrais (nome, e-mail, RA) | Art. 7, V — execução de contrato educacional |
| Dados biométricos (foto, vetor) | Art. 11, II, 'a' — consentimento explícito |
| Registros de presença | Art. 7, V — execução de contrato educacional |
| Logs de auditoria (IP, e-mail mascarado) | Art. 7, II — obrigação legal (segurança) |
| Transferência internacional (AWS us-east-1) | Art. 33, II — DPA da AWS |

---

## 4. Riscos Identificados e Mitigações Implementadas

| Risco | Probabilidade | Impacto | Mitigação Implementada |
|-------|--------------|---------|----------------------|
| Acesso não autorizado à biometria | Média | Alto | JWT + RBAC + require_self_or_admin |
| Dados biométricos órfãos no S3 ao deletar aluno | Alta (corrigido) | Médio | Cleanup S3+Rekognition antes de DELETE (Task 1) |
| Exposição de nomes em logs | Alta (corrigido) | Baixo | Mascaramento nos logs de reconhecimento (Task 2) |
| Logs indefinidos violando retenção | Alta (corrigido) | Médio | TimedRotatingFileHandler 90 dias (Task 3) |
| Acentos corrompendo ExternalImageId | Alta (corrigido) | Médio | unicodedata.normalize NFKD (utils.py) |
| Consentimento sem informar transferência int. | Alta (corrigido) | Alto | Texto atualizado com us-east-1 + DPA (Task 5) |
| Ausência de política de privacidade | Alta (corrigido) | Alto | portal/privacy.html publicado (Task 7) |
| Reconhecimento facial sem consentimento | Baixa | Crítico | Consentimento obrigatório antes do cadastro facial |
| Brute force no login | Média | Médio | Rate limiting 10/min + senha bcrypt |
| Vazamento de token JWT | Baixa | Alto | Expiração 60min + refresh rotation + logout revoga |

---

## 5. Direitos dos Titulares — Implementação

| Direito (Art. 18) | Status | Como Exercer |
|-------------------|--------|-------------|
| Confirmação e acesso | ✅ Implementado | App: Perfil → "Exportar meus dados" |
| Correção | ⚠️ Parcial | Via DPO por e-mail; sem UI self-service |
| Eliminação | ✅ Implementado | App: revogar biometria; exclusão completa via admin/DPO |
| Portabilidade | ✅ Implementado | Exportação JSON via app mobile |
| Revogação do consentimento | ✅ Implementado | App: Perfil → revogar biometria |
| Oposição | ⚠️ Parcial | Via DPO por e-mail |
| Revisão de decisão automatizada | N/A | Sistema não toma decisões prejudiciais automatizadas |

---

## 6. Transferência Internacional

- **Processador:** Amazon Web Services, Inc.
- **Região:** us-east-1 (Virgínia do Norte, EUA)
- **Base legal:** LGPD Art. 33, II — cláusulas contratuais padrão (DPA da AWS)
- **DPA da AWS:** https://aws.amazon.com/agreement/ (Data Processing Addendum)
- **Certificações AWS:** ISO 27001, SOC 2 Type II, PCI DSS

**Sentry (telemetria de erros):**

- **Processador:** Sentry (Functional Software, Inc.), SaaS hospedado nos EUA.
- **Dados enviados:** eventos de erro — tipo da exceção, arquivo, linha e
  stack trace. Sem valores de variáveis locais, sem corpo de requisição e sem
  headers de autenticação.
- **Base legal:** legítimo interesse em segurança e continuidade do serviço.
- **Mitigações aplicadas:** `send_default_pii=False`, `include_local_variables=False`,
  `max_request_body_size="never"` e hook `before_send` removendo credenciais
  antes do envio.

---

## 7. Roadmap para Produção (Pendente)

Os itens abaixo não são impeditivos para o TCC mas devem ser implementados antes de um deploy em produção com dados reais:

| Item | Prioridade | Descrição |
|------|-----------|-----------|
| DPA formal com AWS | Alta | Assinar o AWS DPA via console AWS |
| DPA com Resend | Alta | Acordo formal para serviço de e-mail |
| SOP breach notification | Alta | Procedimento documentado para notificar ANPD e titulares em 72h |
| MFA para administradores | Alta | Segundo fator no login de Admin |
| HTTPS obrigatório | Alta | Configurar nginx/caddy com TLS antes de abrir para internet |
| Endpoint de retificação | Média | UI/API para aluno corrigir nome, e-mail |
| Certificate pinning (mobile) | Média | Evitar MITM em redes não confiáveis |
| Criptografia de campo no DB | Baixa | Criptografar nome/e-mail no PostgreSQL com pgcrypto |
| Auditoria de acesso no portal | Baixa | Log de quem visualizou quais relatórios |
| Registro de operador na ANPD | Alta | Conforme Resolução CD/ANPD nº 2/2022 |

---

## 8. Conclusão

O SCPI trata dados biométricos de alunos com base no consentimento explícito (LGPD Art. 11). As mitigações implementadas nesta versão cobrem os riscos críticos identificados. O sistema está em conformidade com os princípios do Art. 6 da LGPD (finalidade, adequação, necessidade, livre acesso, qualidade, transparência, segurança). Os itens do roadmap de produção devem ser tratados antes de qualquer deploy com dados de alunos reais.
