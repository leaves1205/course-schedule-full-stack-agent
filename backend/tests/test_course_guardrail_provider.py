import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.hooks import course_guardrails
from app.services import agent_service


def completion(decision):
    return httpx.Response(200, json={
        "id": "review-test",
        "object": "chat.completion",
        "created": 0,
        "model": "deepseek-flash",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": json.dumps({"decision": decision})},
            "finish_reason": "stop",
        }],
    })


class CourseGuardrailProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_deepseek_review_uses_json_without_forcing_tools_or_mutating_model(self):
        payloads = []

        async def respond(request):
            payloads.append(json.loads(request.content))
            return completion("clarify")

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = ChatOpenAI(
                api_key="test-only-key",
                base_url="https://api.deepseek.com/v1",
                model="deepseek-flash",
                http_async_client=client,
                extra_body={"thinking": {"type": "enabled"}, "custom_flag": "preserve"},
            )
            result = await course_guardrails._build_reviewer(model).ainvoke([
                SystemMessage(content=course_guardrails.REVIEW_PROMPT),
                HumanMessage(content='{"question":"hello","history":[]}'),
            ])

        self.assertEqual(result.decision, "clarify")
        self.assertEqual(len(payloads), 1)
        body = payloads[0]
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["custom_flag"], "preserve")
        self.assertFalse(body["stream"])
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body.get("max_completion_tokens", body.get("max_tokens")), 128)
        self.assertNotIn("tools", body)
        self.assertNotIn("tool_choice", body)
        self.assertEqual(model.extra_body["thinking"], {"type": "enabled"})

    async def test_other_providers_do_not_receive_deepseek_thinking_option(self):
        payloads = []

        async def respond(request):
            payloads.append(json.loads(request.content))
            return completion("allow")

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = ChatOpenAI(
                api_key="test-only-key",
                base_url="https://compatible.example/v1",
                model="compatible-model",
                http_async_client=client,
            )
            result = await course_guardrails._build_reviewer(model).ainvoke("Schedule query")
        self.assertEqual(result.decision, "allow")
        self.assertNotIn("thinking", payloads[0])
        self.assertNotIn("tool_choice", payloads[0])

    async def test_real_client_review_returns_fixed_responses_in_ask_and_stream(self):
        @tool
        def get_my_schedules(date: str | None = None) -> dict:
            """This tool must not run for rejected or vague requests."""
            raise AssertionError("The tool must not run")

        for decision, expected in (
            ("clarify", course_guardrails.CLARIFICATION_MESSAGE),
            ("deny", course_guardrails.REFUSAL_MESSAGE),
        ):
            for streaming in (False, True):
                with self.subTest(decision=decision, streaming=streaming):
                    payloads = []

                    async def respond(request):
                        body = json.loads(request.content)
                        self.assertEqual(body["response_format"], {"type": "json_object"})
                        self.assertNotIn("tool_choice", body)
                        payloads.append(body)
                        return completion(decision)

                    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                        model = ChatOpenAI(
                            api_key="test-only-key", base_url="https://api.deepseek.com",
                            model="deepseek-flash", http_async_client=client,
                        )
                        with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                            agent_service, "_load_mcp_tools", AsyncMock(return_value=[get_my_schedules])
                        ):
                            if streaming:
                                events = [
                                    json.loads(chunk.removeprefix("data: ").strip())
                                    async for chunk in agent_service.stream_ask("hello", [], "Bearer alice")
                                ]
                                self.assertEqual(events[-1], {
                                    "type": "done", "answer": expected, "tools_used": []
                                })
                                self.assertFalse(any(event["type"] == "token" for event in events))
                                self.assertNotIn('"decision"', str(events))
                            else:
                                result = await agent_service.ask("hello", [], "Bearer alice")
                                self.assertEqual(result, {"answer": expected, "tools_used": []})
                    self.assertEqual(len(payloads), 1)


if __name__ == "__main__":
    unittest.main()
