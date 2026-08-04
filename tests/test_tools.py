import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add workspace path to sys.path so we can import from global_weather_agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from global_weather_agent.agent import (
    get_current_weather,
    get_weather_forecast,
    compare_cities_weather,
    get_local_time,
    get_air_quality,
    _uv_advisory,
    _wind_compass,
)

class TestWeatherAgentToolsOffline(unittest.TestCase):
    """Offline unit tests using mocks for external Open-Meteo API requests."""

    @patch("global_weather_agent.agent._geocode")
    @patch("global_weather_agent.agent._fetch_json")
    def test_get_current_weather_success(self, mock_fetch, mock_geocode):
        # Arrange
        mock_geocode.return_value = {
            "lat": 51.5074,
            "lon": -0.1278,
            "name": "London",
            "country": "United Kingdom",
            "timezone": "Europe/London",
        }
        mock_fetch.return_value = {
            "current": {
                "time": "2026-05-20T12:00",
                "weather_code": 3,
                "is_day": 1,
                "temperature_2m": 15.5,
                "apparent_temperature": 14.2,
                "relative_humidity_2m": 65,
                "precipitation": 0.0,
                "wind_speed_10m": 12.0,
                "wind_direction_10m": 180.0,
                "cloud_cover": 75,
                "surface_pressure": 1012.0,
            }
        }

        # Act
        response = get_current_weather("London")

        # Assert
        self.assertEqual(response["status"], "success")
        report = response["report"]
        self.assertEqual(report["city"], "London")
        self.assertEqual(report["country"], "United Kingdom")
        self.assertEqual(report["condition"], "Overcast ☁️")
        self.assertEqual(report["temperature_c"], 15.5)
        self.assertEqual(report["temperature_f"], 59.9)  # 15.5 * 9/5 + 32
        self.assertEqual(report["humidity_percent"], 65)
        self.assertEqual(report["wind_direction"], "S (180°)")

    @patch("global_weather_agent.agent._geocode")
    def test_get_current_weather_geocode_failure(self, mock_geocode):
        # Arrange
        mock_geocode.return_value = None

        # Act
        response = get_current_weather("UnknownCityXYZ")

        # Assert
        self.assertEqual(response["status"], "error")
        self.assertIn("Could not find location data", response["error_message"])

    @patch("global_weather_agent.agent._geocode")
    @patch("global_weather_agent.agent._fetch_json")
    def test_get_weather_forecast_success(self, mock_fetch, mock_geocode):
        # Arrange
        mock_geocode.return_value = {
            "lat": 48.8566,
            "lon": 2.3522,
            "name": "Paris",
            "country": "France",
            "timezone": "Europe/Paris",
        }
        mock_fetch.return_value = {
            "daily": {
                "time": ["2026-05-20", "2026-05-21"],
                "weather_code": [0, 61],
                "temperature_2m_max": [20.0, 18.0],
                "temperature_2m_min": [12.0, 10.0],
                "precipitation_sum": [0.0, 3.5],
                "wind_speed_10m_max": [15.0, 22.0],
                "uv_index_max": [5.5, 2.0],
                "sunrise": ["2026-05-20T06:00", "2026-05-21T06:01"],
                "sunset": ["2026-05-20T21:00", "2026-05-21T21:02"],
                "precipitation_probability_max": [10, 85],
            }
        }

        # Act
        response = get_weather_forecast("Paris", days=2)

        # Assert
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["city"], "Paris")
        self.assertEqual(len(response["forecast"]), 2)
        
        day1 = response["forecast"][0]
        self.assertEqual(day1["date"], "2026-05-20")
        self.assertEqual(day1["condition"], "Clear sky ☀️")
        self.assertEqual(day1["temp_max_c"], 20.0)
        self.assertIn("Moderate", day1["uv_index"])  # 5.5 is moderate

        day2 = response["forecast"][1]
        self.assertEqual(day2["date"], "2026-05-21")
        self.assertEqual(day2["condition"], "Slight rain 🌧️")
        self.assertEqual(day2["rain_probability_percent"], 85)

    @patch("global_weather_agent.agent.get_current_weather")
    def test_compare_cities_weather(self, mock_get_current):
        # Arrange
        mock_get_current.side_effect = [
            {
                "status": "success",
                "report": {
                    "city": "Paris",
                    "country": "France",
                    "condition": "Clear sky ☀️",
                    "temperature_c": 20.0,
                    "temperature_f": 68.0,
                    "feels_like_c": 19.5,
                    "humidity_percent": 50,
                    "wind_speed_kmh": 10.0,
                    "wind_direction": "N (0°)",
                    "precipitation_mm": 0.0,
                    "local_time": "2026-05-20T12:00",
                }
            },
            {
                "status": "success",
                "report": {
                    "city": "London",
                    "country": "United Kingdom",
                    "condition": "Overcast ☁️",
                    "temperature_c": 15.0,
                    "temperature_f": 59.0,
                    "feels_like_c": 14.0,
                    "humidity_percent": 70,
                    "wind_speed_kmh": 15.0,
                    "wind_direction": "W (270°)",
                    "precipitation_mm": 0.5,
                    "local_time": "2026-05-20T11:00",
                }
            }
        ]

        # Act
        response = compare_cities_weather(["Paris", "London"])

        # Assert
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["comparison"]), 2)
        self.assertEqual(response["comparison"][0]["city"], "Paris")
        self.assertEqual(response["comparison"][1]["city"], "London")

    @patch("global_weather_agent.agent._geocode")
    def test_get_local_time_success(self, mock_geocode):
        # Arrange
        mock_geocode.return_value = {
            "lat": 35.6762,
            "lon": 139.6503,
            "name": "Tokyo",
            "country": "Japan",
            "timezone": "Asia/Tokyo",
        }

        # Act
        response = get_local_time("Tokyo")

        # Assert
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["city"], "Tokyo")
        self.assertEqual(response["timezone"], "Asia/Tokyo")
        self.assertIsNotNone(response["local_datetime"])

    @patch("global_weather_agent.agent._geocode")
    @patch("global_weather_agent.agent._fetch_json")
    def test_get_air_quality_success(self, mock_fetch, mock_geocode):
        # Arrange
        mock_geocode.return_value = {
            "lat": 28.6139,
            "lon": 77.2090,
            "name": "Delhi",
            "country": "India",
            "timezone": "Asia/Kolkata",
        }
        mock_fetch.return_value = {
            "current": {
                "time": "2026-05-20T12:00",
                "european_aqi": 85,
                "pm2_5": 75.4,
                "pm10": 120.2,
                "carbon_monoxide": 400.0,
                "nitrogen_dioxide": 25.5,
                "ozone": 60.0,
            }
        }

        # Act
        response = get_air_quality("Delhi")

        # Assert
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["city"], "Delhi")
        self.assertIn("Very Poor", response["european_aqi"])  # 85 is between 80 and 100
        self.assertEqual(response["pm2_5_μg_m3"], 75.4)

    def test_uv_advisory_logic(self):
        self.assertIn("Low", _uv_advisory(1.5))
        self.assertIn("Moderate", _uv_advisory(4.0))
        self.assertIn("High", _uv_advisory(7.0))
        self.assertIn("Very High", _uv_advisory(9.5))
        self.assertIn("Extreme", _uv_advisory(12.0))

    def test_wind_compass_logic(self):
        self.assertEqual(_wind_compass(0), "N (0°)")
        self.assertEqual(_wind_compass(90), "E (90°)")
        self.assertEqual(_wind_compass(180), "S (180°)")
        self.assertEqual(_wind_compass(270), "W (270°)")
        self.assertEqual(_wind_compass(350), "N (350°)")


class TestWeatherAgentToolsOnline(unittest.TestCase):
    """Integration tests that execute actual HTTPS requests to verifying API compatibility."""

    def test_online_current_weather(self):
        # We run this on a popular city to ensure live API is up and geocoding works
        response = get_current_weather("Singapore")
        if response["status"] == "error":
            self.skipTest(f"Live API request failed: {response['error_message']}")
        
        self.assertEqual(response["status"], "success")
        report = response["report"]
        self.assertEqual(report["city"], "Singapore")
        self.assertIsNotNone(report["temperature_c"])
        self.assertIsNotNone(report["temperature_f"])
        self.assertIsNotNone(report["humidity_percent"])

    def test_online_air_quality(self):
        response = get_air_quality("New York")
        if response["status"] == "error":
            self.skipTest(f"Live API request failed: {response['error_message']}")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["city"], "New York")
        self.assertIsNotNone(response["european_aqi"])


if __name__ == "__main__":
    unittest.main()
