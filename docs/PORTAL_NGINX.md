# Portal — configuração do nginx

A `<meta http-equiv="Content-Security-Policy">` do `index.html` cobre a maior
parte da política, mas `frame-ancestors` é ignorado quando entregue por meta —
precisa vir como header HTTP. O `Cache-Control` também: os scripts em `js/`
carregados direto no HTML (fora de `<script type="module">`) ficam fora do
esquema `?v=N` usado pelos módulos — não enumerar quais são aqui, para a lista
não desatualizar de novo a cada script novo; o `location` abaixo já cobre
qualquer arquivo em `js/`, `vendor/` ou `fonts/` independente do nome.

Aplicar no server block do portal (`admin.scpi.me`):

```nginx
add_header Content-Security-Policy "frame-ancestors 'none'" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;

location ~* ^/(js|vendor|fonts)/ {
    add_header Cache-Control "no-cache, must-revalidate" always;
}
```

`no-cache` (revalida sempre) em vez de `no-store`: mantém o 304 barato e evita
que uma versão em cache de `js/` sobreviva ao deploy — o problema que o `?v=N`
não resolve para scripts carregados direto no HTML.

Depois de editar: `nginx -t && systemctl reload nginx`.

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
