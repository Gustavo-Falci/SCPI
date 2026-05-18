# Manual de Diretrizes de Segurança da Informação: Do Prompt à Produção

**Versão 2.0** — Este documento estabelece as diretrizes essenciais de segurança cibernética que devem ser implementadas no ciclo de vida de desenvolvimento de sistemas (SDLC), abrangendo desde a concepção de código auxiliada por Inteligência Artificial (Vibe Coding) até a implantação na infraestrutura de nuvem, monitoramento contínuo e resposta a incidentes.

---

## 1. Filosofia de Segurança: Defesa em Profundidade

O princípio fundamental deste manual é a **Defesa em Profundidade**. O sistema não deve depender de uma única barreira de proteção. Se uma camada falhar, outras devem estar prontas para mitigar a ameaça.

* **Isolamento de Camadas:** O cliente (Frontend/Mobile) nunca deve ser considerado confiável. Toda e qualquer regra de validação executada no cliente deve ser obrigatoriamente revalidada no servidor (Backend).
* **Independência de Componentes:** APIs, microsserviços, instâncias de banco de dados e gateways devem possuir suas próprias políticas de segurança independentes, funcionando sob o princípio do **Zero Trust** (Nunca Confiar, Sempre Verificar).
* **Minimização da Superfície de Ataque:** Cada endpoint, porta aberta, dependência ou permissão concedida representa um vetor adicional. Reduza ao mínimo necessário.
* **Falha Segura (Fail Secure):** Em caso de erro, o sistema deve falhar negando acesso, nunca concedendo-o por padrão.

---

## 2. Engenharia de Prompts para Desenvolvimento Seguro (Vibe Coding)

A IA atua como um amplificador de conhecimento. Se as instruções forem negligentes, o código gerado herdará essas vulnerabilidades — e em escala.

### 2.1. Diretrizes de Interação com a IA

1. **Exigência Explícita de Segurança:** Todo prompt destinado a gerar lógicas de negócios críticas deve conter cláusulas de segurança.
2. **Exemplo de Prompt Estruturado:**
   > *"Gere o endpoint de transferência de saldo utilizando a stack FastAPI. Esse código deve mitigar Race Conditions usando operações atômicas ou locks no banco de dados. Mensagens de erro devem ser genéricas e nenhuma variável de ambiente ou segredo deve ser mockado no corpo do código."*
3. **Red Teaming Automatizado:** Antes de realizar o commit de um código gerado por IA, submeta-o a um modelo de linguagem em um novo contexto com a seguinte instrução:
   > *"Atue como um analista de AppSec e realize um pentest estático no código a seguir. Identifique falhas lógicas, de concorrência ou brechas de injeção e apresente a correção."*

### 2.2. Riscos Específicos de Código Gerado por IA

* **Slopsquatting / Alucinação de Pacotes:** Modelos podem sugerir dependências que não existem — atacantes registram esses nomes em repositórios públicos (PyPI, npm) com payloads maliciosos. **Sempre verifique manualmente** se cada `import` corresponde a um pacote legítimo, mantido e amplamente utilizado, antes de instalá-lo.
* **Padrões Desatualizados:** IAs podem reproduzir práticas de anos atrás (ex: `md5` para senhas, `pickle` para desserialização não confiável). Valide criticamente a aderência às práticas atuais.
* **Lógica de Autorização Frouxa:** Modelos tendem a gerar código que "funciona no caminho feliz" sem checar ownership do recurso. Exija explicitamente validação de propriedade em prompts de CRUD.
* **Segredos Mockados:** Não raro a IA inclui chaves, tokens e senhas de exemplo no próprio código. Auditoria pós-geração é obrigatória.

### 2.3. Prompts Adversariais Recomendados

Após gerar uma funcionalidade, execute pelo menos um destes prompts em contexto limpo:

* *"Liste 10 formas pelas quais este endpoint poderia ser abusado por um usuário autenticado mal-intencionado."*
* *"Que dados sensíveis poderiam vazar acidentalmente nas respostas, logs ou mensagens de erro deste código?"*
* *"Este código atende aos princípios de OWASP ASVS nível 2? Justifique."*

---

## 3. Segurança na Camada de Aplicação (Mitigação OWASP Top 10)

### 3.1. Validação de Entradas (Input Validation) e Limitação de Payload

