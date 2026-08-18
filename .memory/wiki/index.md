# Wiki do Projeto SCPI

*Diretório central do conhecimento. Migrado da memória do assistente em 2026-08-05.*

**SCPI** — Sistema de Controle de Presença por reconhecimento facial. Escopo **acadêmico**
(Aluno / Professor / Turma / Chamada), TCC com uso real, sob LGPD.

## Páginas padrão

- [[hot.md]]: contexto imediato e próximos passos. **Ler primeiro.**
- [[log.md]]: changelog append-only das sessões.
- [[stack.md]]: tecnologias, versões, estrutura do repo.
- [[patterns.md]]: convenções de código e armadilhas recorrentes.
- [[bugs.md]]: bugs conhecidos, quirks e pins defensivos.
- [[decisions.md]]: decisões arquiteturais e de produto, com o porquê.

## Páginas de domínio

- [[ops.md]]: servidor de produção, deploy, backups, monitoramento.
- [[seguranca.md]]: auditoria, pentest, hardening, dívida de segurança.
- [[lgpd.md]]: consentimento, export do titular, revogação de biometria.
- [[biometria-camera.md]]: Rekognition, liveness, script de câmera da sala.
- [[dominio.md]]: regras de negócio — chamada, professor, aluno, relatórios, CSV.
- [[portal.md]]: portal administrativo web (`admin.scpi.me`).
- [[app-mobile.md]]: app Expo/React Native.
- [[fluxo-de-trabalho.md]]: como trabalhar com o Gustavo — git, commits, testes.

---

⚠️ **Este diretório É VERSIONADO na `main`** desde 2026-08-16. O repositório
`Gustavo-Falci/SCPI` é **PRIVADO** — a afirmação anterior de que era público (e a
consequente regra de manter a wiki git-ignored) estava errada.

Ainda assim, estas páginas contêm caminhos de produção, IPs, nomes de segredo e dívida de
segurança conhecida: **nunca tornar o repositório público sem sanitizar antes.**

Branch criada antes de 2026-08-16 ainda ignora `.memory/` e **apaga a wiki do disco no
checkout**. Recuperar com `git archive main .memory/wiki | tar -x`.
