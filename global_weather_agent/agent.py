"""
Global Weather Report Data Agent
Built with Google Agent Development Kit (ADK) + Open-Meteo API (no API key needed)
"""

import sys
from pathlib import Path

# Automatically find and load the local virtual environment packages
venv_path = Path(__file__).resolve().parents[1] / ".venv" / "lib" / "python3.14" / "site-packages"
if venv_path.exists() and str(venv_path) not in sys.path:
    sys.path.insert(0, str(venv_path))

import datetime
import urllib.request
import urllib.parse
import json
import os
import time
from zoneinfo import ZoneInfo
import ssl
import certifi

# Fallback constraint: ADK often needs GEMINI_API_KEY exactly over GOOGLE_API_KEY
if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

from google.adk.agents import Agent

# Create a secure SSL context using certifi to handle macOS certificate issues
ssl_context = ssl.create_default_context(cafile=certifi.where())


# ─────────────────────────────────────────────
# WMO Weather Code → Description (full set)
# ─────────────────────────────────────────────
WMO_CODES = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤️",
    2: "Partly cloudy ⛅",
    3: "Overcast ☁️",
    45: "Foggy 🌫️",
    48: "Depositing rime fog 🌫️",
    51: "Light drizzle 🌦️",
    53: "Moderate drizzle 🌦️",
    55: "Dense drizzle 🌧️",
    56: "Light freezing drizzle 🌨️",
    57: "Heavy freezing drizzle 🌨️",
    61: "Slight rain 🌧️",
    63: "Moderate rain 🌧️",
    65: "Heavy rain 🌧️",
    66: "Light freezing rain 🌨️",
    67: "Heavy freezing rain 🌨️",
    71: "Slight snowfall 🌨️",
    73: "Moderate snowfall ❄️",
    75: "Heavy snowfall ❄️",
    77: "Snow grains 🌨️",
    80: "Slight rain showers 🌦️",
    81: "Moderate rain showers 🌧️",
    82: "Violent rain showers ⛈️",
    85: "Slight snow showers 🌨️",
    86: "Heavy snow showers ❄️",
    95: "Thunderstorm ⛈️",
    96: "Thunderstorm with slight hail ⛈️",
    99: "Thunderstorm with heavy hail ⛈️",
}


# ─────────────────────────────────────────────
# UV Index → Risk Level
# ─────────────────────────────────────────────
def _uv_advisory(uv: float) -> str:
    """Return a human-readable UV risk level and safety tip."""
    if uv is None:
        return "N/A"
    if uv < 3:
        return f"{uv} — Low ✅ (No protection needed)"
    elif uv < 6:
        return f"{uv} — Moderate 🟡 (Wear sunscreen SPF 30+)"
    elif uv < 8:
        return f"{uv} — High 🟠 (Seek shade 10am–4pm, SPF 50+)"
    elif uv < 11:
        return f"{uv} — Very High 🔴 (Limit sun exposure, hat + sunglasses)"
    else:
        return f"{uv} — Extreme ☠️ (Avoid outdoor activity during peak hours)"


# ─────────────────────────────────────────────
# Wind direction degrees → Compass bearing
# ─────────────────────────────────────────────
def _wind_compass(degrees: float | None) -> str:
    """Convert wind direction degrees to compass bearing string."""
    if degrees is None:
        return "N/A"
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return f"{directions[idx]} ({int(degrees)}°)"


# ─────────────────────────────────────────────
# Helper: HTTP GET with retry
# ─────────────────────────────────────────────
def _fetch_json(url: str, retries: int = 2, timeout: int = 10) -> dict | None:
    """Fetch JSON from a URL with automatic retry on failure."""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout, context=ssl_context) as resp:
                return json.loads(resp.read())
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
    return None


# ─────────────────────────────────────────────
# Helper: Geocode city name → lat/lon
# Uses Open-Meteo's free geocoding API
# ─────────────────────────────────────────────
def _geocode(city: str) -> dict | None:
    """Return {'lat', 'lon', 'name', 'country', 'timezone'} or None."""
    params = urllib.parse.urlencode({
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    })
    url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"
    data = _fetch_json(url)
    if not data:
        return None
    results = data.get("results")
    if not results:
        return None
    r = results[0]
    return {
        "lat": r["latitude"],
        "lon": r["longitude"],
        "name": r.get("name", city),
        "country": r.get("country", ""),
        "timezone": r.get("timezone", "UTC"),
    }