* **Limitação de Tamanho (Max Size):** Todos os payloads de entrada (JSON, strings, formulários) devem ter limites estritos de tamanho máximo definidos nos schemas de validação (ex: Pydantic no FastAPI, serializers no Django). Isso impede ataques de Negação de Serviço (DoS) por exaustão de memória e armazenamento.
* **Sanitização:** Dados textuais recebidos devem ser limpos para evitar *Cross-Site Scripting* (XSS) e *SQL Injection*. Utilize parametrização nativa de ORMs (como Django ORM ou SQLAlchemy) e nunca concatene strings para formar queries executadas diretamente no banco de dados.

#### Upload Seguro de Arquivos

Ao permitir o envio de arquivos:
* Valide a extensão e o tipo MIME declarado.
* Valide os **Magic Bytes** (os primeiros bytes do arquivo) para garantir que um script executável não foi renomeado como `.png` ou `.jpeg`.
* Armazene os arquivos em buckets isolados (AWS S3, OCI Object Storage) e configure os cabeçalhos para evitar a execução de scripts no navegador da vítima (`Content-Disposition: attachment`).

**Errado** (confia apenas no MIME declarado pelo cliente):
```python
if file.content_type == "image/png":
    save(file)
```

**Certo** (valida estrutura real do arquivo):
```python
import magic
header = file.read(2048)
file.seek(0)
real_mime = magic.from_buffer(header, mime=True)
if real_mime not in ALLOWED_MIMES:
    raise ValidationError("Tipo de arquivo não permitido")
```

### 3.2. Controle de Concorrência (Race Conditions)

Em operações que envolvem recursos finitos (transações financeiras, cupons, estoques, votações), garanta a atomicidade através de locks de banco de dados.

**Errado** (duas requisições simultâneas podem debitar duas vezes):
```python
saldo = conta.saldo
if saldo >= valor:
    conta.saldo = saldo - valor
    conta.save()
```

**Certo — Django** (lock em nível de linha dentro de transação):
```python
from django.db import transaction
with transaction.atomic():
    conta = Conta.objects.select_for_update().get(id=conta_id)
    if conta.saldo >= valor:
        conta.saldo -= valor
        conta.save()
```

**Certo — SQLAlchemy:**
```python
with session.begin():
    conta = session.query(Conta).filter_by(id=conta_id).with_for_update().one()
    if conta.saldo >= valor:
        conta.saldo -= valor
```

Independente do framework, o conceito é o mesmo: **row-level locks dentro de uma transação**.

### 3.3. Rate Limiting e Prevenção de Abuso

* Implemente limitadores de requisições baseados no IP do cliente e no token de autenticação.
* Estabeleça políticas diferenciadas de bloqueio (*Lockout*) para endpoints críticos: login, recuperação de senha, processamento de pagamentos, envio de e-mails transacionais.
* **Atenção a proxies/CDN:** Em ambientes atrás de Cloudflare, ALB, ou Nginx, o IP visível na aplicação é o do proxy. Configure adequadamente `X-Forwarded-For` ou `X-Real-IP` e valide a confiabilidade dessa cadeia — caso contrário, atacantes podem forjar o cabeçalho e burlar o rate limit.

### 3.4. Proteção contra CSRF e Configuração de CORS

* **CSRF (Cross-Site Request Forgery):** Para aplicações que usam cookies de sessão, exija tokens CSRF em todas as requisições que mutam estado. APIs stateless com tokens Bearer no header `Authorization` são naturalmente imunes a CSRF clássico.
* **CORS (Cross-Origin Resource Sharing):** Configure listas explícitas de origens permitidas. **Nunca use** `Access-Control-Allow-Origin: *` em conjunto com `Access-Control-Allow-Credentials: true` — essa combinação é uma falha crítica que expõe dados autenticados a qualquer origem.

### 3.5. Cabeçalhos de Segurança HTTP

Configure no servidor ou middleware:
* `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` (HSTS)
* `Content-Security-Policy` restritivo, evitando `unsafe-inline` e `unsafe-eval`
* `X-Content-Type-Options: nosniff`
* `Referrer-Policy: strict-origin-when-cross-origin`
* `Permissions-Policy` para desabilitar APIs do navegador não utilizadas

---

## 4. Autenticação, Autorização e Gestão de Identidade (IAM)

### 4.1. Não Reinvente a Roda

* **Provedores de Identidade (IdP):** É estritamente proibido criar sistemas caseiros de hash de senhas e persistência de sessões, a menos que seja um requisito regulatório estrito. Utilize soluções validadas pelo mercado (AWS Cognito, Firebase Auth, Supabase Auth, Keycloak, Auth0).

### 4.2. Políticas de Senha e MFA

