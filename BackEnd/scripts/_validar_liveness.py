"""Fase 0 — validação empírica de anti-spoofing na câmera REAL de sala.

NÃO é código de produto. Ferramenta descartável para responder duas perguntas
antes de comprometer o design (ver conversa 2026-07-18):

  1) Que tamanho (px) o rosto tem no crop do YuNet na distância real de deploy?
     Modelos passive-liveness (MiniFASNet) são treinados perto (~0.3-1m). Se o
     rosto vier pequeno, o modelo pode degradar (rejeitar aluno real OU deixar
     foto passar). Este é o risco que pode afundar a abordagem.
  2) O modelo ONNX candidato separa rosto-real de foto (papel/tela) NAQUELE
     tamanho? Roda em cv2.dnn sem op não suportada?

Uso:
  # Etapa A — coletar bursts rotulados (roda na máquina COM a câmera da sala).
  # Uma execução por célula da matriz; LIVENESS_COND identifica a célula.
  LIVENESS_COND=2m-celular python scripts/_validar_liveness.py
     Teclas na janela:
       r = ROSTO REAL      p = FOTO em PAPEL
       t = FOTO em TELA    v = VÍDEO em TELA (replay — o ataque desta rodada)
       q = sair (imprime estatísticas de tamanho do rosto)
     Cada tecla grava um BURST de 5 frames em 2s, espelhando BURST_FRAMES /
     BURST_DURACAO_S do produto. Frame solto subestimaria o atacante: o gate
     decide por MAX do burst, então UM frame sortudo já registra presença.
     Colete >= 6 bursts por célula, na distância/posição REAL de uso.

  # Etapa B — rodar um modelo ONNX nas amostras coletadas:
  python scripts/_validar_liveness.py --test scripts/models/best_model.onnx

Amostras: .liveness_samples/<label>/<cond>/burst_NNN/frame_M.{jpg,txt}
  cada frame = frame inteiro (.jpg) + bbox do YuNet (.txt: "x y w h").
  Guardar o frame bruto deixa qualquer preproc (margem/scale) ser testado depois.
  Diretório é git-ignored: são rostos de pessoas reais e o repo é público.
"""
import pathlib
import os
import argparse
import math
import time

import cv2
import numpy as np

_AQUI = pathlib.Path(__file__).resolve().parent

# Mesmo diretório de amostras entre etapa A e B.
_SAMPLES_DIR = pathlib.Path(
    os.getenv("LIVENESS_SAMPLES_DIR", "")
    or (_AQUI.parent.parent / ".liveness_samples")
)
_LABELS = {"r": "real", "p": "papel", "t": "tela", "v": "video"}

# Cadência espelhada do produto (reconhecimento_tempo_real.py): o gate decide
# por MAX de BURST_FRAMES frames em BURST_DURACAO_S. Medir frame solto
# subestima o atacante — basta UM frame acima do limiar para registrar presença.
_BURST_FRAMES = 5
_BURST_DURACAO_S = 2.0

# Célula da matriz de coleta. Setar por execução: LIVENESS_COND=2m-celular
_COND = (os.getenv("LIVENESS_COND") or "").strip() or "sem_cond"


def _resolver_yunet() -> str:
    """Mesma resolução do reconhecimento_tempo_real.py — testa o MESMO detector."""
    model_path = (os.getenv("FACE_MODEL_PATH") or "").strip() or str(
        _AQUI / "models" / "face_detection_yunet_2023mar.onnx"
    )
    if not os.path.exists(model_path):
        raise SystemExit(
            f"Modelo YuNet não encontrado em {model_path}. "
            "Baixe conforme setup (opencv_zoo) ou defina FACE_MODEL_PATH."
        )
    return model_path


def _maior_rosto(faces):
    """Retorna bbox (x,y,w,h) do maior rosto ou None."""
    if faces is None or len(faces) == 0:
        return None
    melhor, area = None, -1
    for f in faces:
        x, y, w, h = (int(v) for v in f[:4])
        if w * h > area:
            melhor, area = (x, y, w, h), w * h
    return melhor