# ─────────────────────────────────────────────
# Tool 1: Current weather
# ─────────────────────────────────────────────
def get_current_weather(city: str) -> dict:
    """
    Retrieves the current weather report for any city in the world.

    Uses real-time data from the Open-Meteo API (no API key required).
    Returns temperature, apparent temperature, humidity, wind speed,
    wind compass direction, precipitation, weather condition description,
    pressure, cloud cover, and local time.

    Args:
        city (str): Name of the city (e.g. "Tokyo", "London", "Nairobi").

    Returns:
        dict: status ("success" | "error") and either a structured
              weather report or an error_message string.
    """
    geo = _geocode(city)
    if not geo:
        return {
            "status": "error",
            "error_message": f"Could not find location data for '{city}'. Try a more specific name or add the country (e.g. 'Springfield, USA')."
        }

    params = urllib.parse.urlencode({
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "current": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
            "cloud_cover",
            "is_day",
        ]),
        "timezone": geo["timezone"],
        "wind_speed_unit": "kmh",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    data = _fetch_json(url)
    if not data:
        return {"status": "error", "error_message": f"Failed to fetch weather data for '{city}'. Please try again."}

    try:
        cur = data["current"]
        wmo = cur.get("weather_code", 0)
        condition = WMO_CODES.get(wmo, f"Weather code {wmo}")
        is_day = cur.get("is_day", 1)
        wind_deg = cur.get("wind_direction_10m")

        report = {
            "city": geo["name"],
            "country": geo["country"],
            "local_time": cur.get("time", ""),
            "timezone": geo["timezone"],
            "condition": condition,
            "is_day": bool(is_day),
            "temperature_c": cur.get("temperature_2m"),
            "temperature_f": round(cur.get("temperature_2m", 0) * 9 / 5 + 32, 1),
            "feels_like_c": cur.get("apparent_temperature"),
            "feels_like_f": round(cur.get("apparent_temperature", 0) * 9 / 5 + 32, 1),
            "humidity_percent": cur.get("relative_humidity_2m"),
            "precipitation_mm": cur.get("precipitation"),
            "wind_speed_kmh": cur.get("wind_speed_10m"),
            "wind_direction": _wind_compass(wind_deg),
            "cloud_cover_percent": cur.get("cloud_cover"),
            "pressure_hpa": cur.get("surface_pressure"),
        }
        return {"status": "success", "report": report}

    except (KeyError, TypeError, ValueError) as e:
        return {"status": "error", "error_message": f"Failed to parse weather data: {e}"}


# ─────────────────────────────────────────────
# Tool 2: 7-day forecast
# ─────────────────────────────────────────────
def get_weather_forecast(city: str, days: int = 7) -> dict:
    """
    Returns a daily weather forecast for a city for up to 7 days.

    Provides daily max/min temperature, precipitation sum, dominant
    weather condition, max wind speed, UV index with health advisory,
    and sunrise/sunset times for each day.

    Args:
        city (str): Name of the city (e.g. "Paris", "Mumbai", "Toronto").
        days (int): Number of forecast days to return (1–7). Defaults to 7.

    Returns:
        dict: status ("success" | "error") and either a list of daily
              forecast records or an error_message string.
    """
    days = max(1, min(days, 7))
    geo = _geocode(city)
    if not geo:
        return {
            "status": "error",
            "error_message": f"Could not find location data for '{city}'."
        }

    params = urllib.parse.urlencode({
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
            "uv_index_max",
            "sunrise",
            "sunset",
            "precipitation_probability_max",
        ]),
        "timezone": geo["timezone"],
        "forecast_days": days,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    data = _fetch_json(url)
    if not data:
        return {"status": "error", "error_message": f"Forecast fetch failed for '{city}'. Please try again."}

    try:
        daily = data["daily"]
        forecast = []
        for i in range(len(daily["time"])):
            wmo = daily["weather_code"][i]
            uv = daily.get("uv_index_max", [None] * days)[i]
            rain_prob = daily.get("precipitation_probability_max", [None] * days)[i]
            forecast.append({
                "date": daily["time"][i],
                "condition": WMO_CODES.get(wmo, f"Code {wmo}"),
                "temp_max_c": daily["temperature_2m_max"][i],
                "temp_min_c": daily["temperature_2m_min"][i],
                "temp_max_f": round(daily["temperature_2m_max"][i] * 9 / 5 + 32, 1),
                "temp_min_f": round(daily["temperature_2m_min"][i] * 9 / 5 + 32, 1),
                "precipitation_mm": daily["precipitation_sum"][i],
                "rain_probability_percent": rain_prob,
                "wind_max_kmh": daily["wind_speed_10m_max"][i],
                "uv_index": _uv_advisory(uv),
                "sunrise": daily["sunrise"][i],
                "sunset": daily["sunset"][i],
            })

        return {
            "status": "success",
            "city": geo["name"],
            "country": geo["country"],
            "timezone": geo["timezone"],
            "forecast": forecast,
        }

    except (KeyError, TypeError, ValueError, IndexError) as e:
        return {"status": "error", "error_message": f"Forecast parse error: {e}"}


