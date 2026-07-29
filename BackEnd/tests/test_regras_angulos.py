"""A lista de ângulos é regra de negócio compartilhada, não detalhe do upload."""


def test_angulos_validos_tem_os_quatro():
    from core.regras import ANGULOS_VALIDOS

    assert ANGULOS_VALIDOS == frozenset({"frontal", "esquerda", "direita", "baixo"})


def test_router_de_upload_usa_a_constante_compartilhada():
    """Cópia local divergiria em silêncio da auditoria que conta ângulos faltantes."""
    import routers.alunos as mod
    from core.regras import ANGULOS_VALIDOS

    assert mod.ANGULOS_VALIDOS is ANGULOS_VALIDOS
