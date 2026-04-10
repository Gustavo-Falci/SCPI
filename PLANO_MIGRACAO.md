# Plano de Migração — Sistema de Ponto Facial Empresarial

## Contexto

O sistema era um TCC acadêmico de controle de frequência por reconhecimento facial (alunos/professores). A equipe decidiu pivotar para um **sistema de ponto para funcionários em empresas**. O usuário já iniciou a migração: o schema do banco, a estrutura das telas e a API foram parcialmente reescritos, mas o sistema está quebrado — imports apontam para módulos deletados, o login redireciona para rotas inexistentes, e todas as telas usam dados mockados.

**Objetivo:** Tornar o sistema funcional de ponta a ponta com 3 papéis (Admin, RH, Funcionário), API protegida por JWT, e todas as telas consumindo dados reais.

---

## Fase 1 — Corrigir Backend (imports, terminologia, auth) ✅ (CONCLUÍDO)

### 1.1 Corrigir imports quebrados

| Arquivo | Import antigo | Import novo |
|---|---|---|
| `BackEnd/api.py` | `db_operacoes` | `db_repositorio` |
| `BackEnd/api.py` | `rekognition_aws` | `rekognition_servico` |
| `BackEnd/api.py` | `aws_clientes` | `aws_conexao` |
| `BackEnd/api.py` | `utils` | `formatadores` |
| `BackEnd/api.py` | `auth_utils` | `auth` |
| `BackEnd/db_repositorio.py` | `database` | `db_conexao` |
| `BackEnd/db_repositorio.py` | `auth_utils` | `auth` |
| `BackEnd/setup_db.py` | `database` | `db_conexao` |
| `BackEnd/setup_db.py` | `auth_utils` | `auth` |
| `BackEnd/cli.py` | `database`, `db_operacoes`, `aws_clientes`, `rekognition_aws`, `capture_camera`, `utils` | `db_conexao`, `db_repositorio`, `aws_conexao`, `rekognition_servico`, `captura_webcam`, `formatadores` |

### 1.2 Renomear terminologia "aluno" → "funcionario"

- **`BackEnd/rekognition_servico.py`**: `reconhecer_aluno_por_bytes` → `reconhecer_funcionario_por_bytes`
- **`BackEnd/formatadores.py`**: docstring "aluno" → "funcionário"
- **`BackEnd/api.py`**: chamada e path S3 `alunos/` → `funcionarios/`
- **`BackEnd/cli.py`**: chamadas que usam nomes antigos

### 1.3 Adicionar proteção JWT nas rotas

- Criar dependência `get_current_user()` com `HTTPBearer` + verificação de token
- Aplicar em todas as rotas exceto login, register e health check

### 1.4 Adicionar endpoints faltantes

- `GET /setores/{empresa_id}` — listar setores
- `GET /usuarios/me` — perfil do usuário logado
- `GET /empresas/{empresa_id}` — dados da empresa

---

## Fase 2 — Corrigir Login e Roteamento no Frontend ✅ (CONCLUÍDO)

- Salvar `usuario_id`, `empresa_id`, `user_role` no SecureStore
- Roteamento: Admin → `/admin/home`, RH → `/rh/home`, Funcionário → `/funcionario/home`
- Para Funcionário: obter e salvar `funcionario_id`

---

## Fase 3 — Criar Seção RH (4 arquivos novos) ✅ (CONCLUÍDO)

- `rh/home.tsx` — Dashboard RH
- `rh/funcionarios.tsx` — Cadastro de funcionários
- `rh/relatorios.tsx` — Relatórios de ponto
- `rh/perfil.tsx` — Perfil + logout

---

## Fase 4 — Conectar Todas as Telas à API Real ✅ (CONCLUÍDO)

- Atualizar `services/api.js` com auth headers e novas funções
- Substituir dados mock em todas as telas admin e funcionário

---

## Fase 5 — Criar Telas Faltantes e Corrigir Perfis ✅ (CONCLUÍDO)

- Criar `admin/perfil.tsx`
- Atualizar `funcionario/perfil.tsx` com dados reais

---

## Fase 6 — Validação

1. `python setup_db.py`
2. `uvicorn api:app --reload`
3. Testar login → token → rotas protegidas
4. App: login → roteamento → ponto facial → histórico
5. CLI: cadastro e reconhecimento
