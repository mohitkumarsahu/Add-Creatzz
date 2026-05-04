# 🍌 NanaBuild — Free AI Image Studio

A full-stack AI image generation tool similar to Nano Banana (Google's Gemini image tool),
built entirely with **free, open-source models**. No paid API keys. No cloud costs.

---

## ✨ Features

| Mode | What it does | Model Used |
|---|---|---|
| **Generate** | Text prompt → image | `black-forest-labs/FLUX.1-schnell` |
| **Edit** | Image + prompt → edited image | `timbrooks/instruct-pix2pix` |
| **Restore** | Blurry/distorted image → fixed image | `caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr` |

---

## 🚀 Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the backend
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open the frontend
Just open `index.html` in your browser (double-click or drag into browser).

---

## 💡 Notes

- **First run**: Models are downloaded automatically from HuggingFace (~14 GB for FLUX, ~7 GB for pix2pix, ~160 MB for Swin2SR)
- **GPU**: Automatically used if available (CUDA). CPU works but is slower.
- **Ctrl+Enter** inside any textarea triggers generation.
- The "Use as Input" button sends the generated image directly into Edit mode.

---

## 📁 Structure

```
nanabuild/
├── main.py          ← FastAPI backend (all 3 AI pipelines)
├── index.html       ← Frontend UI (no build step needed)
├── requirements.txt ← Python dependencies
└── README.md
```

---

## 💰 Cost

**$0.** All models run locally on your machine.
