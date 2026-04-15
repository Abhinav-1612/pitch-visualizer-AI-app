# 🎬 The Pitch Visualizer

**Turn any story into a visual storyboard — powered by Gemini AI and Stable Diffusion.**

---

I built this for Challenge 2 of the hackathon. The idea is simple: you paste a story or a sales pitch, and the app automatically breaks it into scenes, writes detailed image prompts for each one, and generates a full visual storyboard — all in one click.

No design skills needed. No manual prompt writing. You just paste your text, pick a visual style, and let the AI do the heavy lifting.

---

## What it does

- Takes any block of text as input (a pitch, a story, a success case — anything)
- Uses **Google Gemini** to understand the narrative and split it into 5–7 logical scenes
- Gemini writes a proper, detailed image generation prompt for each scene (not just the raw sentence — it adds character descriptions, lighting, mood, art style, and more)
- Sends each prompt to **Hugging Face's Stable Diffusion models** to generate an image
- Shows the storyboard live, panel by panel, as images finish generating
- Automatically detects the emotional tone of your story and changes the UI color theme to match

---

## Features worth mentioning

- **10 Visual Styles** — Cinematic Concept Art, Photorealistic, Watercolor, Cyberpunk, Studio Ghibli Anime, Minimalist Vector, Dark Fantasy Oil Painting, Retro Futurism, Comic Book Sketch, Graphic Novel Ink
- **Gemini Model Switcher** — In case one Gemini server is busy, you can switch between Gemini 2.5 Flash, 2.0 Flash, and Gemini Flash Latest right from the UI
- **Auto Mood Theming** — The UI accent color automatically changes based on the detected story mood (triumph → amber, struggle → blue, adventure → green, dark → purple, warmth → rose)
- **Smart Fallback Chains** — If a Gemini model is down, it tries the next one. If a Hugging Face model fails, it tries the next image model. The app rarely crashes.
- **Grammar & Style Fix** — Gemini silently corrects typos and bad grammar in your input before processing. You don't have to proofread your prompts.
- **Hover to see prompts** — Hover over any panel image to see the exact image prompt that was generated for it

---

## Setup

### 1. Get the code

```bash
git clone https://github.com/Abhinav-1612/pitch-visualizer-AI-app.git
cd pitch-visualizer-AI-app
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API keys

Create a file called `.env` in the root of the project and add your keys:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
HF_TOKEN=your_huggingface_token_here
```

**Getting your keys:**

- **Gemini API Key** → Go to [Google AI Studio](https://aistudio.google.com/app/apikey), sign in with your Google account, and click "Create API Key". It's free.
- **Hugging Face Token** → Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), click "New Token", set the role to **Read**, and copy it. Also free.

> **Note:** Never commit your `.env` file to GitHub. Add it to your `.gitignore`.

### 5. Run the server

```bash
uvicorn app:app --reload
```

### 6. Open the app

Go to **http://localhost:8000** in your browser.

---

## How to use it

1. Paste your story or pitch into the text box
2. Pick a **Visual Style** from the dropdown (try Comic Book Sketch for a fun one)
3. If Gemini is being slow, switch the **AI Model** dropdown to a different version
4. Hit **Generate Storyboard**
5. Watch the panels appear one by one

---

## Project Structure

```
pitch-visualizer/
├── app.py              → FastAPI backend — handles Gemini calls, image generation, streaming
├── requirements.txt    → Python packages needed
├── .env                → Your API keys (don't commit this)
├── static/
│   ├── index.html      → The full frontend — UI, theme switching, streaming logic
│   └── style.css       → Dark glassmorphism design system
└── README.md
```

---

## How prompt engineering works

This was the most interesting part to build. The challenge says "simply using the raw sentence as the prompt is insufficient" — and I agree. Raw sentences make terrible image prompts.

Here's what actually happens:

**Step 1 — Gemini reads the whole story first.**
Rather than processing one sentence at a time, I send the entire text to Gemini with a structured brief. This way it understands the context, the character, and the arc before it writes a single prompt.

**Step 2 — Gemini extracts a character description.**
The first thing Gemini does is write a reusable character description (e.g. *"young Indian male student, early 20s, wearing glasses, determined expression"*). This gets injected into every single image prompt to keep the character visually consistent across all panels.

**Step 3 — Gemini engineers each image prompt from scratch.**
For each scene, Gemini doesn't just clean up the sentence — it writes a complete image generation prompt in this structure:

```
[Art Style], [Character description], [Action in this scene],
[Environment description], [Lighting and mood], 
highly detailed, 8k resolution, professional composition
```

This format produces dramatically better images than using the raw text. Every prompt is tailored to the scene, the selected style, and the overall story.

**Step 4 — Gemini detects emotional mood.**
Alongside the prompts, Gemini also classifies the story's overall emotion (triumph, struggle, adventure, dark, or warmth). The frontend uses this to automatically change the UI accent color.

**Step 5 — Images generate with a shared seed.**
All image generation calls use the same random seed, which nudges the model toward a consistent visual aesthetic across panels — similar colors, similar lighting style.

---

## Reliability

The free APIs can be flaky. Here's how the app handles that:

- **Gemini fallback** — Tries `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-flash-latest` in order
- **Image fallback** — Tries `FLUX.1-schnell` → `stable-diffusion-xl` → `openjourney` → `dreamshaper-8`
- **503 errors** — Auto-retries with exponential backoff (up to 4 attempts per model)
- **Rate limits** — 15-second cooldown before retrying

The streaming architecture also helps with perceived performance — panels appear as soon as they're ready rather than making you wait for everything to finish.

---

## Dependencies

| Package | What it's for |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server to run FastAPI |
| `google-genai` | Official Google Gemini SDK |
| `huggingface_hub` | Official HF SDK (InferenceClient) |
| `Pillow` | Image processing |
| `python-dotenv` | Loads `.env` file |
| `pydantic` | Request validation |

---

## API Rate Limits (important for judges)

Both APIs used here are free tier:

- **Gemini** — ~60 requests/minute on the free tier. If you see a 429 or 503, just wait 30 seconds and try again, or switch the AI Model in the UI.
- **Hugging Face** — ~50-100 image generations per hour on a free token. If images stop loading, the HF quota has probably been hit — wait an hour or switch to a different HF model in `app.py`.

---

Built by **Abhinav Singh**, IIIT Nagpur.