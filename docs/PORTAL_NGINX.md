# Portal — configuração do nginx

Aplicado em produção em 2026-08-02, em `/etc/nginx/sites-available/scpi`
(server block de `admin.scpi.me`; o mesmo arquivo tem o block de `api.scpi.me`,
então config inválida derruba os dois).

A `<meta http-equiv="Content-Security-Policy">` do `index.html` cobre a maior
parte da política, mas `frame-ancestors` é ignorado quando entregue por meta —
precisa vir como header HTTP. O `Cache-Control` também: os scripts em `js/`
carregados direto no HTML (fora de `<script type="module">`) ficam fora do
esquema `?v=N` usado pelos módulos — não enumerar quais são aqui, para a lista
não desatualizar de novo a cada script novo.

```nginx
server {
    server_name admin.scpi.me;

    root /opt/scpi/portal;
    index index.html;

    # Os quatro no nível do server: valem para index.html, privacy.html, js/,
    # vendor/, fonts/ e css/. Ver "add_header não soma" abaixo antes de mover
    # qualquer um destes para dentro de um location.
    add_header Content-Security-Policy "frame-ancestors 'none'" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Cache-Control "no-cache, must-revalidate" always;

    location ~* ^/(js|vendor|fonts|css)/ {
        try_files $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # ... listen/ssl do Certbot
}
```

Depois de editar: `nginx -t && systemctl reload nginx`. Nunca recarregar sem o
`nginx -t` passar.

## `add_header` não soma, substitui

Um `add_header` dentro de um `location` **descarta** todos os herdados do
server — não acrescenta ao conjunto. A versão anterior deste documento punha só
o `Cache-Control` num `location ~* ^/(js|vendor|fonts)/`, o que fazia todo
arquivo em `js/` perder CSP, `X-Frame-Options` e `X-Content-Type-Options`.
Justamente `nosniff`, que é onde mais importa, ao servir JavaScript.

Daí a forma acima: os quatro headers no server, e nenhum `add_header` em
`location` nenhum. Ao adicionar um header novo específico de um `location`,
repita os quatro junto ou o resto se perde em silêncio — nada quebra, os
headers só somem.

## `try_files` e o 404 dos assets

Sozinho, `try_files $uri $uri/ /index.html` responde `index.html` com status
**200** para `/js/qualquer-coisa.js` que não exista. O browser recebe
`<!doctype html>` onde esperava um módulo e falha com `Unexpected token '<'`,
longe da causa. O `location` dos assets com `try_files $uri =404` faz o que
falta virar 404 de verdade.

## `no-cache` em tudo

`no-cache` significa "revalide antes de usar", não "não cacheie": as respostas
seguintes viram `304` de poucos bytes. Num portal interno e pequeno, o custo é
irrelevante perto de garantir que um `index.html` velho em cache — com a meta
CSP velha junto — não sobreviva ao deploy. Por isso está no server, cobrindo o
HTML, e não só nos assets.

## Verificação

```bash
curl -sI https://admin.scpi.me/            | grep -iE 'content-security|x-frame|x-content|cache-control'
curl -sI https://admin.scpi.me/js/main.js  | grep -iE 'content-security|x-frame|x-content|cache-control'
curl -so /dev/null -w '%{http_code}\n' https://admin.scpi.me/js/nao-existe.js
```

Quatro headers em cada um dos dois primeiros, `404` no terceiro. O segundo é o
que pega o erro de `add_header` em `location`: se vier só `Cache-Control`, os
outros três foram descartados.

## `connect-src` e o host da API

O `connect-src` do CSP (em `index.html` e `privacy.html`) pina
`https://api.scpi.me` e precisa ser editado **junto** com
`window.__SCPI_API_URL__` em `portal/js/env.js` sempre que o host da API mudar
— os dois têm que apontar para o mesmo lugar, senão o browser bloqueia as
chamadas silenciosamente (erro só aparece no console).

Isso vale também para desenvolvimento local: `portal/js/config.js` cai para
`http://localhost:8000` quando `window.__SCPI_API_URL__` não está definido,
mas o `connect-src` pinado em produção não inclui `localhost` — rodando o
portal contra o CSP de produção, as chamadas para `localhost:8000` seriam
bloqueadas. Para desenvolver localmente, ajuste `env.js` e o `connect-src`
juntos (ou sirva o portal sem a meta tag de produção).
