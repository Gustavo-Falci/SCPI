"""Testes do módulo de integridade do export LGPD."""
from infra.export_integridade import calcular_integridade, verificar_integridade


def test_sha256_do_payload_canonico():
    dados = {"b": 2, "a": 1}
    resultado = calcular_integridade(dados, hmac_key="testkey")
    # JSON canônico ordena chaves: {"a":1,"b":2}
    assert resultado["sha256"] == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"


def test_hmac_difere_com_chave_diferente():
    dados = {"x": 1}
    r1 = calcular_integridade(dados, hmac_key="key1")
    r2 = calcular_integridade(dados, hmac_key="key2")
    assert r1["hmac_sha256"] != r2["hmac_sha256"]
    assert r1["sha256"] == r2["sha256"]


def test_manifesto_contem_metadados():
    dados = {"x": 1}
    resultado = calcular_integridade(dados, hmac_key="k")
    assert resultado["algoritmo"] == "HMAC-SHA256"
    assert resultado["versao_schema"] == "1.0"
    assert "gerado_em" in resultado


def test_verificar_integridade_valida():
    dados = {"x": 1}
    manifesto = calcular_integridade(dados, hmac_key="k")
    assert verificar_integridade(dados, manifesto, hmac_key="k") is True


def test_verificar_integridade_invalida_se_dados_mudam():
    dados = {"x": 1}
    manifesto = calcular_integridade(dados, hmac_key="k")
    dados["x"] = 2
    assert verificar_integridade(dados, manifesto, hmac_key="k") is False


def test_verificar_integridade_invalida_se_chave_errada():
    dados = {"x": 1}
    manifesto = calcular_integridade(dados, hmac_key="k1")
    assert verificar_integridade(dados, manifesto, hmac_key="k2") is False