* **Comprimento mínimo de 12 caracteres**, com incentivo a passphrases em vez de complexidade artificial.
* **Verificação contra senhas vazadas** usando a API do *Have I Been Pwned* (k-anonymity) no momento do cadastro e troca.
* **MFA obrigatório** para contas administrativas, financeiras e acessos a sistemas internos. Prefira TOTP (apps como Authy, Google Authenticator) ou WebAuthn/Passkeys a SMS, vulnerável a SIM swap.
* **Algoritmos de hash:** Apenas `Argon2id`, `bcrypt` ou `scrypt`. Nunca MD5, SHA1, ou SHA256 puro para senhas.

### 4.3. Controle de Acesso e IDOR

* **RBAC (Role-Based Access Control):** Implemente controle de acesso baseado em papéis ou permissões granulares explicitamente no backend.
* **Mitigação de IDOR:** Cada requisição para visualizar, editar ou deletar um recurso deve validar se o ID do usuário autenticado realmente possui direitos sobre o ID do objeto solicitado.

**Errado:**
```python
@app.get("/api/v1/pedidos/{pedido_id}")
def get_pedido(pedido_id: int):
    return Pedido.objects.get(id=pedido_id)  # qualquer um vê qualquer pedido
```

**Certo:**
```python
@app.get("/api/v1/pedidos/{pedido_id}")
def get_pedido(pedido_id: int, user = Depends(current_user)):
    pedido = Pedido.objects.get(id=pedido_id, usuario_id=user.id)
    if not pedido:
        raise HTTPException(404)  # nunca 403, evita enumeração
    return pedido
```

Note o `404` em vez de `403`: retornar "proibido" revela que o recurso existe, permitindo enumeração.

### 4.4. Gestão de Sessões e Tokens

* Tokens JWT devem ter **expiração curta** (15–60 minutos) com refresh tokens rotativos.
* Refresh tokens devem ser armazenados em cookies `HttpOnly`, `Secure`, `SameSite=Strict`.
* Implemente **revogação** (blocklist) para logout efetivo e resposta a incidentes.

---

## 5. Criptografia: Dados em Trânsito e em Repouso

### 5.1. Em Trânsito

* **TLS 1.2 no mínimo**, preferencialmente TLS 1.3. Desabilite SSLv3, TLS 1.0 e 1.1.
* Certificados gerenciados via Let's Encrypt, ACM (AWS) ou equivalente, com renovação automatizada.
* HSTS habilitado e, idealmente, inclusão na lista de preload dos navegadores.
* Comunicação interna entre microsserviços também deve ser criptografada (mTLS quando possível), especialmente em ambientes multi-tenant.

### 5.2. Em Repouso

* **Bancos de dados:** Habilite criptografia transparente (TDE) — disponível nativamente em RDS, Cloud SQL, OCI Database.
* **Buckets de objetos:** Ative criptografia server-side (SSE-S3, SSE-KMS).
* **Backups:** São frequentemente esquecidos — devem ser criptografados com o mesmo rigor que os dados primários.

### 5.3. Gestão de Chaves Criptográficas

* Use serviços KMS (AWS KMS, GCP KMS, Azure Key Vault, OCI Vault) — nunca chaves em arquivos no servidor.
* **Rotação periódica:** Chaves de assinatura JWT a cada 90 dias; chaves de dados conforme política regulatória.
* Separação de chaves por ambiente (dev/staging/prod) e por classe de dado.

---

## 6. Gestão de Segredos e Configurações (Secrets Management)

A infraestrutura deve seguir o princípio de que o código fonte pode se tornar público a qualquer momento sem que isso comprometa o ambiente produtivo.

* **Variáveis de Ambiente:** Credenciais, tokens, chaves criptográficas e strings de conexão devem ser injetados estritamente em tempo de execução via variáveis de ambiente (`.env` local, segredos injetados via CI/CD).
* **Cofres de Chaves (Key Vaults):** Para staging e produção, utilize cofres centralizados (AWS Secrets Manager, OCI Vault, HashiCorp Vault, Azure Key Vault).
* **Prevenção de Commits Indesejados:** Configure ferramentas pré-commit (`gitleaks`, `trufflehog`) para impedir que segredos sejam acidentalmente commitados.
* **Varredura do Histórico:** Pré-commit hooks só protegem o futuro. Execute `gitleaks detect --source . --log-opts="--all"` periodicamente para varrer todo o histórico do Git em repositórios legados.
* **Procedimento em Caso de Vazamento:** Se um segredo for commitado, **a rotação é imediata e obrigatória** — remover do histórico via `git filter-repo` não é suficiente, pois o segredo já pode ter sido coletado por crawlers.

