from typing import Literal, Optional

from schemas.respostas.comum import RespostaBase


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
