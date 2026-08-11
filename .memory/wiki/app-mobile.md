# App Mobile (Expo / React Native)

Pasta `app/` — renomeada de `tcc-app/` em 2026-06-11; o **slug do Expo segue `tcc-app`**.

## Expo SDK 55

`expo ~55.0.0`, `react-native 0.83.6`, `react 19.2.0`. Upgrade do SDK 54 feito em 2026-05-20
(PR #11) motivado por 6 vulns moderate transitivas que só sumiam no 55.

### Dependabot ignora a stack Expo — desde 2026-05-25

Patterns em `.github/dependabot.yml` (seção npm `/app`): `expo`, `expo-*`, `@expo/*`,
`react`, `react-dom`, `react-native`, `react-native-*`, `@react-native-community/*`,
`@react-navigation/*`, e a toolchain `eslint`, `eslint-config-expo`, `typescript`.

**Qualquer pacote gerenciado pelo SDK só se atualiza via `npx expo install --fix`.**

- **Bumps semver-minor de libs Expo NÃO são seguros** (correção de 2026-05-25): o Dependabot
  rotulou `react-native 0.83→0.85` e reanimated/screens como "minor", mas eles cruzam a
  matriz do SDK 55 e desalinham. PR avulso de pacote SDK-gerenciado → fechar.
- Gap corrigido em 2026-06-11: o ignore não cobria `@react-native-community/*` nem
  `@react-navigation/*`, e a PR #34 desalinhou o `datetimepicker`.
- `eslint-config-expo` **não casa** com o pattern `expo-*` (começa com "eslint"), por isso
  está listado explícito.
- Toolchain travada pelo SDK 55: **`eslint 10` quebra** (`eslint-plugin-react@7.37.5` usa API
  removida → `TypeError: contextOrFilename.getFilename is not a function`). `typescript 6`
  compila limpo mas foi fechado por consistência. Os dois só sobem no SDK 56.
- `expo install --check` lista deps fora da matriz; `--fix` aplica. O SDK 55 **separou as
  flags** (não aceita as duas juntas). `npx expo-doctor` valida o `app.json` contra o schema.

### Detalhes de tipagem/API do SDK 55

- Props removidas do schema: `newArchEnabled` (default true) e `android.edgeToEdgeEnabled`
  (forçado true pelo Android 15).
- Plugins exigidos explicitamente: `expo-font` e `expo-image` no array `plugins`.
- `react/no-unescaped-entities` ficou mais estrita — escapar aspas em JSX com `&apos;`.
- `ColorSchemeName` em RN 0.83 inclui `'unspecified'` além de `'light' | 'dark' | null` —
  **não** usar `?? 'light'`, usar `=== 'dark' ? 'dark' : 'light'`.
- `SymbolViewProps['name']` inclui objeto multi-plataforma `{ios?, android?, web?}` — para
  usar como key de `Record`, aplicar `Extract<..., string>`.
- `useSegments()` do expo-router 55 tipou tuple não-vazia com rotas literais; preferir
  `usePathname()` para detectar index/root.
- TS 5.9 aceita `ignoreDeprecations: "5.0"` apenas.
- `useRouter()` do expo-router devolve singleton de módulo — **seguro em lista de deps**.

## Qualidade

- **Não há testes automatizados no app.** Entraria via `jest-expo`; pulado por decisão.
- CI: job `tsc + eslint (app)` em `tests.yml`. **`--max-warnings 0` mora no script `lint` do
  `package.json`**, não só no CI, para dev e pipeline cobrarem igual.
- `app/expo-env.d.ts` e `.expo/types/` são gitignored e o `tsc` passa sem eles — então
  `npm ci --ignore-scripts` basta no runner.
- Armadilhas de hooks, Modal/SafeArea e DateTimePicker: ver [[patterns.md]].

## Push notifications

Causa raiz da issue #12 (confirmada em 2026-07-16): **zero credencial FCM no EAS**. O token
gerava, mas o Expo não tinha como entregar no Android; `/push/send` retornava ticket `ok` e o
receipt falhava em silêncio.

Fix: projeto Firebase `scpi-6f501`, app Android package `com.gustavofalci.scpi`,
`google-services.json` em `app/` + `googleServicesFile` no `app.json`, e a Service Account Key
FCM V1 subida no EAS. A credencial FCM é **por projeto** e vale dev/preview/prod.

### Chave de API Android

Vive commitada em `app/google-services.json` — **por design**, o arquivo é embarcado no APK e
não é segredo. O GitHub secret scanning abre alerta mesmo assim; qualquer string `AIza…`
dispara.

Restrição aplicada em 2026-07-23 (Google Cloud Console): apps Android com o SHA-1 do keystore
default do EAS + restrição de API. Os três profiles do `eas.json` compartilham esse keystore.

⚠️ **Ao lançar na Play Store:** o profile `production` gera app-bundle e o Google **re-assina**
com a chave do Play App Signing. O SHA-1 do app distribuído passa a ser outro e a restrição
atual **bloqueia o push em produção**. Não é trocar a chave — é **adicionar** o SHA-1 novo
(Play Console → Configuração → Assinatura de apps) à mesma restrição, mantendo o do keystore
EAS para os APKs internos.
**Sintoma se esquecer:** push para de chegar só nos builds vindos da Play Store; o APK preview
continua funcionando. Fácil de diagnosticar errado como bug de token.

### Tickets e receipts — fechados

- **Nível 1**: `send_expo_push` lê os tickets e retorna `{"ok": [...], "dead": [...]}` (deixou
  de retornar `bool`). Só `DeviceNotRegistered` entra em `dead`; a poda é por
  `remover_push_token(expo_token)` — **DELETE por token, não por usuário**, para não apagar
  re-registro. `notificar_alunos_presentes` virou 1 batch (era N requests). Falha de
  transporte ou resposta malformada → retorno vazio, **não poda**.
- **Nível 2**: tabela `PushReceiptsPendentes` (`ticket_id` PK / `expo_token` / `created_at`,
  sem `usuario_id` — a poda é por token), `consultar_receipts` (getReceipts, chunk 1000) e o
  job `scripts/verificar_receipts.py` (`processar` pura + `main` de I/O; idade ≥ 15 min,
  expira em 24 h, aborta com exit 1 se o DB estiver fora). Timer na VM — ver [[ops.md]].

## Débitos conhecidos

- **Push via Expo Go não funciona desde o SDK 53** — validar por EAS dev/preview build.
- **Build iOS local indisponível** (sem Mac) — validar por EAS preview.
- Warning ERESOLVE em `react-native-reanimated@4.2.1` (peerDep `0.78-0.82` vs RN 0.83.6),
  aceito pelo Expo; smoke test confirmou OK.
- `expo-file-system` é módulo nativo: build antigo do app quebra no
  `require("expo-file-system/legacy")` até refazer o build — **não é bug de JS**.
- `@react-native-community/datetimepicker` **não tem build web** (só `.android.js`, `.ios.js`,
  `.windows.js`); em web vira no-op silencioso. O app é mobile-first e **não suporta web**.

## Otimização de polling (P4)

`AppState` pausa o polling em background e faz fetch imediato no `active` **antes** de
rearmar; `buscandoRef` corta a reentrância dos 2 requests em série. **Só rearma se
`chamadaAbertaRef`** — sem essa guarda o resume religa o polling numa chamada já fechada.
O iOS já suspendia timers sozinho; o ganho é Android.
