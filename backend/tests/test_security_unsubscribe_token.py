from app.core.security import generate_unsubscribe_token, verify_unsubscribe_token


def test_generate_and_verify_roundtrip():
    token = generate_unsubscribe_token("C001")
    assert verify_unsubscribe_token(token) == "C001"


def test_verify_token_invalido_devuelve_none():
    assert verify_unsubscribe_token("no-es-un-token-valido") == None


def test_verify_token_manipulado_devuelve_none():
    token = generate_unsubscribe_token("C001")
    # cambiar un caracter del token para simular manipulación
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert verify_unsubscribe_token(tampered) == None


def test_tokens_de_distintas_claves_son_distintos():
    token_a = generate_unsubscribe_token("C001")
    token_b = generate_unsubscribe_token("C002")
    assert token_a != token_b
