"""Crop Doctor: image quality checks + pretrained image classifiers (CNN and transformer) + guidance.
Models run on this computer (free, no key). First use downloads them. Needs: pip install torch transformers pillow
(see install_cnn.ps1). Honest limits: PlantVillage-style models were trained mostly on clean single-leaf photos,
so accuracy drops on messy field photos. Treat results as a first screening, not a diagnosis."""
import json, os, re
import numpy as np

CNN_MODEL = os.getenv("CNN_MODEL", "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification")   # MobileNetV2 CNN, PlantVillage
CROP_MODEL = os.getenv("CROP_MODEL", "wambugu71/crop_leaf_diseases_vit")                                # ViT-tiny: rice, wheat, corn, potato
LOCAL_CNN = os.getenv("LOCAL_CNN", "")   # folder with model.ts and labels.json from train_cnn.py

CROP_WORDS = {"wheat": ["wheat"], "paddy": ["rice", "paddy"], "maize": ["corn", "maize"], "potato": ["potato"], "tomato": ["tomato"]}
ROUTE = {"wheat": [CROP_MODEL], "paddy": [CROP_MODEL], "maize": [CNN_MODEL, CROP_MODEL],
         "potato": [CNN_MODEL, CROP_MODEL], "tomato": [CNN_MODEL], "mustard": []}
MODEL_KIND = {CNN_MODEL: "CNN (MobileNetV2)", CROP_MODEL: "Vision Transformer (ViT-tiny)"}
_CACHE = {}


class Unavailable(RuntimeError):
    pass


# ---------------------------------------------------------------- image quality (plain computer vision)
def image_quality(img):
    """Cheap checks so the farmer retakes a bad photo instead of getting a confident wrong answer.
    Thresholds are heuristics (assumptions)."""
    im = img.convert("RGB")
    w, h = im.size
    im.thumbnail((512, 512))
    a = np.asarray(im, dtype=float)
    gray = a @ np.array([0.299, 0.587, 0.114])
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:])
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = float(((g > r * 1.05) & (g > b * 1.05) & (g > 40)).mean())
    q = {"width": w, "height": h, "sharpness": round(float(lap.var()), 1), "brightness": round(float(gray.mean()), 1),
         "green_share": round(green, 2), "issues": []}
    if min(w, h) < 150:
        q["issues"].append("small")
    if q["sharpness"] < 60:
        q["issues"].append("blurry")
    if q["brightness"] < 45:
        q["issues"].append("dark")
    if q["brightness"] > 220:
        q["issues"].append("bright")
    if green < 0.08:
        q["issues"].append("no_leaf")
    return q


# ---------------------------------------------------------------- labels
def parse_label(raw):
    s = re.sub(r"[()]", "", re.sub(r"[_\-]+", " ", raw.lower())).strip()
    crop = next((c for c, ws in CROP_WORDS.items() if any(w in s for w in ws)), None)
    out = {"raw": raw, "crop": crop, "invalid": ("invalid" in s or "background" in s), "healthy": "healthy" in s}
    if out["healthy"]:
        key = "healthy"
    elif "late blight" in s:
        key = "late_blight"
    elif "early blight" in s:
        key = "early_blight"
    elif "yellow rust" in s or "stripe rust" in s:
        key = "yellow_rust"
    elif "brown rust" in s or "leaf rust" in s:
        key = "brown_rust"
    elif "common rust" in s or ("rust" in s and crop == "maize"):
        key = "common_rust"
    elif "rust" in s:
        key = "brown_rust"
    elif "gray leaf spot" in s or "grey leaf spot" in s or "cercospora" in s:
        key = "gray_leaf_spot"
    elif "northern leaf blight" in s or ("leaf blight" in s and crop == "maize"):
        key = "leaf_blight"
    elif "blast" in s:
        key = "leaf_blast"
    elif "brown spot" in s:
        key = "brown_spot"
    elif "hispa" in s:
        key = "hispa"
    else:
        key = "generic"
    out["key"], out["name"] = key, s.title()
    return out


