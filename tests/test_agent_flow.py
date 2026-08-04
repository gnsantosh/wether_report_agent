import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add workspace path to sys.path so we can import from global_weather_agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from global_weather_agent.agent import root_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

class TestWeatherAgentFlow(unittest.TestCase):
    """Offline unit tests for the weather agent configuration and LLM flow."""

    def test_agent_configuration(self):
        """Verifies that the agent is initialized with correct properties."""
        self.assertEqual(root_agent.name, "global_weather_agent")
        self.assertIn("A global weather data agent", root_agent.description)
        
        # Verify tools are registered correctly
        tool_names = [tool.__name__ for tool in root_agent.tools]
        self.assertIn("get_current_weather", tool_names)
        self.assertIn("get_weather_forecast", tool_names)
        self.assertIn("compare_cities_weather", tool_names)
        self.assertIn("get_local_time", tool_names)
        self.assertIn("get_air_quality", tool_names)
        self.assertEqual(len(tool_names), 5)

    @patch("google.genai.Client")
    def test_agent_conversational_flow(self, mock_client_class):
        """Tests the full multi-turn conversational loop (calling a tool, and rendering output) using mocked LLM responses."""
        
        # 1. Setup mock Client instance
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.vertexai = False  # Ensure Gemini API backend path is chosen

        # 2. Setup mock return values using real GenerateContentResponse structures
        # Turn 1: LLM decides to call get_current_weather for "Paris"
        candidate_1 = types.Candidate(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            name="get_current_weather",
                            args={"city": "Paris"}
                        )
                    )
                ]
            ),
            finish_reason="STOP"
        )
        response_1 = types.GenerateContentResponse(
            candidates=[candidate_1],
            model_version="gemini-2.5-flash"
        )
        
        # Turn 2: LLM receives the weather data and answers the user
        candidate_2 = types.Candidate(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text="The current weather in Paris, France is 15.5°C (59.9°F), Overcast ☁️. Local time is 12:00 PM."
                    )
                ]
            ),
            finish_reason="STOP"
        )
        response_2 = types.GenerateContentResponse(
            candidates=[candidate_2],
            model_version="gemini-2.5-flash"
        )
        
        # Configure the async generator mock for api_client.aio.models.generate_content
        async_gen_mock = AsyncMock()
        async_gen_mock.side_effect = [response_1, response_2]
        mock_client.aio.models.generate_content = async_gen_mock

        # 3. Patch the Gemini.api_client property to return our mock_client
        with patch('google.adk.models.google_llm.Gemini.api_client', new_callable=unittest.mock.PropertyMock) as mock_prop:
            mock_prop.return_value = mock_client
            
            # 4. Initialize the Runner
            session_service = InMemorySessionService()
            runner = Runner(
                agent=root_agent,
                app_name="global_weather_agent",
                session_service=session_service,
                auto_create_session=True
            )
            
            # Prepare message
            user_msg = types.Content(
                role="user",
                parts=[types.Part.from_text(text="What is the weather in Paris?")]
            )
            
            # 5. Run the session and collect events
            events = []
            generator = runner.run(
                user_id="test_user_id",
                session_id="test_session_id",
                new_message=user_msg
            )
            for event in generator:
                events.append(event)
            
            # 6. Assertions
            self.assertEqual(len(events), 3)
            
            # Event 1: LLM outputs a tool call (role='model')
            event_1 = events[0]
            self.assertEqual(event_1.author, "global_weather_agent")
            self.assertEqual(event_1.content.role, "model")
            self.assertTrue(event_1.content.parts[0].function_call is not None)
            self.assertEqual(event_1.content.parts[0].function_call.name, "get_current_weather")
            self.assertEqual(event_1.content.parts[0].function_call.args["city"], "Paris")

            # Event 2: Runner executes the tool and outputs function_response (role='user')
            event_2 = events[1]
            self.assertEqual(event_2.author, "global_weather_agent")
            self.assertEqual(event_2.content.role, "user")
            self.assertTrue(event_2.content.parts[0].function_response is not None)
            self.assertEqual(event_2.content.parts[0].function_response.name, "get_current_weather")
            self.assertEqual(event_2.content.parts[0].function_response.response["status"], "success")

            # Event 3: LLM receives tool result and outputs final text response (role='model')
            event_3 = events[2]
            self.assertEqual(event_3.author, "global_weather_agent")
            self.assertEqual(event_3.content.role, "model")
            self.assertTrue(event_3.content.parts[0].text is not None)
            self.assertIn("Paris", event_3.content.parts[0].text)

            # Verify mock_client's generate_content was called twice
            self.assertEqual(async_gen_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
