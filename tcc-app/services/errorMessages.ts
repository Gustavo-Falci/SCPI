/**
 * Mensagens centralizadas de erro (PT-BR) — SCPI mobile.
 *
 * Mapeia status HTTP e error_codes do backend para mensagens amigáveis.
 * Use `friendlyErrorMessage(error)` para extrair a mensagem mais útil
 * a partir de um erro lançado pelo `services/api.ts`.
 */

/**
 * Mensagens por status HTTP.
 */
export const HTTP_STATUS_MESSAGES: Record<number, string> = {
  400: "Requisição inválida. Confira os dados informados.",
  401: "Sua sessão expirou. Faça login novamente.",
  403: "Você não tem permissão para realizar esta ação.",
  404: "Recurso não encontrado.",
  408: "A requisição demorou demais. Tente novamente.",
  409: "Conflito ao processar a solicitação.",
  413: "Arquivo grande demais para envio.",
  415: "Tipo de arquivo não suportado.",
  422: "Dados inválidos. Confira o formulário.",
  429: "Muitas requisições em pouco tempo. Aguarde alguns segundos.",
  500: "Erro interno do servidor. Tente novamente em instantes.",
  502: "Servidor indisponível no momento.",
  503: "Serviço temporariamente indisponível.",
  504: "O servidor demorou para responder. Tente novamente.",
};

/**
 * Mensagens por error_code do backend (vide BackEnd/core/errors.py).
 */
export const ERROR_CODE_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "E-mail ou senha incorretos.",
  TOKEN_EXPIRED: "Sua sessão expirou. Faça login novamente.",
  TOKEN_INVALID: "Sessão inválida. Faça login novamente.",
  UNAUTHORIZED: "Você precisa estar autenticado para continuar.",
  FORBIDDEN: "Você não tem permissão para realizar esta ação.",
  SESSION_EXPIRED: "Sua sessão expirou. Faça login novamente.",
  VALIDATION_ERROR: "Dados inválidos. Confira o formulário.",
  INVALID_INPUT: "Entrada inválida.",
  MISSING_FIELD: "Preencha todos os campos obrigatórios.",
  NOT_FOUND: "Recurso não encontrado.",
  ALREADY_EXISTS: "Este registro já existe.",
  CONFLICT: "Conflito ao processar a solicitação.",
  ALUNO_NOT_FOUND: "Aluno não encontrado.",
  PROFESSOR_NOT_FOUND: "Professor não encontrado.",
  TURMA_NOT_FOUND: "Turma não encontrada.",
  CHAMADA_FORA_HORARIO: "Você só pode iniciar a chamada durante o horário oficial da aula.",
  CHAMADA_JA_ABERTA: "Já existe uma chamada aberta para esta turma.",
  FACE_NAO_DETECTADA: "Não foi possível detectar um rosto. Posicione-se em local iluminado e tente novamente.",
  FACE_NAO_RECONHECIDA: "Rosto não reconhecido. Tente novamente.",
  FACE_JA_CADASTRADA: "Este rosto já está cadastrado para outro usuário.",
  CONSENTIMENTO_OBRIGATORIO: "É necessário aceitar o consentimento LGPD para o cadastro biométrico.",
  RATE_LIMIT_EXCEEDED: "Muitas tentativas em pouco tempo. Aguarde alguns segundos.",
  INTERNAL_ERROR: "Ocorreu um erro interno. Tente novamente em instantes.",
  SERVICE_UNAVAILABLE: "Serviço temporariamente indisponível.",
  AWS_ERROR: "Falha na comunicação com o serviço de reconhecimento. Tente novamente.",
};

/**
 * Erros típicos de rede sem resposta HTTP.
 */
export const NETWORK_ERROR = "Sem conexão com o servidor. Verifique sua internet.";
export const TIMEOUT_ERROR = "Tempo de resposta esgotado. Tente novamente.";
export const GENERIC_ERROR = "Algo deu errado. Tente novamente.";

/**
 * Estrutura interna usada por `services/api.ts` ao lançar Error.
 * `(error as any).status` e `(error as any).errorCode` quando disponíveis.
 */
export type ApiErrorLike = {
  message?: string;
  status?: number;
  errorCode?: string | null;
};

/**
 * Resolve a mensagem mais amigável a partir de um Error lançado pela API.
 *
 * Ordem de preferência:
 *   1. error_code conhecido
 *   2. detail do backend (já em error.message)
 *   3. mensagem por status HTTP
 *   4. heurísticas de rede (sem internet, timeout)
 *   5. fallback genérico
 */
export function friendlyErrorMessage(
  err: unknown,
  fallback: string = GENERIC_ERROR
): string {
  if (!err) return fallback;

  const e = err as ApiErrorLike;
  const rawMsg = (e.message || "").trim();

  // 1. error_code conhecido
  if (e.errorCode && ERROR_CODE_MESSAGES[e.errorCode]) {
    return ERROR_CODE_MESSAGES[e.errorCode];
  }

  // 2. detail do backend (string útil)
  if (rawMsg && !rawMsg.startsWith("Erro HTTP") && !rawMsg.toLowerCase().includes("network")) {
    return rawMsg;
  }

  // 3. mensagem por status
  if (typeof e.status === "number" && HTTP_STATUS_MESSAGES[e.status]) {
    return HTTP_STATUS_MESSAGES[e.status];
  }

  // 4. erros de rede sem resposta
  const lower = rawMsg.toLowerCase();
  if (lower.includes("network") || lower.includes("failed to fetch")) return NETWORK_ERROR;
  if (lower.includes("timeout") || lower.includes("aborted")) return TIMEOUT_ERROR;

  return rawMsg || fallback;
}
