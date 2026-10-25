# Claude Banana

**You tell it what picture you want. It writes the perfect instructions to make that picture.**

That's it. That's what Claude Banana does.

---

## The Problem

You want AI to make you an image. You type "a cool sunset." You get... something okay. But not what you imagined.

**Why?** Because AI image generators need very specific instructions. The more detail you give them — lighting, camera angle, colors, mood, textures — the better the result. But writing those detailed instructions is hard and takes practice.

## The Solution

Claude Banana is your **creative assistant**. You describe what you want in plain words, and it:

1. **Asks you a few quick questions** to understand your vision
2. **Builds a detailed, optimized prompt** using a proven formula
3. **Gives you a ready-to-copy prompt** that gets amazing results from image generators

Think of it like having a professional photographer in your pocket who translates "I want a cool sunset" into a paragraph of perfect instructions that the AI actually understands.

---

## How to Use It

### Step 1: Get Claude Code

Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's command-line tool).

### Step 2: Download This Project

```bash
git clone https://github.com/Hainrixz/claude-banana.git
cd claude-banana
```

### Step 3: Start Claude and Ask

```bash
claude
```

Then just describe what you want in plain words:

```
"Help me create a prompt for a cozy coffee shop with warm lighting and a cat sleeping on some books"
```

Claude automatically picks up the prompt-architect agent and knowledge base from this project. It will ask you a couple of questions (like "What's the mood?" or "Where will you use this image?"), and then give you a perfect prompt ready to paste into any image generator.

---

## What Makes It Special

### The 7-Piece Formula

Every prompt Claude Banana creates has 7 carefully balanced ingredients:

| Ingredient | What It Does | Example |
|-----------|-------------|---------|
| **Subject** | Who or what is in the picture | "A gray tabby cat curled up on a stack of books" |
| **Style** | How it looks visually | "Warm watercolor illustration with soft edges" |
| **Environment** | Where it takes place | "Inside a small bookshop cafe with wooden shelves" |
| **Lighting** | How light falls on the scene | "Honey-gold afternoon light from a bay window" |
| **Action** | What's happening | "The cat is sleeping with one paw draped over a book spine" |
| **Camera** | How the picture is framed | "Eye-level close-up, slightly overhead angle" |
| **Texture** | What things feel like | "Worn leather book covers, soft fur, steam rising from a mug" |

### 9 Expertise Modes

The agent adjusts its formula depending on what kind of image you want:

- **Cinema** — Movie-like dramatic scenes
- **Product** — Clean, professional product photos
- **Portrait** — Beautiful photos of people
- **Fashion** — Magazine-style editorial looks
- **UI/Web** — App icons, web designs, interfaces
- **Logo** — Brand marks and symbols
- **Landscape** — Nature and environments
- **Abstract** — Artistic patterns and textures
- **Infographic** — Charts, data visuals, diagrams

### 70+ Creative Techniques

Want something special? The agent knows how to do things like:

- Turn photos into **anime/Ghibli style**
- Create **miniature worlds inside crystal balls**
- Make characters **break out of picture frames**
- Mix **pencil sketches with real photos**
- Build **tiny tilt-shift cities**
- Design **voxel/pixel art** icons
- And 60+ more creative effects

### Works With Your Existing Prompts

Already have prompts from Midjourney, DALL-E, or Stable Diffusion? Paste them in and Claude Banana converts them to work better with Nano Banana Pro (Google's image generator).

### Brand Presets

Making images for a brand? Load a preset with your brand colors, style, and mood so every image stays consistent.

---

## What's Inside

```
claude-banana/
  knowledge/           -- The brain: everything the agent knows about making great prompts
  templates/examples/  -- 25 ready-to-use prompt templates you can customize
  presets/             -- Brand style presets (colors, fonts, mood)
  scripts/             -- Python tools for generating images directly
  .claude/agents/      -- The agent itself
```

### Optional: Generate Images Directly

If you have a Google AI API key (free from [aistudio.google.com](https://aistudio.google.com/apikey)), you can generate images without leaving your terminal:

```bash
# Check your setup
python3 scripts/validate_setup.py

# Generate an image from a prompt
python3 scripts/generate.py --prompt "your optimized prompt here"

# Generate from a template with custom values
python3 scripts/generate.py --template templates/examples/cinematic-landscape.md \
  --vars '{"location": "mountain lake", "time_of_day": "sunset"}'

# Edit an existing image
python3 scripts/edit.py --image photo.png --instruction "make it look like autumn"

# Generate a batch of variations
python3 scripts/batch.py --template templates/examples/product-showcase.md \
  --variations my_products.json
```

---

## Want to Contribute?

We'd love your help! You can:

- **Share a prompt template** — Open an issue with your favorite prompt
- **Add a technique** — Document a new creative technique
- **Improve the knowledge** — Make the reference guides even better
- **Fix bugs** — Submit a pull request

See the [issue templates](.github/ISSUE_TEMPLATE/) for easy submission forms.

---

## License

MIT — free to use, modify, and share. See [LICENSE](LICENSE).

---

**[Leer en Espanol / Read in Spanish](README_ES.md)**

<!-- marca-agua:inicio -->

---

<sub>Hecho por **Enrique Rocha (@soyenriquerocha)** · [tododeia.com](https://www.tododeia.com)⁠​‌‌​​‌​‌​‌‌‌​​‌​​​‌​‌‌​‌​‌‌​​‌​‌​​‌‌‌​​​​‌‌​​​‌​​​‌‌​​‌​​‌‌​​​‌​​‌‌​​​‌‌​​‌‌​‌​​​​‌‌‌​​​⁠</sub>
<!-- marca-agua:fin -->
