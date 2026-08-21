from typing import Literal, Optional, Union

from schemas.respostas.comum import RespostaBase


class TurmaDoFiltro(RespostaBase):
    turma_id: str
    nome_disciplina: Optional[str] = None
    codigo_turma: Optional[str] = None


class ProfessorDoFiltro(RespostaBase):
    professor_id: str
    nome: Optional[str] = None


class OpcoesDeFiltro(RespostaBase):
    """Opções derivadas das chamadas FECHADAS existentes, não do cadastro.

    Assim o usuário não escolhe uma turma sem chamada nenhuma e recebe lista
    vazia sem entender. Na rota do professor o recorte já vem aplicado: só
    turmas dele aparecem. `professores` chega preenchida nas duas rotas — na do
    professor ela lista quem deu as chamadas das turmas dele.
    """

    turmas: list[TurmaDoFiltro]
    professores: list[ProfessorDoFiltro]
    turnos: list[str]
    semestres: list[str]


class ChamadaNoRelatorio(RespostaBase):
    """Uma chamada fechada na listagem, com o resumo de presença já calculado.

    Datas e horas vêm formatadas do banco (`DD/MM/YYYY`, `HH:MM`), não em ISO —
    a tela e o PDF consomem o texto direto.

    Há DOIS contadores de ausência, e eles medem coisas diferentes:
    `ausentes_alunos` conta ALUNOS que não registraram nenhuma presença;
    `ausentes` conta SLOTS vazios (`total_alunos * total_aulas - presentes`), e
    é o que alimenta `percentual`. Numa chamada de 2 aulas, quem faltou a uma
    só entra em `parciais_alunos` e soma 1 em `ausentes`.
    """

    chamada_id: int
    turma_id: str
    nome_disciplina: str
    codigo_turma: Optional[str] = None
    semestre: Optional[str] = None
    turno: Optional[str] = None
    professor_nome: Optional[str] = None
    data_chamada: Optional[str] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    total_aulas: int
    total_alunos: int
    presentes: int
    presentes_alunos: int
    ausentes_alunos: int
    parciais_alunos: int
    ausentes: int
    percentual: int


class RelatoriosPaginados(RespostaBase):
    """Envelope opt-in do `paginado=1`.

    `has_more` é `offset + len(items) < total`, calculado no servidor: o cliente
    não precisa somar offset com tamanho de página para saber se pede a próxima.
    """

    items: list[ChamadaNoRelatorio]
    total: int
    has_more: bool


# O 200 desta rota tem DOIS formatos JSON, escolhidos pelo `paginado`. Declarar
# só a lista esconderia o envelope de quem lê o /docs; declarar só o envelope
# descreveria errado a chamada padrão, que é a que o app faz. A união vira
# `anyOf` no schema e diz a verdade sobre os dois.
ListaOuPaginado = Union[list[ChamadaNoRelatorio], RelatoriosPaginados]


class AlunoNaChamada(RespostaBase):
    """Presença de um aluno na chamada.

    `ra` e `tipo_registro` vêm com `"—"` quando não há valor — o traço é do
    SELECT (`COALESCE`), pensado para cair direto na célula do PDF.
    `presente` é `aulas_presentes_count > 0`: numa chamada de 2 aulas, quem foi
    a uma só é `presente` com `aulas_presentes_count=1`.
    """

    aluno_id: str
    nome: str
    ra: str
    total_aulas: int
    aulas_presentes_count: int
    presente: bool
    tipo_registro: str


class DetalheDaChamada(RespostaBase):
    """Ata de uma chamada fechada: cabeçalho, resumo e a lista de alunos.

    `presentes` conta linhas de Presenças (inclusive de aluno que já saiu da
    turma), enquanto `total_alunos` conta a matrícula atual — é por isso que o
    resumo é calculado aqui e não em SQL.
    """

    chamada_id: int
    turma_id: str
    nome_disciplina: str
    codigo_turma: Optional[str] = None
    semestre: Optional[str] = None
    turno: Optional[str] = None
    professor_nome: Optional[str] = None
    data_chamada: Optional[str] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    total_aulas: int
    total_alunos: int
    presentes: int
    ausentes: int
    percentual: int
    alunos: list[AlunoNaChamada]


class TurmaDaFrequencia(RespostaBase):
    """Cabeçalho da turma. `professor_nome` vem `"—"` em turma sem professor —
    o vínculo é anulável de propósito (excluir professor não apaga histórico)."""

    turma_id: str
    nome_disciplina: str
    codigo_turma: Optional[str] = None
    turno: Optional[str] = None
    semestre: Optional[str] = None
    professor_nome: str


class PeriodoDaFrequencia(RespostaBase):
    """Recorte pedido, ecoado. Ambos `null` significam "sem recorte": o
    relatório cobre todas as chamadas fechadas da turma."""

    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None


class TotaisDaFrequencia(RespostaBase):
    """Números da turma no período.

    `percentual` usa como denominador a SOMA dos denominadores por aluno, não
    `total_alunos * aulas_dadas`: quem se matriculou no meio do período tem
    menos aulas devidas e não pode puxar a média da turma para baixo.
    """

    total_alunos: int
    chamadas: int
    aulas_dadas: int
    presencas: int
    percentual: int


class AlunoNaFrequencia(RespostaBase):
    """Frequência acumulada de um aluno no período.

    `aulas_dadas`/`chamadas_count` são o denominador DELE (só chamadas a partir
    da matrícula); `aulas_dadas_periodo`/`chamadas_periodo_count` são os
    números da turma, repetidos em toda linha porque saem da mesma query.

    `situacao` é `"Insuficiente"` quando `aulas_dadas` é 0 — matrícula depois da
    última chamada do período, por exemplo. Não é `"Risco"`: sem aula devida não
    há amostra para julgar, e 0% ali seria acusação sem base.
    """

    aluno_id: str
    nome: str
    ra: str
    aulas_dadas: int
    chamadas_count: int
    aulas_dadas_periodo: int
    chamadas_periodo_count: int
    aulas_presentes: int
    percentual: int
    situacao: Literal["Regular", "Risco", "Insuficiente"]


class FrequenciaDaTurma(RespostaBase):
    turma: TurmaDaFrequencia
    periodo: PeriodoDaFrequencia
    totais: TotaisDaFrequencia
    alunos: list[AlunoNaFrequencia]
