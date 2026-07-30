/**
 * Gate de `npm audit` com allowlist de advisories aceitas conscientemente.
 *
 * O `npm audit` não tem equivalente ao `--ignore-vuln` do pip-audit: ou o gate
 * bloqueia tudo de severidade high+, ou não bloqueia nada. Quando uma advisory
 * não tem correção possível (patch só existe em major incompatível, sem backport),
 * a única saída seria baixar o gate para `moderate`/`critical` — e aí advisory
 * high NOVA passaria batido. Este script mantém o bloqueio em high+ e abre
 * exceção só para IDs listados abaixo, com justificativa.
 *
 * Uso: npm audit --json | node ../.github/scripts/npm-audit-gate.mjs
 */

/**
 * Advisories de severidade high+ aceitas conscientemente.
 * Toda entrada precisa de motivo e de condição de saída (o que destrava a remoção).
 */
const ALLOWLIST = {
  "GHSA-mh99-v99m-4gvg": {
    pacote: "brace-expansion",
    motivo:
      "DoS por expansão sem limite (CVE-2026-14257). JÁ CORRIGIDO na árvore: " +
      "overrides pinam 1.1.18 (backport publicado em 2026-07-30, mantém a API " +
      "callable que minimatch@3 exige) e 5.0.9 (o 5.0.8 do advisory deixou " +
      "expandSequence e o acúmulo de `values` sem teto de maxLength). " +
      "O alerta persiste porque o range da advisory é `<= 5.0.7` em semver puro, " +
      "que engloba o ramo 1.x inteiro — inclusive o 1.1.18 já corrigido.",
    remover_quando:
      "o GitHub corrigir o range da advisory para excluir o 1.x corrigido " +
      "(ou expo/react-native/eslint migrarem para glob 10+, eliminando " +
      "minimatch@3 da árvore).",
  },
};

const BLOQUEIA = new Set(["high", "critical"]);

/** Extrai o ID GHSA-... da URL do advisory. */
function idDoAdvisory(url) {
  const match = /\/(GHSA-[\w-]+)$/.exec(url ?? "");
  return match ? match[1] : null;
}

async function lerStdin() {
  const partes = [];
  for await (const parte of process.stdin) partes.push(parte);
  return Buffer.concat(partes).toString("utf8");
}

const bruto = await lerStdin();

let relatorio;
try {
  relatorio = JSON.parse(bruto);
} catch {
  console.error("Não foi possível parsear a saída do `npm audit --json`.");
  console.error(bruto.slice(0, 2000));
  process.exit(1);
}

if (!relatorio.vulnerabilities) {
  console.error("Saída do `npm audit --json` sem o campo `vulnerabilities`.");
  process.exit(1);
}

// Uma advisory aparece em vários pacotes da cadeia (cada `via` objeto é a raiz
// real; strings são "depende de pacote vulnerável"). Dedupe pelo ID.
const encontradas = new Map();
for (const vuln of Object.values(relatorio.vulnerabilities)) {
  for (const via of vuln.via) {
    if (typeof via !== "object") continue;
    const id = idDoAdvisory(via.url);
    if (!id || encontradas.has(id)) continue;
    encontradas.set(id, {
      id,
      pacote: via.name,
      severidade: via.severity,
      titulo: via.title,
      url: via.url,
    });
  }
}

const bloqueantes = [...encontradas.values()].filter(
  (a) => BLOQUEIA.has(a.severidade) && !ALLOWLIST[a.id],
);

// Allowlist que não corresponde mais a nada na árvore vira lixo silencioso:
// avisa para a exceção não sobreviver ao problema que a justificava.
const obsoletas = Object.keys(ALLOWLIST).filter((id) => !encontradas.has(id));
for (const id of obsoletas) {
  console.log(
    `::notice::${id} (${ALLOWLIST[id].pacote}) está na allowlist mas não aparece ` +
      `mais no audit — remova a entrada de .github/scripts/npm-audit-gate.mjs.`,
  );
}

for (const id of Object.keys(ALLOWLIST)) {
  if (encontradas.has(id)) {
    console.log(`Ignorada (risco aceito): ${id} — ${ALLOWLIST[id].pacote}`);
  }
}

if (bloqueantes.length > 0) {
  console.error(`\n${bloqueantes.length} advisory high+ fora da allowlist:\n`);
  for (const a of bloqueantes) {
    console.error(`  [${a.severidade}] ${a.pacote} — ${a.titulo}`);
    console.error(`    ${a.url}`);
  }
  console.error(
    "\nCorrija a dependência ou, se o risco for aceito conscientemente, " +
      "adicione o ID à ALLOWLIST em .github/scripts/npm-audit-gate.mjs com motivo.",
  );
  process.exit(1);
}

const { high = 0, critical = 0 } = relatorio.metadata?.vulnerabilities ?? {};
console.log(
  `Nenhuma vulnerabilidade high+ fora da allowlist ` +
    `(${high} high / ${critical} critical no relatório, todas em cadeias já cobertas).`,
);
