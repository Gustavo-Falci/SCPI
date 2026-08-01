# Portal — configuração do nginx

A `<meta http-equiv="Content-Security-Policy">` do `index.html` cobre a maior
parte da política, mas `frame-ancestors` é ignorado quando entregue por meta —
precisa vir como header HTTP. O `Cache-Control` também: os scripts de boot
(`js/env.js`, `js/boot-sidebar.js`, `js/tailwind-config.js`, `js/boot-gate.js`)
ficam fora do esquema `?v=N` usado pelos módulos.

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
