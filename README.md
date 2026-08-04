# 🌍 Global Weather Report Agent
### Built with Python + Google Agent Development Kit (ADK)

Real-time global weather data powered by **Open-Meteo** (free, no API key needed)
and **Google Gemini 3.1 Flash Lite** via the Google ADK.

---

## 📁 Project Structure

```
wether_report_agent/
├── global_weather_agent/
│   ├── __init__.py
│   └── agent.py          ← All agent + tool logic
├── .env                  ← Your Gemini API key (GOOGLE_API_KEY)
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Prerequisites
- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) (free)

### 2. Create virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows CMD
.venv\Scripts\activate.bat

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Edit the `.env` file and set your key:

```env
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

> **Note**: The agent automatically maps `GOOGLE_API_KEY` → `GEMINI_API_KEY` so either variable name works.

---

## 🚀 How to Use

> **Important**: Always run commands from the **project root** (`wether_report_agent/`), not from inside the `global_weather_agent/` subfolder.

### Step 1 — Activate your virtual environment

Every time you open a new terminal, activate the environment first:

```bash
cd /path/to/wether_report_agent
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate.bat     # Windows CMD
# .venv\Scripts\Activate.ps1     # Windows PowerShell
```

---

### ▶️ Option A: Terminal Chat Mode

The simplest way — have a conversation directly in the terminal:

```bash
adk run global_weather_agent
```

Type your question and press **Enter**. Type `exit` or press `Ctrl+C` to quit.

**Example session:**
```
You: What's the weather in Tokyo right now?
Agent: 🌤️ It's currently 18°C (64°F) in Tokyo, Japan...

You: Compare London, Paris and Berlin
Agent: Here's a side-by-side comparison...

You: exit
```

---

### 🌐 Option B: Browser Dev UI (Recommended)

Launches a full chat interface in your browser:

```bash
adk web
```

Then open → **http://localhost:8000**

1. Select **`global_weather_agent`** from the dropdown at the top
2. Type your question in the chat box and press **Send**
3. Press `Ctrl+C` in the terminal to stop the server

> 💡 **Tip**: If you get a port conflict error (`address already in use`), run this to free up port 8000:
> ```bash
> lsof -ti :8000 | xargs kill -9 2>/dev/null || true
> ```

---

### 🔌 Option C: Local REST API Server

Runs a FastAPI server for programmatic access:

```bash
adk api_server
```

Test with **cURL**:
```bash
# Current weather
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Weather in London?"}'

# 5-day forecast
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Give me a 5-day forecast for Mumbai"}'
```

Interactive API docs available at → **http://localhost:8000/docs**

---

## 💬 Example Queries by Feature

| Feature | What to ask |
|---------|------------|
| **Current weather** | `What's the weather in New York?` |
| **7-day forecast** | `Give me a 5-day forecast for Cairo.` |
| **Rain check** | `Will it rain in Mumbai this week?` |
| **City comparison** | `Compare London, Paris, and Berlin.` |
| **Local time** | `What time is it in São Paulo?` |
| **Air quality** | `What's the air quality in Delhi?` |
| **Which is hotter** | `Which is hotter today — Dubai or Singapore?` |
| **Region overview** | `What's the weather like in Southeast Asia?` |

---

## 🛠️ Agent Tools

| Tool | Description |
|------|-------------|
| `get_current_weather(city)` | Real-time weather — temperature, humidity, wind, pressure, condition |
| `get_weather_forecast(city, days)` | 1–7 day forecast with rain probability & UV health advisory |
| `compare_cities_weather(cities)` | Side-by-side comparison of multiple cities |
| `get_local_time(city)` | Current local time + timezone + UTC offset |
| `get_air_quality(city)` | PM2.5, PM10, ozone, NO₂, CO + European AQI category |

**Data source**: [Open-Meteo](https://open-meteo.com/) — free, no API key required.

---

## ✨ What's New (Latest)

- 🤖 **Model upgraded** to `gemini-3.1-flash-lite` (replaces `gemini-2.5-flash` for better cost-efficiency and higher free-tier quotas)
- 🌬️ **Air quality tool** — European AQI with PM2.5, PM10, ozone, NO₂, CO
- ☀️ **UV health advisory** embedded in forecast output
- 🧭 **Wind compass** — direction shown as NE/SW etc., not just degrees
- 🔁 **Retry logic** — HTTP calls auto-retry on transient failures
- 🗂️ **Full WMO weather code map** — covers all 100+ codes with emoji
- 🔐 **Dual API key support** — accepts both `GOOGLE_API_KEY` and `GEMINI_API_KEY`

---

## ⚠️ Troubleshooting

**`404 NOT_FOUND` — model not found**
> The model name is invalid or no longer available via the v1beta API.
> Make sure `agent.py` uses `model="gemini-3.1-flash-lite"`. Do **not** use invalid or discontinued model names like `gemini-2.0-flash`.

**`429 RESOURCE_EXHAUSTED` — quota exceeded**
> You've hit the Gemini free-tier daily or per-minute limit.
> - We use `gemini-3.1-flash-lite` by default as it has generous free-tier quotas.
> - If you hit limits, wait a few minutes or until the next day (daily quota resets at midnight Pacific)
> - Enable billing on [Google AI Studio](https://aistudio.google.com) for increased quotas
> - Monitor your usage at [ai.dev/rate-limit](https://ai.dev/rate-limit)

**`[Errno 48] Address already in use` — port 8000 conflict**
> Another process (or a suspended `adk web`) is holding port 8000.
```bash
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
adk web
```

**`ModuleNotFoundError`**
> Make sure your virtual environment is active and dependencies are installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**`Could not find location data for '...'`**
> Try a more specific city name, e.g. `"Springfield, Illinois"` instead of `"Springfield"`.

**`SSL certificate error` on macOS**
> Run the macOS certificate installer:
```bash
/Applications/Python\ 3.x/Install\ Certificates.command
```

---

## ☁️ Deploy to Google Cloud Run

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy from source (auto-builds Docker image)
adk deploy cloud_run \
  --project YOUR_PROJECT_ID \
  --region us-central1 \
  --service-name global-weather-agent \
  global_weather_agent
```

---

## 🔧 Customization Ideas

- **Historical weather** — add date-range comparisons via Open-Meteo's archive API
- **Weather alerts** — trigger notifications when UV or AQI crosses a threshold
- **Multi-agent setup** — add a `GreetingAgent` sub-agent for small talk routing
- **Persistent sessions** — swap `InMemorySessionService` for Firestore-backed storage
- **Voice interface** — integrate with ADK's audio streaming for spoken weather queries

---

## 📄 License

MIT — free to use, modify, and distribute.
# wether_report_agent
