import os
import sys
import json
import random
import time
from huggingface_hub import InferenceClient

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from google import genai
from google.genai import types
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
hf_token = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")

app = FastAPI(title="The Pitch Visualizer")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="static/images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/images", exist_ok=True)

HF_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "stabilityai/stable-diffusion-2-1",
    "runwayml/stable-diffusion-v1-5"
]


class StoryRequest(BaseModel):
    story_text: str
    style: str
    llm_model: str = "gemini-2.5-flash"


def generate_storyboard_prompts(text: str, style: str, llm_model: str = "gemini-2.5-flash") -> dict:
    prompt = f"""
You are an expert storyboard director AND a professional AI image prompt engineer.

The user wants to visualize the following story in a '{style}' visual style.

STORY:
{text}

Your tasks:
1. Identify the main subject/character of the story.
2. Detect the overall emotional mood of the story and return it as a single word from ONLY these choices:
   - "triumph"    for success, achievement, winning, happiness
   - "struggle"   for hardship, difficulty, pain, challenges
   - "adventure"  for travel, exploration, excitement, action
   - "dark"       for fear, danger, mystery, loss, grief
   - "warmth"     for love, family, friendship, nostalgia, hope
3. Split the narrative chronologically into individual, distinct moments.
   - CRITICAL: You MUST create at least 5 to 7 scenes for long, multi-sentence stories.
   - Do NOT just default to 3 scenes. Break the story down into many smaller visual panels.
4. For each scene, act as a friendly storyteller writing for a general audience and create a 'narrative_caption'.
   - ABSOLUTELY DO NOT copy the user's text verbatim.
   - Automatically FIX ANY misspelled words, bad grammar, and poor phrasing from the user's input.
   - Use SIMPLE, EVERYDAY words — write like you are telling a story to a friend. Avoid complex, academic, or literary vocabulary.
   - Make it warm, human, and easy to read. Short snappy sentences. 2-3 sentences max.
   - STRICT RULE: Do NOT invent or hallucinate facts, hometowns, or plot points that the user did not provide. Stay faithful to the given facts — only make them sound more interesting.
5. For each scene, write a highly detailed image generation prompt.

CRITICAL RULES for each image prompt:
- ALWAYS begin with the art style: "[{style} style],"
- ALWAYS include the character description for visual consistency across panels.
- Describe the environment, lighting, mood, and action vividly.
- End every prompt with: "highly detailed, 8k resolution, professional composition"
- Do NOT include any text, letters, or logos in the image description.

Respond ONLY with a valid JSON object — no markdown fences, no extra text:
{{
    "character_description": "Brief description of main subject for consistency.",
    "mood": "one of: triumph | struggle | adventure | dark | warmth",
    "scenes": [
        {{
            "narrative_caption": "A simple, warm, easy-to-read rewrite of this moment.",
            "image_prompt": "Full engineered prompt here."
        }}
    ]
}}
"""

    gemini_models = [
        llm_model,
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
    ]
    seen = set()
    gemini_models = [m for m in gemini_models if not (m in seen or seen.add(m))]

    last_err = None
    for m in gemini_models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)
        except Exception as e:
            last_err = e
            time.sleep(1)
            continue

    raise Exception(f"All Gemini models failed. Last error: {last_err}")


def generate_image_hf(prompt: str, seed: int, index: int) -> str:
    last_error = "Unknown error"

    for model_id in HF_MODELS:
        try:
            print(f"[IMG] Trying model: {model_id} for scene {index}", flush=True)
            hf_client = InferenceClient(model=model_id, token=hf_token)
            image = hf_client.text_to_image(
                prompt,
                width=768,
                height=512
            )
            image_path = f"static/images/scene_{index}_{seed}.png"
            image.save(image_path)
            print(f"[IMG] Success with {model_id} for scene {index}", flush=True)
            return f"/images/scene_{index}_{seed}.png"
        except Exception as e:
            last_error = str(e)
            print(f"[IMG] FAILED {model_id} for scene {index}: {last_error}", file=sys.stderr, flush=True)
            time.sleep(2)
            continue

    raise Exception(
        f"All image generation models failed for scene {index}. Last error: {last_error}"
    )


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.post("/api/generate")
async def generate_storyboard(request: StoryRequest):
    if not request.story_text.strip():
        raise HTTPException(status_code=400, detail="Story text cannot be empty.")
    if len(request.story_text) > 5000:
        raise HTTPException(status_code=400, detail="Story text is too long (max 5000 chars).")

    async def stream_panels():
        try:
            yield json.dumps({"type": "status", "message": f"Analyzing with {request.llm_model}..."}) + "\n"
            scene_data = generate_storyboard_prompts(request.story_text, request.style, request.llm_model)

            scenes = scene_data.get("scenes", [])
            mood   = scene_data.get("mood", "triumph")
            if not scenes:
                yield json.dumps({"type": "error", "message": "Gemini returned no scenes. Try again."}) + "\n"
                return

            yield json.dumps({"type": "mood", "mood": mood}) + "\n"

            shared_seed = random.randint(1, 2**31 - 1)
            total = len(scenes)

            yield json.dumps({
                "type": "status",
                "message": f"Identified {total} scenes. Starting image generation..."
            }) + "\n"

            for index, scene in enumerate(scenes):
                yield json.dumps({
                    "type": "status",
                    "message": f"Generating Scene {index + 1} of {total}..."
                }) + "\n"

                image_url = generate_image_hf(scene["image_prompt"], shared_seed, index)
                panel = {
                    "text": scene.get("narrative_caption", scene.get("original_text", "")),
                    "image_url": image_url,
                    "prompt": scene["image_prompt"],
                }

                yield json.dumps({"type": "panel", "panel": panel, "index": index}) + "\n"

            yield json.dumps({"type": "done", "total": total}) + "\n"

        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(stream_panels(), media_type="application/x-ndjson")