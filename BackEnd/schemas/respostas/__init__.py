"""Modelos de SAÍDA das rotas — o que o /docs mostra em "Successful Response".

Um arquivo por router, espelhando `routers/`. Estes modelos são declarados
com `responses={200: {"model": X}}`, nunca com `response_model=`: o
`response_model` FILTRA o payload em runtime, e um campo esquecido aqui
sumiria da resposta que o portal e o app já leem. Documentar não pode mudar
comportamento.

A fidelidade de cada modelo é provada em teste — ver
`tests/conformidade_respostas.py` e `tests/test_openapi_respostas.py`.
"""