---

## 7. Segurança de Dependências e Cadeia de Suprimentos (Supply Chain)

Vulnerabilidades em dependências (Log4Shell, event-stream, xz-utils) demonstraram que código que você não escreveu pode comprometer todo o sistema.

* **Lockfiles obrigatórios:** `package-lock.json`, `yarn.lock`, `poetry.lock`, `Pipfile.lock`, `Cargo.lock`, `go.sum`. Commits nunca devem ignorá-los.
* **SCA (Software Composition Analysis):** Integre `pip-audit`, `npm audit`, `Snyk`, `Dependabot` ou `Renovate` no pipeline para alertar e abrir PRs automáticos de atualização.
* **SBOM (Software Bill of Materials):** Gere e armazene o SBOM (formato CycloneDX ou SPDX) de cada build de produção. Permite resposta rápida a vulnerabilidades publicadas (zero-day em dependência transitiva).
* **Verificação de pacotes sugeridos por IA:** Veja seção 2.2 — *slopsquatting* é vetor crescente.
* **Pinning de versões:** Evite ranges abertos (`^1.0.0`) em produção; prefira versões fixas e atualize conscientemente.

---

## 8. Segurança de Infraestrutura, Nuvem e Deploy

### 8.1. Princípio do Menor Privilégio

* Contas de serviço, contêineres e aplicações devem rodar com o mínimo de permissões necessárias.
* Nunca execute aplicações como usuário `root` dentro de contêineres Docker.
* IAM roles devem ser específicas por função, evitando políticas amplas como `*:*`.

### 8.2. Segurança de Contêineres

* **Imagens base mínimas:** Prefira `distroless`, `alpine`, ou imagens *scratch* quando possível. Menos pacotes = menor superfície de ataque.
* **Scan de imagens:** Integre `Trivy`, `Grype` ou `Snyk Container` no pipeline para detectar CVEs em camadas.
* **Read-only filesystems:** Quando a aplicação não precisa escrever em disco, configure `readOnlyRootFilesystem: true` no Kubernetes.
* **Capabilities:** Drop todas as capabilities do Linux e adicione apenas as estritamente necessárias.
* **Não embuta segredos em layers da imagem** — eles persistem mesmo após `rm`.

### 8.3. Segurança de Rede

* Bancos de dados e instâncias de cache (Redis, Memcached) devem residir em sub-redes privadas, sem IPs públicos.
* Acesso público restrito exclusivamente às portas necessárias (HTTP/HTTPS) via Security Groups e Firewalls de Borda rígidos.
* WAF (Web Application Firewall) na borda — AWS WAF, Cloudflare, OCI WAF — com regras OWASP Core Rule Set.
* Bastion hosts ou acesso via VPN/Zero Trust Network Access (Tailscale, Cloudflare Access) para administração; nunca SSH público.

### 8.4. Monitoramento, Logs e Auditoria

* Auditoria centralizada (Datadog, CloudWatch, Loki, ELK).
* **Logs não devem conter dados sensíveis** (senhas, tokens, números de cartão, CPF completo). Use redaction/masking automatizado.
* Registre: tentativas falhas de autenticação, falhas de autorização, mudanças de privilégio, acessos a recursos administrativos, comportamentos anômalos.
* Configure **alertas acionáveis**, não apenas dashboards. Alertas que ninguém olha são equivalentes a não ter alerta.

**Errado:**
```python
logger.info(f"Login attempt: user={username}, password={password}, token={jwt}")
```

**Certo:**
```python
logger.info("Login attempt", extra={"username": username, "ip": request.ip, "success": False})
```

---

## 9. Conformidade com LGPD e Proteção de Dados Pessoais

Operando no Brasil, o tratamento de dados pessoais é regulado pela Lei Geral de Proteção de Dados (Lei 13.709/2018), com impactos diretos nas decisões de arquitetura.

* **Minimização:** Colete apenas os dados estritamente necessários para a finalidade declarada. Não armazene "por garantia".
* **Finalidade e Base Legal:** Cada coleta deve ter finalidade clara e base legal mapeada (consentimento, execução de contrato, legítimo interesse, etc.).
* **Direitos do Titular:** Implemente endpoints/processos para:
  * Acesso aos dados (portabilidade em formato estruturado).
  * Correção.
  * Exclusão / anonimização (com atenção a obrigações legais de retenção).
