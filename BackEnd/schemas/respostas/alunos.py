from typing import Literal, Optional

from schemas.respostas.comum import RespostaBase


class PoliticaVigenteNoConsentimento(RespostaBase):
    """Política em vigor AGORA — o front compara com `politica_versao` para
    decidir se pede novo aceite."""

    versao: str
    url: str


class EstadoDoConsentimento(RespostaBase):
    """Estado derivado do último evento da trilha append-only, não de coluna.

    `"nunca"` = nenhum evento registrado; `"ativo"` = último evento é aceite;
    `"revogado"` = último evento é revogação. `politica_versao` pode vir
    `"legado"` em aceite anterior ao versionamento, e `null` quando o estado é
    `"nunca"`. `registrado_em` é ISO 8601.
    """

    estado: Literal["nunca", "ativo", "revogado"]
    politica_versao: Optional[str] = None
    registrado_em: Optional[str] = None
    angulos_cadastrados: list[str]
    politica_vigente: PoliticaVigenteNoConsentimento


class AulaDeHoje(RespostaBase):
    """Aula prevista para hoje, já filtrada pelo turno do aluno.

    `horario` vem pronto para exibição ("19:00 - 20:40"), montado no SELECT —
    o app não recebe início e fim separados nesta tela.
    """

    id: str
    nome: str
    horario: str
    sala: Optional[str] = None


class DashboardDoAluno(RespostaBase):
    """Cabeçalho da tela inicial do aluno.

    `frequencia_geral` é percentual inteiro já arredondado, e vale 0 — não
    `null` — enquanto não houver chamada fechada, para a tela não ter que
    tratar ausência de dado como caso especial.
    """

    nome: str
    frequencia_geral: int
    aulas_hoje: list[AulaDeHoje]


class FrequenciaEmTurma(RespostaBase):
    """Uma turma na tela de frequência.

    `presenca` é o percentual (0 quando a turma ainda não teve aula fechada);
    `total` é o total de AULAS, não de chamadas — uma chamada pode valer duas
    aulas geminadas.
    """

    turma_id: str
    codigo_turma: str
    nome: str
    presenca: int
    total: int
    presencas_count: int
    faltas_count: int


class FrequenciasDoAluno(RespostaBase):
    """`media_geral` é calculada sobre o total de aulas de todas as turmas
    juntas, não é a média dos percentuais por turma — turma com mais aulas
    pesa mais."""

    media_geral: int
    frequencias: list[FrequenciaEmTurma]


class ChamadaNoHistorico(RespostaBase):
    """Uma aula fechada no histórico do aluno.

    `presente` é verdadeiro com QUALQUER aula do slot registrada; quem quer
    distinguir presença cheia de parcial compara `aulas_presentes_count` com
    `total_aulas`. `dia_iso` é o ISODOW do Postgres (1=segunda) e `dia_semana`
    é a sigla já traduzida no backend a partir dele. `tipo_registro` vem
    `"—"` quando não há presença registrada.
    """

    chamada_id: int
    data_chamada: str
    dia_iso: int
    dia_semana: str
    horario_inicio: str
    horario_fim: Optional[str] = None
    total_aulas: int
    aulas_presentes_count: int
    presente: bool
    tipo_registro: str


class HistoricoDeChamadas(RespostaBase):
    """Histórico do aluno numa turma, com os totais já somados.

    Os totais contam AULAS, não chamadas: `total` soma `total_aulas` de cada
    chamada. `parciais` conta as chamadas em que o aluno esteve em algumas
    aulas do slot, mas não em todas — número que não sai de `presentes` nem
    de `ausentes`.
    """

    turma_id: str
    nome_disciplina: str
    codigo_turma: str
    total: int
    presentes: int
    ausentes: int
    parciais: int
    percentual: int
    chamadas: list[ChamadaNoHistorico]


class FotoDeBiometria(RespostaBase):
    """URL presigned do S3 com a validade junto.

    `expira_em_segundos` acompanha a URL porque o link é temporário (300s): o
    cliente que guardá-lo em cache precisa saber quando parar de reusá-lo.
    """

    url: str
    expira_em_segundos: int


class StatusDosAngulos(RespostaBase):
    """Progresso do cadastro biométrico multi-ângulo do aluno.

    `completo` é `total >= 4` (o cadastro padrão), calculado no backend para o
    app não repetir a regra. Rosto revogado não entra na contagem.
    """

    total: int
    angulos_cadastrados: list[str]
    completo: bool
