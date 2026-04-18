# SCPI — Security Operations

Guia operacional de segurança. Complementa o código com ações de infra/AWS/LGPD que não moram no repositório.

## 1. Rotação imediata de credenciais (urgente)

O histórico git contém um commit (`2b793c55`) que expôs o arquivo `.env`. Mesmo já removido do tree atual, as credenciais precisam ser **rotacionadas**:

1. **PostgreSQL (Oracle Cloud)** — Trocar a senha do usuário `postgres` e de qualquer role usada pela API.
2. **AWS IAM** — Revogar o `AWS_ACCESS_KEY_ID` vazado, criar um novo par com política mínima (ver §3).
3. **JWT `SECRET_KEY`** — Gerar nova chave (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Trocar invalida todos os tokens emitidos.
4. **Limpar histórico git** (opcional, destrutivo):
   ```bash
   git filter-repo --path BackEnd/.env --invert-paths
   git push --force origin main
   ```
   Só execute após coordenar com o time — reescreve SHAs.

## 2. HTTPS em produção

A API hoje serve em HTTP puro. Para expor fora da rede local:

- **Reverse proxy com TLS**: Nginx/Caddy na frente do Uvicorn, certificado Let's Encrypt (Caddy faz isso sozinho).
- **Alternativa**: Cloudflare Tunnel / Oracle Cloud LB com TLS terminator.
- No Expo/RN, `EXPO_PUBLIC_API_URL` passa a apontar para `https://api.<seu-domínio>` — tokens e fotos de rosto deixam de trafegar em claro.
- Ativar HSTS (`Strict-Transport-Security: max-age=31536000; includeSubDomains`) no proxy.

## 3. IAM least-privilege (AWS)

O usuário IAM da API só precisa de duas coisas: Rekognition na coleção específica e S3 no bucket específico. Exemplo de policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3RostosObjetos",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<BUCKET_NAME>/alunos/*"
    },
    {
      "Sid": "RekognitionColecao",
      "Effect": "Allow",
      "Action": [
        "rekognition:IndexFaces",
        "rekognition:SearchFacesByImage",
        "rekognition:DeleteFaces",
        "rekognition:ListFaces"
      ],
      "Resource": "arn:aws:rekognition:<REGION>:<ACCOUNT>:collection/<COLLECTION_ID>"
    }
  ]
}
```

Não conceda `s3:ListAllMyBuckets`, `iam:*` ou wildcards em `Resource`.

## 4. Bucket S3 privado + presigned URLs

- Bloquear acesso público: **Block all public access = ON** no console S3.
- Ativar **versioning** + **default encryption (SSE-S3 ou SSE-KMS)**.
- Nenhum endpoint da API retorna URL pública. Para exibir a foto cadastrada, o cliente chama `GET /aluno/biometria-foto/{usuario_id}` que retorna URL presigned válida por 5 min.

## 5. LGPD — Dados biométricos (art. 11)

- Cadastro facial exige `consentimento_biometrico=true` explícito nos endpoints `/auth/register-aluno-com-face` e `/alunos/cadastrar-face`.
- Timestamp do consentimento persistido em `Colecao_Rostos.consentimento_data`.
- Revogação pelo titular: `DELETE /aluno/biometria/{usuario_id}` remove face no Rekognition, apaga objeto no S3 e marca `revogado_em`.
- Auditoria: logs `scpi.audit` registram login (ok/falha), abertura de chamada, presença confirmada, logout e revogação de biometria.

## 6. Tokens e sessão

- Access token JWT: **15 min**. Carrega `type=access` para evitar confusão com refresh.
- Refresh token **opaco** (não-JWT): 7 dias, hash SHA-256 persistido em `RefreshTokens`. Rotação a cada `/auth/refresh` — o anterior é marcado `revoked_at`.
- `/auth/logout` revoga o refresh atual. Access tokens vigentes continuam válidos até expirar (aceitável para 15 min de TTL).

## 7. Rate limits ativos (`slowapi`)

| Endpoint | Limite |
| --- | --- |
| `/auth/login` | 10 / min / IP |
| `/auth/register` | 5 / min / IP |
| `/auth/register-aluno-com-face` | 5 / min / IP |
| `/auth/refresh` | 30 / min / IP |
| `/alunos/cadastrar-face` | 10 / min / IP |
| `/chamadas/registrar_rosto` | 10 / min / IP |

Ajustar em `BackEnd/api.py` conforme volume real de produção.

## 8. Checklist antes de publicar

- [ ] `.env` preenchido a partir de `.env.example` com segredos reais e fora do git.
- [ ] `SECRET_KEY` com ≥ 32 caracteres aleatórios.
- [ ] `ALLOWED_ORIGINS` listando só os domínios reais do app (sem `*`).
- [ ] IAM policy reduzida ao bucket/coleção únicos.
- [ ] S3 bucket privado + versioning + encryption.
- [ ] Proxy TLS (HTTPS) na frente da API.
- [ ] `EXPO_PUBLIC_API_URL` aponta para o domínio HTTPS.
- [ ] Credenciais antigas do histórico git revogadas/rotacionadas.
