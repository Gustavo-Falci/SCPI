"""Contabilidade de quem já foi tratado na chamada atual.

Dois estados em vez de um. Antes o aluno entrava em `presentes_chamada` ANTES
do POST: um POST que falhasse nunca era tentado de novo naquela aula e virava
falta indevida silenciosa. Enquanto o backend aceitava quase tudo (resolvia a
chamada globalmente), recusa era rara; com a validação por chamada_id ela virou
caminho normal, e o registro só pode ser dado como resolvido depois que o
servidor responde.

Classe pura: sem rede, sem AWS, sem câmera, sem env — testável isoladamente,
no mesmo molde de scripts/confirmacao_burst.py.

Não é thread-safe por si só: o chamador (SistemaReconhecimento) já serializa
os acessos sob self.lock, e embutir um lock aqui daria a impressão falsa de
que a sequência reivindicar-e-submeter é atômica.
"""


class RegistroPresencaTracker:
    def __init__(self):
        # Reivindicado por um envio em andamento.
        self._em_voo: set[str] = set()
        # Resolvido: registrado com sucesso, ou recusado de forma definitiva
        # (não adianta repetir nesta chamada).
        self._resolvidos: set[str] = set()

    def reivindicar(self, external_id: str) -> bool:
        """True se o chamador ficou responsável por enviar o POST deste aluno."""
        if external_id in self._resolvidos or external_id in self._em_voo:
            return False
        self._em_voo.add(external_id)
        return True

    def concluir(self, external_id: str, *, definitivo: bool) -> None:
        """Fecha o envio.

        `definitivo=True` para sucesso e para recusa que repetir não muda
        (rosto desconhecido, aluno de outra turma, chamada fechada).
        `definitivo=False` para falha transitória (rede, 503) — o próximo burst
        tenta de novo.
        """
        self._em_voo.discard(external_id)
        if definitivo:
            self._resolvidos.add(external_id)

    def tratado(self, external_id: str) -> bool:
        """Resolvido ou em voo: dá para pular o SearchFaces deste crop."""
        return external_id in self._resolvidos or external_id in self._em_voo

    def limpar(self) -> None:
        """Troca de chamada: nada do estado anterior vale para a nova."""
        self._em_voo.clear()
        self._resolvidos.clear()

    def __len__(self) -> int:
        return len(self._resolvidos)