# ---------------------------------------------------------------------------
# Agregação — a conta que define o limiar
# ---------------------------------------------------------------------------
def _max_por_burst(scores_por_burst):
    """MAX de cada burst. Burst sem nenhum score (nenhum rosto detectado) é
    descartado, não vira 0 — 0 mentiria dizendo 'fake perfeito'."""
    return [max(scores) for scores in scores_por_burst if scores]


def _separacao(max_real, max_fake):
    """(R, V, folga) sobre max-por-burst.

    R = min(real): o pior burst de rosto real, o que define falso positivo.
    V = max(fake): o melhor burst de ataque, o que define falso negativo.
    folga = R / V. Devolve (None, None, None) se faltar amostra de um lado.
    """
    if not max_real or not max_fake:
        return None, None, None
    R = min(max_real)
    V = max(max_fake)
    folga = R / V if V > 0 else math.inf
    return R, V, folga


def _meio_geometrico(R, V):
    """Limiar sugerido quando há separação: equidistante em escala log."""
    return math.sqrt(R * V)


def _limiar_sugerido(R, V):
    """Limiar a recomendar. Com V=0 a separação é perfeita e o meio geométrico
    colapsaria em 0 — que o gate lê como 'passa tudo'. Metade do pior burst real
    é a escolha conservadora e continua muito acima de qualquer ataque medido."""
    if V == 0:
        return R / 2
    return _meio_geometrico(R, V)


# ---------------------------------------------------------------------------
# Layout no disco: <raiz>/<label>/<cond>/burst_NNN/frame_M.{jpg,txt}
# `cond` = célula da matriz de coleta (ex.: "2m-celular"), vem de LIVENESS_COND.
# ---------------------------------------------------------------------------
def _descobrir_bursts(raiz, label):
    """[(cond, dir_do_burst)] ordenado. Amostra do layout antigo (frame solto
    direto em <label>/) é ignorada: a spec exige recoletar `real` na mesma
    sessão, então misturar iluminação de julho com a de hoje falsearia R."""
    base = pathlib.Path(raiz) / label
    if not base.is_dir():
        return []
    achados = []
    for cond_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for burst_dir in sorted(p for p in cond_dir.iterdir()
                                if p.is_dir() and p.name.startswith("burst_")):
            achados.append((cond_dir.name, burst_dir))
    return achados


def _proximo_indice_burst(raiz, label, cond):
    """Continua a numeração entre execuções; nunca sobrescreve burst salvo."""
    existentes = [d for c, d in _descobrir_bursts(raiz, label) if c == cond]
    return len(existentes)


# ---------------------------------------------------------------------------
# Etapa A — coleta
# ---------------------------------------------------------------------------
def _gravar_burst(cap, detector, raiz, label, cond):
    """Grava _BURST_FRAMES frames ao longo de _BURST_DURACAO_S.

    Cada frame vira <burst>/frame_M.jpg (frame INTEIRO) + frame_M.txt (bbox do
    YuNet "x y w h"). Guardar o frame inteiro mantém a liberdade de testar
    qualquer margem/scale depois. Frame sem rosto é pulado, não aborta o burst.
    """
    n = _proximo_indice_burst(raiz, label, cond)
    destino = pathlib.Path(raiz) / label / cond / f"burst_{n:03d}"
    destino.mkdir(parents=True, exist_ok=True)

    intervalo = _BURST_DURACAO_S / _BURST_FRAMES
    salvos = 0
    for i in range(_BURST_FRAMES):
        ok, frame = cap.read()
        if not ok:
            print("  (falha ao ler frame — pulado)")
            time.sleep(intervalo)
            continue
        h_img, w_img = frame.shape[:2]
        detector.setInputSize((w_img, h_img))
        _, faces = detector.detect(frame)
        box = _maior_rosto(faces)
        if not box:
            print(f"  frame {i}: sem rosto — pulado")
            time.sleep(intervalo)
            continue
        base = destino / f"frame_{i}"
        cv2.imwrite(str(base) + ".jpg", frame)
        with open(str(base) + ".txt", "w") as fh:
            fh.write("{} {} {} {}".format(*box))
        salvos += 1
        print(f"  frame {i}: rosto {box[2]}x{box[3]}px")
        # waitKey mantém a janela viva durante os 2 s do burst.
        cv2.waitKey(max(1, int(intervalo * 1000)))

    if salvos == 0:
        destino.rmdir()
        print(f"  ⚠️  burst descartado: nenhum frame com rosto.")
    else:
        print(f"  ✅ {label}/{cond}/burst_{n:03d}: {salvos}/{_BURST_FRAMES} frames.")
    return salvos


