# Planejamento: SCPI → Sistema de Ponto Facial

## Visão Geral

Migrar o SCPI de sistema de chamada escolar para **sistema de registro de ponto por reconhecimento facial** para empresas, em conformidade com a **Portaria 671/2021** (MTb).

---

## 1. O que REAPROVEITAR do código atual

| Módulo Atual                | Novo Uso                                                     | Esforço    |
| ---------------------------- | ------------------------------------------------------------ | ----------- |
| `capture_camera.py`        | Captura facial do funcionário                               | Baixo       |
| `rekognition_aws.py`       | Identificação do funcionário                              | Baixo       |
| `aws_clientes.py`          | Conexão AWS S3 + Rekognition                                | Nenhum      |
| `utils.py` (formatar_nome) | Gerar ID facial do funcionário                              | Baixo       |
| `auth_utils.py`            | Login de gestores/RH                                         | Baixo       |
| `database.py`              | Conexão com banco                                           | Nenhum      |
| `config.py`                | Configurações                                              | Baixo       |
| `api.py`                   | Adaptar endpoints                                            | Médio      |
| `db_operacoes.py`          | **Reescrever SQL**                                     | Alto        |
| `main.py`                  | **Novo menu/cli** → depois será substituído por API | Alto        |
| `mobile/` (React Native)   | App do funcionário                                          | Médio-Alto |

---

## 2. O que MUDAR

### 2.1. Schema do Banco de Dados

**Tabelas atuais:**

- `Usuarios`, `Alunos`, `Professores`, `Turmas`, `Chamadas`, `Presencas`, `Turma_Alunos`, `Colecao_Rostos`

**Novas tabelas necessárias:**

```sql
Empresas          -- id, cnpj, razao_social, endereco, configuracoes
Funcionarios      -- id, empresa_id, usuario_id, cpf, cargo, departamento, data_admissao, jornada_entrada, jornada_saida
Setores           -- id, empresa_id, nome
Registros_Ponto   -- id, funcionario_id, timestamp, tipo (entrada/saida/intervalo_inicio/intervalo_fim), metodo (facial/mobile/web), ip, foto_s3_path, latitude?, longitude?
Jornadas          -- id, funcionario_id, data, entrada, saida_almoco, volta_almoco, saida, horas_trabalhadas, horas_extras
Aprovacoes        -- id, registro_id, justificativa, status (aprovado/rejeitado/pendente)
Dispositivos      -- id, empresa_id, nome, tipo (kiosk/web/mobile), ip, serial
Auditoria_Ponto   -- id, acao, usuario_id, timestamp, detalhes  (obrigatório por lei)
```

### 2.2. Lógica de Negócio

| Funcionalidade         | Descrição                                                                |
| ---------------------- | -------------------------------------------------------------------------- |
| Registrar ponto        | Reconhece rosto → registra timestamp → tipo automático (entrada/saída) |
| Tipos de registro      | Entrada, saída almoço, volta almoço, saída final                       |
| Jornada configurável  | Cada empresa define horários padrão                                      |
| Horas extras           | Cálculo automático                                                       |
| Exportação           | Relatório em PDF/CSV conforme Portaria 671                                |
| Ajustes/justificativas | Funcionário justifica, gestor aprova                                      |
| Dashboard              | Visão de presença/ausência em tempo real                                |
| Kiosk mode             | App/web para ponto presencial na empresa                                   |
| Mobile                 | Ponto remoto com geolocalização + selfie para home office                |

---

## 3. Fases de Implementação

### Fase 1 — Fundação (Backend)

- [ ] Criar novas tabelas no banco (migration)
- [ ] Adaptar `db_operacoes.py` com as novas operações
- [ ] Criar tabela `Empresas` e `Funcionarios`
- [ ] CRUD de empresas (criar, listar, editar)
- [ ] CRUD de funcionários por empresa
- [ ] Função `registrar_ponto(funcionario_id, tipo, método)`
- [ ] Função `identificar_funcionario_e_registrar(foto_bytes)`
- [ ] Função `calcular_jornada(data, funcionario_id)`
- [ ] Sistema de logs/auditoria (obrigatório)

### Fase 2 — API REST

- [ ] `POST /api/empresas` — criar empresa
- [ ] `POST /api/empresas/{id}/funcionarios` — cadastrar funcionário
- [ ] `POST /api/ponto/registrar` — registrar ponto (com foto)
- [ ] `POST /api/ponto/reconhecer` — identificar rosto e registrar
- [ ] `GET /api/ponto/historico/{funcionario_id}` — histórico
- [ ] `GET /api/ponto/relatorio/{empresa_id}` — relatório geral
- [ ] `GET /api/ponto/dashboard/{empresa_id}` — visão do dia
- [ ] `POST /api/ponto/justificar` — justificativa
- [ ] `PATCH /api/ponto/aprovar/{id}` — aprovar/rejeitar
- [ ] `GET /api/exportar/{empresa_id}` — exportar relatório

### Fase 3 — Reconhecimento Adaptado

- [ ] Adaptar `reconhecimento_tempo_real.py` para modo "ponto"
- [ ] Determinar tipo de registro automaticamente (1º reconhecimento = entrada, 2º = saída almoço, etc.)
- [ ] Capturar metadata: timestamp, IP, foto
- [ ] Registrar em `Registros_Ponto` + `Auditoria_Ponto`

### Fase 4 — Mobile (App do Funcionário)

- [ ] Tela de login
- [ ] Botão "Bater Ponto" com captura de selfie
- [ ] Geolocalização (registro de coordenadas)
- [ ] Histórico de pontos do funcionário
- [ ] Notificações (esqueceu de bater ponto, etc.)
- [ ] Solicitar justificativa

### Fase 5 — Web Dashboard (Gestor/RH)

- [ ] Dashboard com presença/ausência do dia
- [ ] Lista de funcionários
- [ ] Relatório de horas trabalhadas/extras
- [ ] Aprovação de justificativas
- [ ] Exportar relatório (Portaria 671)
- [ ] Configuração de jornadas

### Fase 6 — Conformidade Legal (Portaria 671/2021)

- [ ] Tratamento de dado biométrico conforme LGPD
- [ ] Termo de consentimento
- [ ] Registro auditável e imutável
- [ ] Arquivo AFRMM (formato exigido pelo MTE)
- [ ] Prevalidação do ponto (sem edição direta)
- [ ] Separador de registros inválidos

---

## 4. Prioridade: por onde começar

Sugiro esta ordem:

1. **Novo schema** — criar migration para as tabelas novas
2. **CRUD de Empresas e Funcionários** — base de tudo
3. **Registro de ponto básico** — função que recebe foto → identifica → registra
4. **API** — expor as operações via REST
5. **Mobile** — app simples para bater ponto
6. **Dashboard** — visão do gestor
7. **Conformidade** — ajustar conforme exigências legais

---

## 5. Notas Técnicas

- **Foto de registro**: cada ponto deve guardar a foto que identificou o funcionário (auditoria)
- **Timestamp**: usar UTC + timezone da empresa para conformidade
- **Tipos de ponto**: `entrada`, `saida_intervalo`, `retorno_intervalo`, `saida_final`
- **Geolocalização**: opcional para kiosk, obrigatório para mobile remoto
- **LGPD**: dado facial é dado sensível → precisa consentimento explícito por escrito/digital
- **AWS Rekognition**: considerar custo por chamada — para alto volume, avaliar modelo local (FaceNet/deepface)