* **Dados Sensíveis** (saúde, biometria, origem racial, orientação sexual, dados de crianças): exigem proteções reforçadas — criptografia adicional, controle de acesso restrito, logs de acesso.
* **Retenção:** Defina políticas explícitas de TTL por categoria de dado. Dados não devem viver eternamente.
* **DPIA / RIPD:** Para tratamentos de alto risco, conduza Relatório de Impacto à Proteção de Dados antes do desenvolvimento.
* **Notificação de Incidentes:** A ANPD deve ser notificada em prazo razoável em caso de incidente de segurança envolvendo dados pessoais. Tenha o procedimento documentado.

---

## 10. Testes Automatizados de Segurança (DevSecOps)

A segurança deve ser validada programaticamente no pipeline de CI/CD em múltiplos estágios:

### 10.1. SAST (Static Application Security Testing)

Análise do código-fonte sem executá-lo. Detecta padrões de vulnerabilidade.
* **Python:** `Bandit`, `Semgrep`
* **JavaScript/TypeScript:** `ESLint security plugins`, `Semgrep`
* **Elixir/Phoenix:** `Sobelow`
* **Multi-linguagem:** `SonarQube`, `Semgrep`, `CodeQL`

### 10.2. DAST (Dynamic Application Security Testing)

Testes contra a aplicação em execução, simulando atacantes externos.
* `OWASP ZAP` em modo automatizado contra ambiente de staging.
* `Nuclei` para varredura baseada em templates.

### 10.3. IAST e Fuzzing

* IAST (Interactive AST) combina elementos de SAST e DAST instrumentando a aplicação em testes.
* Fuzzing (`AFL++`, `boofuzz`, libFuzzer) é especialmente valioso para parsers, deserializadores e APIs públicas.

### 10.4. TDD de Segurança (Testes de Abuso)

Escreva testes de integração que tentem **violar** as regras de negócio. O pipeline deve falhar se a violação passar.

Exemplos:
* Tentar acessar painel administrativo com token de usuário comum → esperado 403.
* Enviar valor negativo em rota de transação → esperado 422.
* Acessar `/pedidos/{id}` de outro usuário → esperado 404.
* Enviar payload de 10MB onde o limite é 1MB → esperado 413.
* Login com 100 senhas erradas em 10 segundos → esperado 429 após o limite.

---

## 11. Resposta a Incidentes (Incident Response)

Por mais robusta que seja a prevenção, incidentes ocorrerão. A maturidade de uma equipe é medida pela velocidade e clareza da resposta.

### 11.1. Preparação

* **Runbook documentado** e acessível offline, cobrindo cenários: vazamento de credenciais, comprometimento de servidor, ataque DDoS, ransomware, vazamento de dados pessoais.
* **Contatos de emergência** definidos: DPO, jurídico, comunicação, provedores de nuvem, autoridades (ANPD, CERT.br quando aplicável).
* **Backups testados regularmente** — backup nunca testado é backup que não existe.

### 11.2. Detecção e Contenção

* Critérios claros para classificar severidade (P0–P3).
* Procedimento para **rotação emergencial** de segredos: o que rotacionar, em que ordem, como validar.
* Capacidade de **isolar** rapidamente uma máquina/serviço comprometido sem derrubar a produção inteira.

### 11.3. Erradicação e Recuperação

* Análise de causa raiz (RCA) documentada.
* Patches aplicados antes da restauração de serviço.
* Verificação de persistência (atacantes frequentemente deixam backdoors).

### 11.4. Pós-Incidente

* **Post-mortem sem culpabilização** (blameless), focado em melhorias sistêmicas.
* Atualização deste manual e dos runbooks com lições aprendidas.
* Comunicação transparente com usuários afetados, conforme exigências da LGPD.

---

## 12. Cultura de Segurança

Tecnologia sozinha não protege ninguém. Diretrizes, ferramentas e pipelines funcionam quando incorporados à rotina.

* **Treinamento periódico** da equipe em fundamentos de AppSec e novos vetores (incluindo riscos de uso de IA).
* **Threat modeling** participativo no início de cada feature significativa.
* **Champions de segurança** distribuídos por time, atuando como ponte com a equipe central de segurança.
* **Bug bounty interno ou externo** para incentivar reportes responsáveis.

---

*Este manual é um documento vivo. Deve ser revisado a cada ciclo de auditoria, após cada incidente significativo, e atualizado conforme novas classes de vulnerabilidade emergem no cenário de ameaças.*