def coletar():
    detector = cv2.FaceDetectorYN.create(_resolver_yunet(), "", (320, 320), 0.6)
    cam_index = int(os.getenv("CAMERA_INDEX", "0"))
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        raise SystemExit(f"Não abriu câmera índice {cam_index}. Ajuste CAMERA_INDEX.")

    if _COND == "sem_cond":
        print("⚠️  LIVENESS_COND não definida — o relatório não vai conseguir "
              "quebrar por distância/aparelho. Ex.: LIVENESS_COND=2m-celular")
    print(f"Coleta iniciada. Condição: {_COND}")
    print(f"Cada tecla grava {_BURST_FRAMES} frames em {_BURST_DURACAO_S}s.")
    print("Teclas: [r]eal  [p]apel  [t]ela(foto)  [v]ideo  [q]sair")

    # Contagem lida do disco UMA vez e incrementada em memória. Chamar
    # _descobrir_bursts a cada frame do preview seria uma varredura de
    # diretório a 30 fps.
    contagem = {
        lbl: len([1 for c, _ in _descobrir_bursts(_SAMPLES_DIR, lbl) if c == _COND])
        for lbl in _LABELS.values()
    }

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Falha ao ler frame.")
                break
            h_img, w_img = frame.shape[:2]
            detector.setInputSize((w_img, h_img))
            _, faces = detector.detect(frame)
            box = _maior_rosto(faces)

            vis = frame.copy()
            if box:
                x, y, w, h = box
                cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(vis, f"{w}x{h}px", (x, max(0, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            hud = " ".join(f"{lbl}:{contagem[lbl]}" for lbl in _LABELS.values())
            cv2.putText(vis, f"[r][p][t][v] [q]sair  cond={_COND}  {hud}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow("Fase 0 - coleta liveness", vis)

            k = cv2.waitKey(1) & 0xFF
            tecla = chr(k) if k != 255 else ""
            if tecla == "q":
                break
            if tecla in _LABELS:
                if not box:
                    print("  (nenhum rosto no frame de gatilho — burst não iniciado)")
                    continue
                print(f"Burst {_LABELS[tecla]} / {_COND}…")
                if _gravar_burst(cap, detector, _SAMPLES_DIR, _LABELS[tecla], _COND):
                    contagem[_LABELS[tecla]] += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()

    _estatisticas_tamanho()


def _estatisticas_tamanho():
    print("\n=== Tamanho do rosto (lado menor do bbox, px) ===")
    for lbl in _LABELS.values():
        lados = []
        for _cond, burst_dir in _descobrir_bursts(_SAMPLES_DIR, lbl):
            for txt in sorted(burst_dir.glob("*.txt")):
                _bx, _by, w, h = (int(v) for v in txt.read_text().split())
                lados.append(min(w, h))
        if not lados:
            print(f"  {lbl:6s}: (sem amostras)")
            continue
        lados.sort()
        med = lados[len(lados) // 2]
        print(f"  {lbl:6s}: n={len(lados):3d}  min={lados[0]:3d}  "
              f"mediana={med:3d}  max={lados[-1]:3d}")
    print("\nRegra prática: MiniFASNet espera ~80px. Se a mediana do 'real' vier "
          "bem abaixo (ex.: <60px), o modelo provavelmente degrada na distância "
          "real — considerar o fallback de endurecer pose.")


# ---------------------------------------------------------------------------
# Etapa B — testar um modelo ONNX
# ---------------------------------------------------------------------------
def _softmax(v):
    e = np.exp(v - np.max(v))
    return e / e.sum()


def _crop_com_scale(frame, box, scale):
    """Expande o bbox por `scale` mantendo o centro; recorta com clamp."""
    bx, by, w, h = box
    cx, cy = bx + w / 2.0, by + h / 2.0
    lado = max(w, h) * scale
    x1 = int(max(0, cx - lado / 2)); y1 = int(max(0, cy - lado / 2))
    x2 = int(min(frame.shape[1], cx + lado / 2)); y2 = int(min(frame.shape[0], cy + lado / 2))
    return frame[y1:y2, x1:x2]


def _liveness_score(net, frame, box, preproc):
    if preproc == "minivision":
        # garciafido/minifasnet_v2.onnx está QUEBRADO: colapsa em 1 classe
        # (~0.994) p/ real E fake, confirmado nas imagens de demo do minivision
        # via cv2.dnn E onnxruntime. No minivision original classe 1 = real.
        crop = _crop_com_scale(frame, box, 2.7)
        blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (80, 80), swapRB=False)
        net.setInput(blob)
        p = _softmax(net.forward().flatten())
        return float(p[1])  # classe 1 = live (minivision)
    # facenox best_model_quantized: preproc VALIDADO em ground-truth (T/F do
    # minivision) — scale 1.4, RGB (swapRB), /255, classe 0 = live.
    # Separou real=0.998 vs fake=0.000 em close-up. Falta confirmar a 2m.
    crop = _crop_com_scale(frame, box, 1.4)
    blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (128, 128), swapRB=True)
    net.setInput(blob)
    p = _softmax(net.forward().flatten())
    return float(p[0])  # classe 0 = live (facenox)


def _preproc_blob(frame, box, preproc):
    if preproc == "minivision":
        crop = _crop_com_scale(frame, box, 2.7)
        return cv2.dnn.blobFromImage(crop, 1 / 255.0, (80, 80), swapRB=False)
    crop = _crop_com_scale(frame, box, 1.4)
    return cv2.dnn.blobFromImage(crop, 1 / 255.0, (128, 128), swapRB=True)


def _scores_do_burst(net, burst_dir, preproc):
    """Liveness score de cada frame do burst. Frame ilegível é pulado."""
    scores = []
    for txt in sorted(pathlib.Path(burst_dir).glob("*.txt")):
        frame = cv2.imread(str(txt.with_suffix(".jpg")))
        if frame is None:
            continue
        box = tuple(int(v) for v in txt.read_text().split())
        try:
            scores.append(_liveness_score(net, frame, box, preproc))
        except cv2.error as e:
            raise SystemExit(f"Falha na inferência ({txt}):\n  {e}")
    return scores


def _avisar_layout_antigo():
    """Amostra de 2026-07-19 ficava solta em <label>/*.jpg. É ignorada — mas em
    silêncio o operador pensaria que ela entrou na conta."""
    for lbl in _LABELS.values():
        base = _SAMPLES_DIR / lbl
        if base.is_dir() and any(base.glob("*.jpg")):
            print(f"⚠️  {base} tem amostra do layout antigo (frame solto). "
                  "IGNORADA: a spec exige recoletar 'real' na mesma sessão.")


def _scores_por_label(net, preproc):
    """{label: {cond: [max_por_burst]}} — a grandeza que o gate compara."""
    resumo = {}
    for lbl in _LABELS.values():
        por_cond = {}
        for cond, burst_dir in _descobrir_bursts(_SAMPLES_DIR, lbl):
            por_cond.setdefault(cond, []).append(_scores_do_burst(net, burst_dir, preproc))
        resumo[lbl] = {cond: _max_por_burst(bursts) for cond, bursts in por_cond.items()}
    return resumo


def _debug_saida_crua(net, preproc):
    """Imprime shape + valores crus do modelo p/ 1 frame de cada label.
    Revela a interpretação correta do output (índice da classe 'live')."""
    print("\n--- DEBUG saída crua (1 frame por label) ---")
    for lbl in _LABELS.values():
        achados = _descobrir_bursts(_SAMPLES_DIR, lbl)
        txts = sorted(achados[0][1].glob("*.txt")) if achados else []
        if not txts:
            print(f"  {lbl:6s}: (sem amostras)")
            continue
        frame = cv2.imread(str(txts[0].with_suffix(".jpg")))
        if frame is None:
            continue
        box = tuple(int(v) for v in txts[0].read_text().split())
        blob = _preproc_blob(frame, box, preproc)
        net.setInput(blob)
        out = net.forward()
        raw = out.flatten()
        print(f"  {lbl:6s}: shape={out.shape} raw={np.round(raw, 4).tolist()} "
              f"softmax={np.round(_softmax(raw), 4).tolist()}")
    print("--- fim debug ---\n")


def testar(modelo_path, preproc):
    if not os.path.exists(modelo_path):
        raise SystemExit(f"Modelo não encontrado: {modelo_path}")
    try:
        net = cv2.dnn.readNetFromONNX(modelo_path)
    except cv2.error as e:
        raise SystemExit(
            f"cv2.dnn NÃO carregou o ONNX (possível op não suportada):\n  {e}\n"
            "=> este modelo exigiria onnxruntime (dep nova)."
        )
    print(f"Modelo carregado em cv2.dnn OK. preproc={preproc}")
    _avisar_layout_antigo()
    _estatisticas_tamanho()
    _debug_saida_crua(net, preproc)

    resumo = _scores_por_label(net, preproc)

    print("=== max-por-burst (0=fake .. 1=real) — a grandeza que o gate usa ===")
    for lbl, por_cond in resumo.items():
        if not por_cond:
            print(f"  {lbl}: (sem amostras)")
            continue
        print(f"  {lbl}:")
        for cond in sorted(por_cond):
            m = sorted(por_cond[cond])
            if not m:
                print(f"    {cond:16s}: (nenhum burst com rosto)")
                continue
            print(f"    {cond:16s}: n={len(m):2d}  min={m[0]:.3f}  "
                  f"mediana={m[len(m) // 2]:.3f}  max={m[-1]:.3f}")

    reais = [v for m in resumo.get("real", {}).values() for v in m]
    videos = [v for m in resumo.get("video", {}).values() for v in m]
    _imprimir_desfecho(reais, videos, resumo.get("video", {}))


def _imprimir_desfecho(reais, videos, video_por_cond):
    """Tabela de desfecho da spec 2026-08-05."""
    R, V, folga = _separacao(reais, videos)
    if R is None:
        print("\n⚠️  Sem amostra de 'real' ou de 'video' — nada a concluir. "
              "Colete os dois na MESMA sessão (spec: iluminação desloca o score).")
        return

    print(f"\n=== Desfecho ===\n  R = min(max_burst(real))  = {R:.4f}"
          f"\n  V = max(max_burst(video)) = {V:.4f}\n  folga = R/V = {folga:.2f}x")
    if R > V and folga >= 2.0:
        print(f"  ✅ SEPARADO com folga. Subir TEXTURE_LIVENESS_MIN para "
              f"{_limiar_sugerido(R, V):.4f}. Nenhum código novo no loop.")
    elif R > V:
        print(f"  ⚠️  SEPARADO, folga fina (<2x). Limiar sugerido "
              f"{_limiar_sugerido(R, V):.4f} MAIS camada anti-replay "
              f"(bezel/moiré) nas condições que encostam.")
    else:
        print("  ❌ SOBREPOSTO — não há limiar que separe. Camada anti-replay "
              "é obrigatória.")

    if video_por_cond:
        pior = max(video_por_cond.items(), key=lambda kv: max(kv[1], default=0.0))
        print(f"  Condição de ataque mais forte: {pior[0]} "
              f"(max={max(pior[1], default=0.0):.4f})")


def main():
    ap = argparse.ArgumentParser(description="Fase 0 — validação de anti-spoofing.")
    ap.add_argument("--test", metavar="MODELO.onnx", help="roda modelo nas amostras coletadas")
    # facenox é o default: garciafido/minivision onnx testado veio quebrado.
    ap.add_argument("--preproc", choices=["minivision", "facenox"], default="facenox")
    args = ap.parse_args()
    if args.test:
        testar(args.test, args.preproc)
    else:
        coletar()


if __name__ == "__main__":
    main()
