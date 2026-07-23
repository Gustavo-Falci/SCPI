from unittest.mock import patch

import services.agendador as ag


def test_executar_limpeza_chama_os_tres_purges():
    with patch("repositories.tokens.purgar_tokens_expirados", return_value=1) as t, \
         patch("core.limiter_storage.purgar_rate_limit_buckets", return_value=2) as r, \
         patch("repositories.auth_lockout.purgar_login_attempts", return_value=3) as l:
        result = ag._executar_limpeza()
    assert result == (1, 2, 3)
    t.assert_called_once()
    r.assert_called_once()
    l.assert_called_once()