# ─────────────────────────────────────────────
# Tool 3: Compare weather in multiple cities
# ─────────────────────────────────────────────
def compare_cities_weather(cities: list[str]) -> dict:
    """
    Compares current weather across multiple cities simultaneously.

    Fetches real-time weather data for each provided city and returns
    a side-by-side comparison including temperature, feels-like, humidity,
    wind speed and direction, precipitation, and weather conditions.

    Args:
        cities (list[str]): List of city names to compare (2–6 cities recommended).
                            Example: ["New York", "London", "Tokyo", "Dubai"]

    Returns:
        dict: status ("success" | "error") and a list of weather summaries
              for each city, or an error_message.
    """
    if not cities:
        return {"status": "error", "error_message": "Please provide at least one city."}

    results = []
    errors = []

    for city in cities:
        result = get_current_weather(city)
        if result["status"] == "success":
            r = result["report"]
            results.append({
                "city": r["city"],
                "country": r["country"],
                "condition": r["condition"],
                "temperature_c": r["temperature_c"],
                "temperature_f": r["temperature_f"],
                "feels_like_c": r["feels_like_c"],
                "humidity_percent": r["humidity_percent"],
                "wind_speed_kmh": r["wind_speed_kmh"],
                "wind_direction": r["wind_direction"],
                "precipitation_mm": r["precipitation_mm"],
                "local_time": r["local_time"],
            })
        else:
            errors.append(f"{city}: {result.get('error_message', 'Unknown error')}")

    if not results:
        return {
            "status": "error",
            "error_message": "Could not retrieve weather for any city. Errors: " + "; ".join(errors)
        }

    return {
        "status": "success",
        "comparison": results,
        "errors": errors if errors else None,
    }


# ─────────────────────────────────────────────
# Tool 4: Local time for a city
# ─────────────────────────────────────────────
def get_local_time(city: str) -> dict:
    """
    Returns the current local date and time for any city in the world.

    Uses timezone data from the geocoding API to compute the accurate
    local time without needing an external time API.

    Args:
        city (str): Name of the city (e.g. "Sydney", "São Paulo", "Cairo").

    Returns:
        dict: status ("success" | "error") and local time details including
              date, time, timezone name, and UTC offset.
    """
    geo = _geocode(city)
    if not geo:
        return {
            "status": "error",
            "error_message": f"Could not determine timezone for '{city}'."
        }

    try:
        tz = ZoneInfo(geo["timezone"])
        now = datetime.datetime.now(tz)
        return {
            "status": "success",
            "city": geo["name"],
            "country": geo["country"],
            "local_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "local_date": now.strftime("%A, %B %d, %Y"),
            "local_time": now.strftime("%I:%M %p"),
            "timezone": geo["timezone"],
            "utc_offset": now.strftime("%z"),
        }
    except (KeyError, ValueError) as e:
        return {"status": "error", "error_message": f"Time computation failed: {e}"}


