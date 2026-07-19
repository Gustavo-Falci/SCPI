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
  # Etapa A — coletar amostras rotuladas (roda na máquina com câmera):
  python scripts/_validar_liveness.py
     Teclas na janela:
       r = salvar amostra ROSTO REAL (você na frente da câmera)
       p = salvar amostra FOTO em PAPEL (mostre foto impressa)
       t = salvar amostra FOTO em TELA  (mostre foto no celular/tablet)
       q = sair (imprime estatísticas de tamanho do rosto)
     Colete ~15-20 de cada, na distância/posição REAL de uso.

  # Etapa B — rodar um modelo ONNX nas amostras coletadas:
  python scripts/_validar_liveness.py --test caminho/modelo.onnx
  python scripts/_validar_liveness.py --test modelo.onnx --preproc minivision

Amostras vão para o scratchpad (não sujam o repo):
  cada amostra = frame inteiro (.jpg) + bbox do YuNet (.txt: "x y w h").
  Guardar o frame bruto deixa qualquer preproc (margem/scale) ser testado depois.
"""
import pathlib
import os
import argparse
import glob

import cv2
import numpy as np

_AQUI = pathlib.Path(__file__).resolve().parent

# Mesmo diretório de amostras entre etapa A e B.
_SAMPLES_DIR = pathlib.Path(
    os.getenv("LIVENESS_SAMPLES_DIR", "")
    or (_AQUI.parent.parent / ".liveness_samples")
)
_LABELS = {"r": "real", "p": "papel", "t": "tela"}


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
# Etapa A — coleta
# ---------------------------------------------------------------------------
def coletar():
    for lbl in _LABELS.values():
        (_SAMPLES_DIR / lbl).mkdir(parents=True, exist_ok=True)

    detector = cv2.FaceDetectorYN.create(_resolver_yunet(), "", (320, 320), 0.6)
    cam_index = int(os.getenv("CAMERA_INDEX", "0"))
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        raise SystemExit(f"Não abriu câmera índice {cam_index}. Ajuste CAMERA_INDEX.")

    contagem = {lbl: len(glob.glob(str(_SAMPLES_DIR / lbl / "*.jpg"))) for lbl in _LABELS.values()}
    print("Coleta iniciada. Posicione na DISTÂNCIA REAL de uso.")
    print("Teclas: [r]eal  [p]apel  [t]ela  [q]sair")

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
            hud = " ".join(f"{l}:{contagem[l]}" for l in _LABELS.values())
            cv2.putText(vis, f"[r]eal [p]apel [t]ela [q]sair  {hud}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow("Fase 0 - coleta liveness", vis)

            k = cv2.waitKey(1) & 0xFF
            tecla = chr(k) if k != 255 else ""
            if tecla == "q":
                break
            if tecla in _LABELS:
                if not box:
                    print("  (nenhum rosto detectado — não salvo)")
                    continue
                lbl = _LABELS[tecla]
                n = contagem[lbl]
                base = _SAMPLES_DIR / lbl / f"{lbl}_{n:03d}"
                cv2.imwrite(str(base) + ".jpg", frame)
                with open(str(base) + ".txt", "w") as fh:
                    fh.write("{} {} {} {}".format(*box))
                contagem[lbl] += 1
                print(f"  salvo {lbl}_{n:03d}  rosto={box[2]}x{box[3]}px")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    _estatisticas_tamanho()


def _estatisticas_tamanho():
    print("\n=== Tamanho do rosto (lado menor do bbox, px) ===")
    for lbl in _LABELS.values():
        lados = []
        for txt in glob.glob(str(_SAMPLES_DIR / lbl / "*.txt")):
            with open(txt) as fh:
                _bx, _by, w, h = (int(v) for v in fh.read().split())
            lados.append(min(w, h))
        if not lados:
            print(f"  {lbl:6s}: (sem amostras)")
            continue
        lados.sort()
        med = lados[len(lados) // 2]
        print(f"  {lbl:6s}: n={len(lados):2d}  min={lados[0]:3d}  "
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
        crop = _crop_com_scale(frame, box, 2.7)
        blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (80, 80), swapRB=False)
        net.setInput(blob)
        out = net.forward().flatten()
        p = _softmax(out)  # [live, print, replay]
        return float(p[0]) if len(p) >= 3 else float(p[0])
    # facenox: 128x128 RGB /255, 2 classes [?]. Best-effort; ajuste se preciso.
    crop = _crop_com_scale(frame, box, 1.4)
    blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (128, 128), swapRB=True)
    net.setInput(blob)
    out = net.forward().flatten()
    p = _softmax(out)
    return float(p[0])  # assume classe 0 = real; VERIFICAR na saída


def _preproc_blob(frame, box, preproc):
    if preproc == "minivision":
        crop = _crop_com_scale(frame, box, 2.7)
        return cv2.dnn.blobFromImage(crop, 1 / 255.0, (80, 80), swapRB=False)
    crop = _crop_com_scale(frame, box, 1.4)
    return cv2.dnn.blobFromImage(crop, 1 / 255.0, (128, 128), swapRB=True)


def _debug_saida_crua(net, preproc):
    """Imprime shape + valores crus do modelo p/ 1 amostra de cada label.
    Revela a interpretação correta do output (índice da classe 'live')."""
    print("\n--- DEBUG saída crua (1 amostra por label) ---")
    for lbl in _LABELS.values():
        txts = sorted(glob.glob(str(_SAMPLES_DIR / lbl / "*.txt")))
        if not txts:
            print(f"  {lbl:6s}: (sem amostras)")
            continue
        jpg = txts[0][:-4] + ".jpg"
        frame = cv2.imread(jpg)
        if frame is None:
            continue
        with open(txts[0]) as fh:
            box = tuple(int(v) for v in fh.read().split())
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
            "=> este modelo exigiria onnxruntime (dep nova). Ponto #2 do advisor."
        )
    print(f"Modelo carregado em cv2.dnn OK. preproc={preproc}")
    _debug_saida_crua(net, preproc)

    resumo = {}
    for lbl in _LABELS.values():
        scores = []
        for txt in sorted(glob.glob(str(_SAMPLES_DIR / lbl / "*.txt"))):
            jpg = txt[:-4] + ".jpg"
            frame = cv2.imread(jpg)
            if frame is None:
                continue
            with open(txt) as fh:
                box = tuple(int(v) for v in fh.read().split())
            try:
                scores.append(_liveness_score(net, frame, box, preproc))
            except cv2.error as e:
                raise SystemExit(f"Falha na inferência ({jpg}):\n  {e}")
        resumo[lbl] = scores

    print("\n=== Liveness score (0=fake .. 1=real) ===")
    for lbl, scores in resumo.items():
        if not scores:
            print(f"  {lbl:6s}: (sem amostras)")
            continue
        scores.sort()
        med = scores[len(scores) // 2]
        print(f"  {lbl:6s}: n={len(scores):2d}  min={scores[0]:.3f}  "
              f"mediana={med:.3f}  max={scores[-1]:.3f}")
    reais = resumo.get("real", [])
    fakes = resumo.get("papel", []) + resumo.get("tela", [])
    if reais and fakes:
        print(f"\nSeparação: min(real)={min(reais):.3f} vs max(fake)={max(fakes):.3f}")
        if min(reais) > max(fakes):
            print("  ✅ Separável — existe limiar que separa real de foto nesta distância.")
        else:
            print("  ⚠️  Sobreposto — não há limiar limpo. Modelo fraco nesta distância; "
                  "considerar fallback (endurecer pose) OU aproximar/melhorar câmera.")


def main():
    ap = argparse.ArgumentParser(description="Fase 0 — validação de anti-spoofing.")
    ap.add_argument("--test", metavar="MODELO.onnx", help="roda modelo nas amostras coletadas")
    ap.add_argument("--preproc", choices=["minivision", "facenox"], default="minivision")
    args = ap.parse_args()
    if args.test:
        testar(args.test, args.preproc)
    else:
        coletar()


if __name__ == "__main__":
    main()
