# SCPI — Runbook de Segurança

Procedimentos operacionais para incidentes e tarefas recorrentes de segurança. Cobre o que o manual `manual_seguranca_sistemas_v2.md` §11 e §5.3 exigem.

> Mantenha este documento sincronizado com o estado real da infraestrutura. Toda mudança em fluxo crítico (rotação, isolamento, restauração) deve ser refletida aqui.

---

## 1. Contatos de emergência

| Papel | Pessoa | Como acionar |
|---|---|---|
| DPO / LGPD | _preencher_ | _email + telefone_ |
| Líder técnico | Gustavo Falci | _email_ |
| Provedor de nuvem | AWS Support | console AWS → Support Center |
| ANPD (vazamento dados pessoais) | comunicacao@anpd.gov.br | https://www.gov.br/anpd |
| CERT.br | cert@cert.br | https://www.cert.br |

---

## 2. Classificação de severidade

| Nível | Definição | SLA inicial |
|---|---|---|
| **P0** | Vazamento ativo, comprometimento confirmado, indisponibilidade total | 15 min |
| **P1** | Vulnerabilidade explorável em produção, sem comprometimento confirmado | 4 h |
| **P2** | Vulnerabilidade explorável em staging/dev, ou em prod com mitigação parcial | 1 dia útil |
| **P3** | Hardening / dívida técnica de segurança | sprint corrente |

---

## 3. Rotação de credenciais

### 3.1. `SECRET_KEY` (JWT)

**Quando:** a cada 90 dias **ou** suspeita de vazamento.

**Como:**

```bash
# 1. Gere nova chave
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Atualize SECRET_KEY no .env de produção (ou cofre)

# 3. Reinicie a API
sudo systemctl restart scpi-api  # ou equivalente

# 4. Todos os access tokens existentes são invalidados imediatamente.
#    Refresh tokens continuam válidos (opacos, não assinados com SECRET_KEY).
#    Clientes fazem refresh transparente.
```

**Impacto:** usuários com access token expirado recebem 401 uma vez; cliente roda fluxo de refresh automaticamente; sem logout visível.

### 3.2. `CAMERA_SERVICE_TOKEN`

**Quando:** a cada 90 dias, ao detectar uso indevido, ou ao trocar a máquina da câmera.

**Como:**

```bash
# 1. Gere
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Atualize em DOIS lugares simultaneamente:
#    - BackEnd/.env (servidor)
#    - .env da máquina da câmera
# 3. Reinicie backend + script reconhecimento_tempo_real.py
```

**Impacto:** janela curta (segundos) sem reconhecimento por câmera enquanto restart acontece.

### 3.3. Senha de banco (`DB_PASSWORD`)

**Quando:** suspeita de vazamento, troca de prestador, fim de período de empregado com acesso.

**Como:**

```sql
ALTER USER scpi_app WITH PASSWORD 'nova-senha-forte';
```

```bash
# Atualize DB_PASSWORD em BackEnd/.env, reinicie backend.
```

### 3.4. Credenciais AWS (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`)

**Preferência:** usar IAM Role no EC2 ou ECS — chaves estáticas só em dev local.

**Rotação em prod (se inevitável):**

1. IAM Console → criar nova access key para o usuário scpi-backend.
2. Atualizar segredo no AWS Secrets Manager / cofre.
3. Reiniciar backend; validar que `_check_aws_connectivity` passa.
4. **Desabilitar** (não deletar) chave antiga; aguardar 24 h; deletar.

### 3.5. `RESEND_API_KEY`

Resend dashboard → API Keys → Revoke + Create New → atualizar `.env`.

---

## 4. Resposta a incidentes

### 4.1. Vazamento de credencial em commit público

1. **Rotacionar imediatamente** (seção 3 aplicável). O Git filter-repo NÃO desfaz o vazamento — crawlers podem já ter coletado.
2. Adicionar fingerprint ao `.gitleaksignore` para CI parar de alarmar no histórico.
3. Auditar logs de uso da credencial nas últimas 90 dias.
4. Comunicar incidente conforme §4.4 se houver indício de acesso indevido.

### 4.2. Suspeita de comprometimento de servidor

1. **Isolar**: bloquear Security Group para inbound público, exceto seu IP.
2. Snapshot do disco antes de qualquer ação destrutiva (forense).
3. Rotacionar **todas** as credenciais (seção 3).
4. Restaurar a partir de imagem conhecida boa **antes** do indício.
5. Validar persistência (cron tabs, ssh keys, systemd units não conhecidos).
6. Reaplicar deploy do último commit auditado.

### 4.3. Indisponibilidade por ataque DDoS

1. AWS Shield Standard já ativo; ative WAF rate-based rule se ainda não estiver.
2. Cloudflare em modo "Under Attack" se em uso.
3. Slowapi (já configurado) absorve camada aplicação; monitore métricas.

### 4.4. Vazamento de dados pessoais (LGPD art. 48)

1. Confirmar escopo: que dados, quais titulares, por quanto tempo.
2. Notificar DPO em até 1 h.
3. DPO comunica ANPD em prazo razoável (LGPD não fixa; jurisprudência aponta 72 h).
4. Comunicar titulares afetados.
5. Documentar timeline e medidas corretivas no post-mortem.

---

## 5. Backups e recuperação

- **Frequência mínima recomendada:** diária para banco, retenção 30 dias.
- **Teste de restore:** trimestral, em ambiente isolado. Backup não testado = backup que não existe.
- **Criptografia:** SSE-KMS ou equivalente — backup vaza com a mesma severidade que dado primário.

---

## 6. Pós-incidente (blameless post-mortem)

Para cada incidente P0/P1, em até 7 dias:

1. Timeline cronológica (detecção → contenção → erradicação → recuperação).
2. Causa raiz (técnica + organizacional).
3. O que funcionou bem.
4. O que falhou.
5. Ações corretivas com responsáveis e prazos.
6. Atualizar este runbook se necessário.

Sem culpabilização de pessoas — foco em melhorias sistêmicas.

---

## 7. Calendário de revisões

| Item | Periodicidade |
|---|---|
| Este runbook | Após cada incidente significativo; revisão geral a cada 6 meses |
| Rotação `SECRET_KEY` | 90 dias |
| Rotação `CAMERA_SERVICE_TOKEN` | 90 dias |
| Teste de restore | Trimestral |
| Auditoria de permissões IAM | Semestral |
| Pentest externo | Anual (recomendado) |