# ─────────────────────────────────────────────
# Tool 5: Air quality for a city
# ─────────────────────────────────────────────
def get_air_quality(city: str) -> dict:
    """
    Returns current air quality data for any city in the world.

    Fetches PM2.5, PM10, carbon monoxide, nitrogen dioxide, ozone,
    and European AQI (Air Quality Index) from Open-Meteo's free
    air quality API. Includes a human-readable AQI category.

    Args:
        city (str): Name of the city (e.g. "Beijing", "Delhi", "Los Angeles").

    Returns:
        dict: status ("success" | "error") and air quality metrics or error_message.
    """
    geo = _geocode(city)
    if not geo:
        return {
            "status": "error",
            "error_message": f"Could not find location data for '{city}'."
        }

    params = urllib.parse.urlencode({
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "current": ",".join([
            "pm10",
            "pm2_5",
            "carbon_monoxide",
            "nitrogen_dioxide",
            "ozone",
            "european_aqi",
        ]),
        "timezone": geo["timezone"],
    })
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{params}"

    data = _fetch_json(url)
    if not data:
        return {"status": "error", "error_message": f"Air quality fetch failed for '{city}'. Please try again."}

    try:
        cur = data.get("current", {})
        aqi = cur.get("european_aqi")

        # European AQI categories
        if aqi is None:
            aqi_label = "N/A"
        elif aqi <= 20:
            aqi_label = f"{aqi} — Good 🟢"
        elif aqi <= 40:
            aqi_label = f"{aqi} — Fair 🟡"
        elif aqi <= 60:
            aqi_label = f"{aqi} — Moderate 🟠"
        elif aqi <= 80:
            aqi_label = f"{aqi} — Poor 🔴"
        elif aqi <= 100:
            aqi_label = f"{aqi} — Very Poor 🟣"
        else:
            aqi_label = f"{aqi} — Extremely Poor ☠️"

        return {
            "status": "success",
            "city": geo["name"],
            "country": geo["country"],
            "local_time": cur.get("time", ""),
            "european_aqi": aqi_label,
            "pm2_5_μg_m3": cur.get("pm2_5"),
            "pm10_μg_m3": cur.get("pm10"),
            "carbon_monoxide_μg_m3": cur.get("carbon_monoxide"),
            "nitrogen_dioxide_μg_m3": cur.get("nitrogen_dioxide"),
            "ozone_μg_m3": cur.get("ozone"),
        }

    except (KeyError, TypeError, ValueError) as e:
        return {"status": "error", "error_message": f"Air quality parse error: {e}"}


# ─────────────────────────────────────────────
# Root Agent definition
# ─────────────────────────────────────────────
root_agent = Agent(
    name="global_weather_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "A global weather data agent that provides real-time weather reports, "
        "7-day forecasts, multi-city comparisons, local time, and air quality "
        "for any city worldwide."
    ),
    instruction="""
You are a knowledgeable, friendly, and proactive **Global Weather Report Assistant**.
You have access to real-time weather and air quality data for any city in the world.

## Your Capabilities

- 🌡️  **Current Weather** — Temperature (°C & °F), feels-like, humidity, wind speed & direction, precipitation, cloud cover, pressure
- 📅  **7-Day Forecast** — Daily highs/lows, rain probability, UV index with health advisory, sunrise/sunset
- 🌍  **City Comparison** — Side-by-side real-time weather for multiple cities
- 🕐  **Local Time** — Accurate local time and timezone for any city
- 🌬️  **Air Quality** — PM2.5, PM10, ozone, NO₂, CO, and European AQI with health category

## Formatting Rules

- Always present temperatures in **both °C and °F**.
- Always include wind **direction** (e.g. "SW at 18 km/h") not just speed.
- Present **rain probability** from forecasts when available.
- Show **UV advisory** prominently for sunny/forecasted days.
- Use bullet points or short paragraphs — never dump raw JSON at the user.
- Always mention **local time** when giving current conditions.
- For multi-day forecasts, **highlight standout days**: heavy rain, heat waves, snow, extreme UV.

## Behaviour Guidelines

- If a city name is ambiguous (e.g. "Springfield"), ask the user to clarify the country or state.
- If the user asks about weather in a region (e.g. "Southeast Asia"), proactively suggest comparing major cities there.
- If air quality is poor or hazardous, mention it as a health concern even if not asked.
- Be conversational and helpful — if conditions are notable, add a friendly tip (e.g. "Great day to be outdoors!" or "You might want an umbrella today ☔").
- If a tool returns an error, explain it clearly and suggest alternatives (e.g. a nearby city).
""",
    tools=[
        get_current_weather,
        get_weather_forecast,
        compare_cities_weather,
        get_local_time,
        get_air_quality,
    ],
)
