"""
NanaBuild - Free AI Image Generation Backend
FastAPI server with smart auto-detection for text-to-image,
image editing, and image restoration. No paid API keys required.
"""

import io
import logging
import torch
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
from contextlib import asynccontextmanager
import httpx
import base64

# ─── Gemini Integration ──────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY")
    GEMINI_CLIENT = genai.Client(api_key=api_key)
except ImportError:
    GEMINI_CLIENT = None


# ─── Transformers Fix ────────────────────────────────────────────────────────
# Some versions of transformers (e.g. 5.4.0) may not export CLIPImageProcessor
# directly in the top-level __init__.py, causing diffusers to fail.
try:
    from transformers import CLIPImageProcessor
except ImportError:
    try:
        from transformers.models.clip.image_processing_clip import CLIPImageProcessor
        import transformers
        transformers.CLIPImageProcessor = CLIPImageProcessor
    except ImportError:
        pass

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s")
log = logging.getLogger("nanabuild")

# ─── Global Model Registry ────────────────────────────────────────────────────
models = {
    "pix2pix": None,       # image + prompt → edited image
}

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DTYPE  = torch.float16 if torch.cuda.is_available() else torch.float32

log.info(f"Using device: {DEVICE} | dtype: {DTYPE}")


# ─── Lazy Model Loaders ───────────────────────────────────────────────────────

# (Pix2Pix and other local loaders removed as they are replaced by Gemini)

# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 NanaBuild Studio starting (Translation Mode) …")
    yield
    log.info("👋 NanaBuild Studio shutting down.")


# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="NanaBuild Studio",
    description="Dedicated AI Image-Text Translation Studio using Gemini 3.1 Flash",
    version="1.0.3",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def pil_to_stream(img: Image.Image) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def bytes_to_pil(data: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")


import base64

# ─── Core Pipeline Functions ──────────────────────────────────────────────────

def run_image_edit(image: Image.Image, prompt: str, source_lang: str = "auto", target_lang: str = "target", model_name: str = "gemini-3.1-flash-image-preview") -> Image.Image:
    """Edit an existing image using a specific Gemini model with mandatory language conversion instructions."""
    
    print(f"--- DEBUG TRACE: Model: {model_name} | Source: {source_lang} | Target: {target_lang} ---")
    
    enhanced_prompt = (
        f"### PRIMARY TASK: YOU ARE CURRENTLY GENERATING THE {target_lang.upper()} VERSION OF THIS ADVERTISEMENT ###\n"
        f"### MANDATORY DIRECTIVE: CONVERT ALL TEXT FROM {source_lang.upper()} TO {target_lang.upper()} ###\n\n"
        f"You are a specialized image-text translation engine. Your MANDATORY task is to find EVERY SINGLE piece of text "
        f"currently written in {source_lang.upper()} and convert it into {target_lang.upper()}.\n\n"
        f"STRICT RULES:\n"
        f"1. YOU MUST LOCALIZE ALL TEXT. NO PIECE OF {source_lang.upper()} TEXT SHOULD REMAIN UNCHANGED.\n"
        f"2. IF TEXT IS ALREADY {target_lang.upper()} -> DO NOT TOUCH IT.\n"
        f"3. DO NOT CHANGE ANY OTHER PART OF THE IMAGE (background, colors, theme, objects).\n"
        f"4. Maintain exact font size, style, and positioning for the new text.\n"
        f"5. Refine for professional quality.\n\n"
        "STRICT MECHANICAL RULES:\n"
        f"- Preserve the original background, components, and theme perfectly.\n"
        f"- Render the translated text in the EXACT same font, style, and size as the original.\n"
        f"- Refine the image for a natural, native-look result.\n\n"
        f"USER REQUEST: {prompt} (TARGET LANGUAGE: {target_lang.upper()})"
    )
    
    log.info(f"[image+prompt→edit] {model_name} | Target: {target_lang}")
    
    if GEMINI_CLIENT is None:
        raise HTTPException(status_code=500, detail="Gemini client not initialized.")

    try:
        response = GEMINI_CLIENT.models.generate_content(
            model=model_name,
            contents=[image, enhanced_prompt],
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE']
            )
        )
        
        result_img = None
        if hasattr(response, 'generated_images') and response.generated_images:
            result_img = response.generated_images[0].image
        elif hasattr(response, 'candidates') and response.candidates:
            content = response.candidates[0].content
            if content and hasattr(content, 'parts') and content.parts:
                for part in content.parts:
                    if hasattr(part, 'image') and part.image:
                        result_img = part.image
                        break
                    elif hasattr(part, 'inline_data') and part.inline_data:
                        result_img = Image.open(io.BytesIO(part.inline_data.data))
                        break
        
        if result_img is None:
            raise HTTPException(status_code=500, detail=f"{model_name} did not return an image.")
            
        return result_img

    except Exception as e:
        log.error(f"{model_name} failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini Error ({model_name}): {e}")


# ─── Main Endpoint ────────────────────────────────────────────────────────────

import json

@app.post("/generate")
async def generate(
    prompt: Optional[str] = Form(default=None),
    image:  Optional[UploadFile] = File(default=None),
    source_lang: Optional[str] = Form(default="auto"),
    target_lang: Optional[str] = Form(default="target"),
):
    """Streaming Image-Text Translation Endpoint."""
    print(">>> [API] /generate hit - STREAMING JSON mode active <<<")
    
    if not image:
        raise HTTPException(status_code=400, detail="An image file is required.")
    
    targets = [t.strip() for t in target_lang.split(",") if t.strip()]
    count = len(targets)
    
    if count == 0:
        raise HTTPException(status_code=400, detail="At least one target language must be selected.")
    
    log.info(f">>> [API] target_lang: '{target_lang}' | targets: {targets} | count: {count}")
    
    instruction = prompt if prompt else "REFINE THE IMAGE"
    raw = await image.read()
    pil_img = bytes_to_pil(raw)

    async def event_generator():
        import asyncio
        
        async def process_task(lang, i):
            active_model = "gemini-3.1-flash-image-preview"
            log.info(f"Starting parallel task for {lang} (index {i}) using {active_model}...")
            
            # Offload the synchronous run_image_edit to a separate thread for parallel execution
            result_img = await asyncio.to_thread(
                run_image_edit, pil_img, instruction.strip(), source_lang, lang, active_model
            )
            
            buffered = io.BytesIO()
            result_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return json.dumps({
                "language": lang, 
                "image": img_str, 
                "model": active_model,
                "index": i,
                "total": count
            }) + "\n"

        try:
            # Create tasks for all target languages concurrently
            tasks = [process_task(lang, i) for i, lang in enumerate(targets)]
            
            # Use as_completed to yield each result as soon as it finishes
            for future in asyncio.as_completed(tasks):
                yield await future
                
        except Exception as e:
            log.error(f"Parallel stream error: {e}", exc_info=True)
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": str(DEVICE),
        "models_loaded": {k: v is not None for k, v in models.items()},
    }


# ─── Dev Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
