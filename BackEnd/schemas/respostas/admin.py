from typing import Literal, Optional

from schemas.respostas.comum import RespostaBase


class ProfessorNaLista(RespostaBase):
    """Professor no seletor do portal — só o que a tela precisa para escolher.

    `professor_id` é a chave da tabela Professores, não o `usuario_id` do
    login: é ele que a atribuição de turma espera receber.
    """

    professor_id: str
    nome: str
    email: str


class TurmaCompleta(RespostaBase):
    """Turma na aba Turmas, já cruzada com professor e matrículas.

    `professor_nome` nunca é `null`: turma sem professor vem com o texto
    "Sem professor", resolvido no próprio SELECT. `total_alunos` é a contagem
    de matrículas, calculada na consulta e não persistida.
    """

    turma_id: str
    nome_disciplina: str
    codigo_turma: str
    turno: Optional[str] = None
    semestre: Optional[str] = None
    periodo_letivo: Optional[str] = None
    professor_nome: str
    total_alunos: int


class HorarioCompleto(RespostaBase):
    """Horário de aula com os dados da turma juntos, para montar a grade.

    `inicio` e `fim` são texto "HH:MM" (formatados no SELECT), não `time`.
    `dia_semana` é 0-6 com 0=segunda — a MESMA convenção do `weekday()` do
    Python, e não a do ISODOW do Postgres usada no histórico do aluno.
    """

    horario_id: str
    turma_id: Optional[str] = None
    dia_semana: Optional[int] = None
    inicio: Optional[str] = None
    fim: Optional[str] = None
    sala: Optional[str] = None
    nome_disciplina: str
    turno: Optional[str] = None
    semestre: Optional[str] = None


class AlunoDaTurmaAdmin(RespostaBase):
    """Aluno matriculado, na visão do Admin.

    O handler renomeia `id` (como sai do SELECT) para `aluno_id` — a rota do
    professor, `GET /turmas/{turma_id}/alunos`, devolve a mesma consulta sem
    renomear. Turma inexistente devolve lista vazia, não 404.
    """

    aluno_id: str
    nome: str
    email: str
    ra: str


class TurmaCriada(RespostaBase):
    """O `turma_id` é gerado no backend (UUID), não vem do cliente — por isso
    volta na resposta: é a única forma de o portal referenciar a turma nova."""

    mensagem: str
    turma_id: str


class MatriculaAplicada(RespostaBase):
    """Resultado de matricular/desmatricular em lote.

    `total_enviados` é quantos IDs o cliente mandou, e a contagem do que
    realmente mudou vai dentro de `mensagem`. Os dois números divergem de
    propósito: aluno já matriculado (ou já fora) não conta como alterado, e o
    portal precisa saber que o pedido inteiro foi recebido mesmo assim.
    """

    mensagem: str
    total_enviados: int


class ProfessorCriado(RespostaBase):
    """A senha temporária NÃO volta no corpo — vai por e-mail. Devolver aqui a
    deixaria em log de proxy e no histórico do navegador."""

    mensagem: str
    usuario_id: str
    email: str


class AlunoCriado(RespostaBase):
    """Dois IDs porque são duas tabelas: `usuario_id` (login) e `aluno_id`
    (cadastro acadêmico, chave de biometria e presença)."""

    mensagem: str
    usuario_id: str
    aluno_id: str
    email: str


class AlunoNaListaAdmin(RespostaBase):
    """Aluno na aba Alunos do portal.

    `ja_matriculado` só é verdadeiro quando a chamada passou
    `contexto_turma_id` (é o modal de matrícula perguntando "este já está na
    turma?"); sem esse parâmetro vem `false` para todo mundo.
    """

    aluno_id: str
    ra: Optional[str] = None
    nome: str
    email: Optional[str] = None
    turno: Optional[str] = None
    turmas_count: int
    tem_biometria: bool
    ja_matriculado: bool


class AlunosPaginados(RespostaBase):
    """`total` já é o total FILTRADO (base da paginação), não o total de alunos.

    `ocultos_pendentes` conta quem ficou de fora só pelo critério de pendência
    — sempre 0 com `situacao=pendentes`, senão a própria lista se contaria como
    oculta.
    """

    items: list[AlunoNaListaAdmin]
    total: int
    ocultos_pendentes: int


class AlunoDoRosto(RespostaBase):
    """Dono do rosto. `null` no item órfão, que por definição não tem dono."""

    aluno_id: str
    nome: Optional[str] = None
    ra: Optional[str] = None


class RostoNoRekognition(RespostaBase):
    """Face da collection cruzada com o banco.

    `divergente` só é calculado quando os DOIS lados da AWS responderam: com um
    faltando, tudo pareceria sem par e a tela acusaria divergência falsa em
    massa — por isso vem `false` junto de `indisponivel` não vazio.
    """

    face_id: Optional[str] = None
    external_image_id: Optional[str] = None
    image_id: Optional[str] = None
    status: Literal["ok", "revogado", "orfao"]
    divergente: bool
    aluno: Optional[AlunoDoRosto] = None
    angulo: Optional[str] = None


class ObjetoNoS3(RespostaBase):
    """Objeto do bucket cruzado com o banco. `last_modified` é ISO 8601."""

    key: str
    size: int
    last_modified: Optional[str] = None
    status: Literal["ok", "revogado", "orfao"]
    divergente: bool
    aluno: Optional[AlunoDoRosto] = None
    angulo: Optional[str] = None


class AlunoDoInventario(RespostaBase):
    """Aluno com biometria ATIVA. Quem não tem nenhum ângulo ativo não aparece
    aqui — é assunto da aba Alunos, não desta."""

    aluno_id: str
    nome: Optional[str] = None
    ra: Optional[str] = None
    angulos_presentes: list[str]
    angulos_faltantes: list[str]
    incompleto: bool


class ContagemDoLado(RespostaBase):
    total: int
    orfaos: int
    revogados: int
    divergentes: int


class ResumoDoInventario(RespostaBase):
    rekognition: ContagemDoLado
    s3: ContagemDoLado
    alunos_incompletos: int


class InventarioBiometrico(RespostaBase):
    """Auditoria cruzada dos três lados, degradando por lado.

    `indisponivel` lista `"rekognition"` e/ou `"s3"` quando aquela listagem da
    AWS falhou: o outro lado ainda chega preenchido, e a tela sabe o que não
    pode afirmar.
    """

    rekognition: list[RostoNoRekognition]
    s3: list[ObjetoNoS3]
    alunos: list[AlunoDoInventario]
    resumo: ResumoDoInventario
    indisponivel: list[Literal["rekognition", "s3"]]