# ---------------------------------------------------------------- model backends
def _load(model_id):
    if model_id in _CACHE:
        return _CACHE[model_id]
    try:
        import torch  # noqa: F401
        from transformers import AutoImageProcessor, AutoModelForImageClassification
    except ImportError as e:
        raise Unavailable("CNN support is not installed. Run install_cnn.ps1 once, then restart the app.") from e
    proc = AutoImageProcessor.from_pretrained(model_id)
    try:
        model = AutoModelForImageClassification.from_pretrained(model_id)
    except Exception:  # noqa: BLE001 - some community checkpoints need this flag
        model = AutoModelForImageClassification.from_pretrained(model_id, ignore_mismatched_sizes=True)
    model.eval()
    _CACHE[model_id] = (proc, model)
    return _CACHE[model_id]


def _predict_hf(model_id, img):
    """Returns {label: probability} over ALL classes of the model."""
    import torch
    proc, model = _load(model_id)
    inputs = proc(images=img.convert("RGB"), return_tensors="pt")
    with torch.no_grad():
        probs = torch.softmax(model(**inputs).logits[0], dim=-1)
    return {model.config.id2label[i]: float(p) for i, p in enumerate(probs)}


def _predict_local(folder, img):
    import torch
    labels = json.load(open(os.path.join(folder, "labels.json"), encoding="utf-8"))
    model = _CACHE.get(folder) or torch.jit.load(os.path.join(folder, "model.ts")).eval()
    _CACHE[folder] = model
    a = (np.asarray(img.convert("RGB").resize((224, 224)), dtype="float32") / 255 - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = torch.tensor(a.transpose(2, 0, 1)[None], dtype=torch.float32)
    with torch.no_grad():
        p = torch.softmax(model(x)[0], dim=-1)
    return {labels[i]: float(v) for i, v in enumerate(p)}


def predict(model_id, img):
    return _predict_local(model_id[6:], img) if model_id.startswith("local:") else _predict_hf(model_id, img)


# ---------------------------------------------------------------- the pipeline
def _restrict(probs, crop):
    """Keep only classes of the crop the farmer selected, renormalise, and report how much the model believed it is that crop."""
    words = CROP_WORDS[crop]
    keep = {k: v for k, v in probs.items() if any(w in re.sub(r"[_\-]+", " ", k.lower()) for w in words)}
    mass = sum(keep.values())
    if not keep or mass <= 0:
        return None, 0.0
    return sorted(((k, v / mass) for k, v in keep.items()), key=lambda x: -x[1]), mass


def classify(img, crop, predictor=predict):
    quality = image_quality(img)
    models = list(ROUTE.get(crop, []))
    if LOCAL_CNN and crop in CROP_WORDS:
        models.insert(0, "local:" + LOCAL_CNN)
    if not models:
        return {"supported": False, "quality": quality, "models": [], "verdict": None}
    runs = []
    for mid in models:
        ranked, mass = _restrict(predictor(mid, img), crop)
        if not ranked:
            continue
        top = [{"label": k, "score": round(v, 3), **{x: parse_label(k)[x] for x in ("key", "healthy", "invalid", "name")}} for k, v in ranked[:3]]
        runs.append({"model": mid, "kind": MODEL_KIND.get(mid, "Your own CNN" if mid.startswith("local:") else mid),
                     "crop_mass": round(mass, 3), "top": top})
    if not runs:
        return {"supported": True, "quality": quality, "models": [], "verdict": None}
    best = max(runs, key=lambda r: r["top"][0]["score"] * min(1.0, r["crop_mass"] * 2))
    t = best["top"][0]
    agree = None
    if len(runs) > 1:
        agree = len({r["top"][0]["key"] for r in runs}) == 1
    conf = t["score"]
    level = "likely" if (conf >= 0.75 and best["crop_mass"] >= 0.5) else "possible" if conf >= 0.5 else "unsure"
    if agree is False and level == "likely":
        level = "possible"
    if quality["issues"] and level == "likely":
        level = "possible"
    return {"supported": True, "quality": quality, "models": runs,
            "verdict": {"key": "generic" if t["invalid"] else t["key"], "healthy": t["healthy"], "invalid": t["invalid"],
                        "confidence": conf, "level": level, "agree": agree, "crop_mass": best["crop_mass"],
                        "not_this_crop": best["crop_mass"] < 0.3, "name": t["name"]}}
