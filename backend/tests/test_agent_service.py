import asyncio
import json
import unittest
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import (
    FakeListChatModel,
    FakeMessagesListChatModel,
)
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.tools import tool
from pydantic import Field

from app.common.exceptions import BusinessException
from app.hooks import course_guardrails
from app.schemas.chat import ChatMessage
from app.services import agent_service


class RecordingStreamingModel(FakeListChatModel):
    """Emit real LangChain model events without an external provider."""

    calls: list[list[BaseMessage]] = Field(default_factory=list)

    def _call(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        return super()._call(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        async for chunk in super()._astream(
            messages, stop=stop, run_manager=run_manager, **kwargs
        ):
            yield chunk


class ScriptedChatModel(FakeMessagesListChatModel):
    """Exercise the real agent graph and tool loop with scripted responses."""

    calls: list[list[BaseMessage]] = Field(default_factory=list)
    review_model: BaseChatModel

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        return self.review_model | PydanticOutputParser(pydantic_object=schema)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class StreamingChatModel(RecordingStreamingModel):
    review_model: BaseChatModel

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        return self.review_model | PydanticOutputParser(pydantic_object=schema)


def reviewer(decision="allow", **kwargs):
    return RecordingStreamingModel(
        responses=[json.dumps({"decision": decision})], **kwargs
    )


def schedule_call(call_id="schedule-call"):
    return AIMessage(
        content="",
        tool_calls=[{
            "name": "get_my_schedules",
            "args": {"date": "2026-11-19"},
            "id": call_id,
            "type": "tool_call",
        }],
    )


async def collect_stream(question, history=None):
    return [
        json.loads(chunk.removeprefix("data: ").strip())
        async for chunk in agent_service.stream_ask(
            question, history or [], "Bearer alice"
        )
    ]


class AgentServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tool_calls = []

        @tool
        async def get_my_schedules(date: str | None = None) -> dict:
            """Query the current user schedule."""
            self.tool_calls.append(date)
            return {"items": [{"course_name": "Python", "date": date}], "count": 1}

        self.tools = [get_my_schedules]

    def test_prompt_supplies_english_language_and_correct_calendar_context(self):
        prompt = agent_service._build_system_prompt(date(2026, 11, 18))
        self.assertIn("Respond in English", prompt)
        self.assertIn("Today is 2026-11-18 (Wednesday)", prompt)
        self.assertIn("2026-11-16 (Monday)", prompt)
        self.assertIn("2026-11-22 (Sunday)", prompt)
        self.assertIn("Preserve course names and locations exactly", prompt)

    async def test_both_paths_request_english_despite_previous_chinese_replies(self):
        history = [
            ChatMessage(role="user", content="Show my schedule"),
            ChatMessage(role="assistant", content="\u4eca\u5929\u6ca1\u6709\u8bfe\u7a0b\u3002"),
        ]
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                model = ScriptedChatModel(
                    responses=[AIMessage(content="No classes are scheduled today.")],
                    review_model=reviewer(),
                )
                with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                    agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                ):
                    if streaming:
                        result = (await collect_stream("Show my schedule", history))[-1]
                    else:
                        result = await agent_service.ask("Show my schedule", history, "Bearer alice")
                self.assertIn("Respond in English", model.calls[0][0].content)
                self.assertIn("earlier replies used another language", model.calls[0][0].content)
                self.assertEqual(result["answer"], "No classes are scheduled today.")

    async def test_allow_preserves_history_and_reviews_only_once(self):
        history = [
            ChatMessage(role="user", content="What classes do I have today?"),
            ChatMessage(role="assistant", content="You have Python today."),
        ]
        model = ScriptedChatModel(
            responses=[schedule_call(), AIMessage(content="You have Python tomorrow.")],
            review_model=reviewer(),
        )
        with patch.object(agent_service, "_build_model", return_value=model), patch.object(
            agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
        ):
            result = await agent_service.ask("And tomorrow?", history, "Bearer alice")

        self.assertEqual(result, {
            "answer": "You have Python tomorrow.", "tools_used": ["get_my_schedules"]
        })
        self.assertEqual(len(model.review_model.calls), 1)
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(self.tool_calls, ["2026-11-19"])
        review_input = json.loads(model.review_model.calls[0][-1].content)
        self.assertEqual(review_input["question"], "And tomorrow?")
        self.assertEqual(review_input["history"], [message.model_dump() for message in history])
        self.assertEqual([message.type for message in model.calls[0]], ["system", "human", "ai", "human"])
        self.assertIn(date.today().isoformat(), model.calls[0][0].content)
        self.assertIsInstance(model.calls[1][-1], ToolMessage)
        self.assertNotIn("Bearer alice", str(model.review_model.calls) + str(model.calls))
        self.assertEqual(len(history), 2)

    async def test_deny_and_clarify_skip_business_model_in_both_paths(self):
        for decision, expected in (
            ("deny", course_guardrails.REFUSAL_MESSAGE),
            ("clarify", course_guardrails.CLARIFICATION_MESSAGE),
        ):
            for streaming in (False, True):
                with self.subTest(decision=decision, streaming=streaming):
                    model = ScriptedChatModel(
                        responses=[AIMessage(content="MUST NOT BE GENERATED")],
                        review_model=reviewer(decision),
                    )
                    with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                        agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                    ):
                        if streaming:
                            events = await collect_stream("Write Tetris for my Python course")
                            self.assertFalse(any(event["type"] == "token" for event in events))
                            self.assertFalse(any(event["type"] == "tool_start" for event in events))
                            self.assertFalse(any(event["type"] == "error" for event in events))
                            self.assertEqual(events[-1], {"type": "done", "answer": expected, "tools_used": []})
                            self.assertNotIn('"decision"', str(events))
                        else:
                            result = await agent_service.ask(
                                "Write Tetris for my Python course", [], "Bearer alice"
                            )
                            self.assertEqual(result, {"answer": expected, "tools_used": []})
                    self.assertEqual(model.calls, [])
                    self.assertEqual(len(model.review_model.calls), 1)
        self.assertEqual(self.tool_calls, [])

    async def test_stream_forwards_answer_tokens_without_review_tokens(self):
        answer = "You have Python tomorrow."
        model = StreamingChatModel(responses=[answer], review_model=reviewer())
        with patch.object(agent_service, "_build_model", return_value=model), patch.object(
            agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
        ):
            events = await collect_stream("What classes do I have tomorrow?")

        tokens = [event["content"] for event in events if event["type"] == "token"]
        self.assertEqual("".join(tokens), answer)
        self.assertEqual(events[-1], {"type": "done", "answer": answer, "tools_used": []})
        self.assertNotIn('"decision"', str(events))
        self.assertNotIn(course_guardrails.REVIEW_PROMPT, str(events))
        self.assertEqual(len(model.review_model.calls), 1)
        self.assertEqual(len(model.calls), 1)

    async def test_stream_retains_tool_events_and_final_tool_names(self):
        model = ScriptedChatModel(
            responses=[schedule_call(), AIMessage(content="You have Python tomorrow.")],
            review_model=reviewer(),
        )
        with patch.object(agent_service, "_build_model", return_value=model), patch.object(
            agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
        ):
            events = await collect_stream("What classes do I have tomorrow?")
        self.assertIn({"type": "tool_start", "name": "get_my_schedules"}, events)
        self.assertIn({"type": "tool_end", "name": "get_my_schedules"}, events)
        self.assertEqual(events[-1]["tools_used"], ["get_my_schedules"])
        self.assertEqual(events[-1]["answer"], "You have Python tomorrow.")
        self.assertEqual(len(model.review_model.calls), 1)

    async def test_invalid_review_results_stop_both_paths_without_leaking_output(self):
        for output in (
            "PRIVATE INVALID REVIEW",
            '{"decision": "run_arbitrary_code"}',
            '{"decision": "allow", "reason": "PRIVATE REVIEW DETAILS"}',
        ):
            for streaming in (False, True):
                with self.subTest(output=output, streaming=streaming):
                    model = ScriptedChatModel(
                        responses=[AIMessage(content="MUST NOT BE GENERATED")],
                        review_model=RecordingStreamingModel(responses=[output]),
                    )
                    with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                        agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                    ):
                        if streaming:
                            events = await collect_stream("What classes do I have tomorrow?")
                            self.assertEqual(events[-1]["type"], "error")
                            self.assertIn("review is temporarily unavailable", events[-1]["message"])
                            self.assertFalse(any(event["type"] == "token" for event in events))
                            self.assertNotIn("PRIVATE", str(events))
                        else:
                            with self.assertRaises(BusinessException) as caught:
                                await agent_service.ask("What classes do I have tomorrow?", [], "Bearer alice")
                            self.assertEqual(caught.exception.code, 503)
                            self.assertNotIn("PRIVATE", caught.exception.message)
                    self.assertEqual(model.calls, [])
        self.assertEqual(self.tool_calls, [])

    async def test_review_timeout_stops_both_paths(self):
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                model = ScriptedChatModel(
                    responses=[AIMessage(content="MUST NOT BE GENERATED")],
                    review_model=reviewer(sleep=1),
                )
                with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                    agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                ), patch.object(course_guardrails, "REVIEW_TIMEOUT_SECONDS", 0.001):
                    if streaming:
                        events = await collect_stream("What classes do I have tomorrow?")
                        self.assertEqual(events[-1]["type"], "error")
                    else:
                        with self.assertRaises(BusinessException) as caught:
                            await agent_service.ask("What classes do I have tomorrow?", [], "Bearer alice")
                        self.assertEqual(caught.exception.code, 503)
                self.assertEqual(model.calls, [])
        self.assertEqual(self.tool_calls, [])

    async def test_blank_question_returns_clarification_without_any_model_call(self):
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                model = ScriptedChatModel(
                    responses=[AIMessage(content="MUST NOT BE GENERATED")], review_model=reviewer()
                )
                with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                    agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                ):
                    if streaming:
                        result = (await collect_stream(" \n\t "))[-1]
                    else:
                        result = await agent_service.ask(" \n\t ", [], "Bearer alice")
                self.assertEqual(result["answer"], course_guardrails.CLARIFICATION_MESSAGE)
                self.assertEqual(model.calls, [])
                self.assertEqual(model.review_model.calls, [])

    async def test_review_uses_recent_context_but_preserves_full_business_history(self):
        history = [ChatMessage(role="user", content=f"Schedule question {index}") for index in range(12)]
        model = ScriptedChatModel(responses=[AIMessage(content="Your schedule.")], review_model=reviewer())
        with patch.object(agent_service, "_build_model", return_value=model), patch.object(
            agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
        ):
            await agent_service.ask("And tomorrow?", history, "Bearer alice")
        context = json.loads(model.review_model.calls[0][-1].content)["history"]
        self.assertEqual(context, [message.model_dump() for message in history[-8:]])
        self.assertEqual(len(model.calls[0]), len(history) + 2)

    async def test_default_step_budget_supports_six_tool_round_trips_with_review(self):
        model = ScriptedChatModel(
            responses=[schedule_call(f"call-{index}") for index in range(6)] + [AIMessage(content="Your schedule.")],
            review_model=reviewer(),
        )
        with patch.object(agent_service, "_build_model", return_value=model), patch.object(
            agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
        ):
            result = await agent_service.ask("Show my schedule", [], "Bearer alice")
        self.assertEqual(result["answer"], "Your schedule.")
        self.assertEqual(len(self.tool_calls), 6)
        self.assertEqual(len(model.review_model.calls), 1)

    async def test_recursion_limit_stops_repeated_tool_calls_in_both_paths(self):
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                model = ScriptedChatModel(
                    responses=[schedule_call(f"call-{index}") for index in range(10)],
                    review_model=reviewer(),
                )
                with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                    agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                ), patch.object(agent_service.settings, "AGENT_RECURSION_LIMIT", 3):
                    if streaming:
                        result = (await collect_stream("Show my schedule"))[-1]
                        self.assertEqual(result["type"], "error")
                        self.assertIn("Too many processing steps", result["message"])
                    else:
                        with self.assertRaises(BusinessException) as caught:
                            await agent_service.ask("Show my schedule", [], "Bearer alice")
                        self.assertIn("Too many processing steps", caught.exception.message)

    async def test_empty_answer_is_rejected_in_both_paths(self):
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                model = ScriptedChatModel(responses=[AIMessage(content="   ")], review_model=reviewer())
                with patch.object(agent_service, "_build_model", return_value=model), patch.object(
                    agent_service, "_load_mcp_tools", AsyncMock(return_value=self.tools)
                ):
                    if streaming:
                        result = (await collect_stream("Show my schedule"))[-1]
                        self.assertEqual(result["type"], "error")
                        self.assertIn("did not generate a final answer", result["message"])
                    else:
                        with self.assertRaises(BusinessException) as caught:
                            await agent_service.ask("Show my schedule", [], "Bearer alice")
                        self.assertIn("did not generate a final answer", caught.exception.message)

    async def test_concurrent_requests_keep_credentials_and_review_context_isolated(self):
        invocations = []

        def make_client(connections):
            authorization = connections["campus"]["headers"]["Authorization"]

            @tool
            async def get_my_schedules(date: str | None = None) -> dict:
                """Query the current user schedule."""
                await asyncio.sleep(0)
                invocations.append((authorization, date))
                return {"owner": authorization.removeprefix("Bearer "), "count": 1}

            return Mock(get_tools=AsyncMock(return_value=[get_my_schedules]))

        models = [
            ScriptedChatModel(responses=[schedule_call(), AIMessage(content=f"{name} schedule")], review_model=reviewer())
            for name in ("Alice", "Bob")
        ]
        with patch.object(agent_service, "MultiServerMCPClient", side_effect=make_client), patch.object(
            agent_service, "_build_model", side_effect=models
        ):
            results = await asyncio.gather(
                agent_service.ask("Alice schedule", [], "Bearer alice"),
                agent_service.ask("Bob schedule", [], "Bearer bob"),
            )
        self.assertEqual([result["answer"] for result in results], ["Alice schedule", "Bob schedule"])
        self.assertCountEqual(invocations, [("Bearer alice", "2026-11-19"), ("Bearer bob", "2026-11-19")])
        for model, owner in zip(models, ("alice", "bob")):
            self.assertIn(f'"owner": "{owner}"', model.calls[1][-1].content)
            self.assertNotIn("Bearer ", str(model.review_model.calls) + str(model.calls))

    async def test_invalid_authorization_is_rejected_before_mcp_discovery(self):
        with patch.object(agent_service, "MultiServerMCPClient") as client:
            for authorization in ("", "Basic abc", "Bearer", "Bearer   ", "   "):
                with self.subTest(authorization=authorization):
                    with self.assertRaises(BusinessException) as caught:
                        await agent_service._load_mcp_tools(authorization)
                    self.assertEqual(caught.exception.code, 401)
        client.assert_not_called()

    async def test_mcp_failure_and_empty_tools_report_service_unavailable(self):
        with patch.object(agent_service, "MultiServerMCPClient") as client:
            for tools, error in (([], None), (None, ConnectionError("private connection details"))):
                with self.subTest(error=error):
                    client.return_value.get_tools = AsyncMock(return_value=tools, side_effect=error)
                    with self.assertRaises(BusinessException) as caught:
                        await agent_service._load_mcp_tools("Bearer alice")
                    self.assertEqual(caught.exception.code, 503)
                    self.assertNotIn("private", caught.exception.message)

    async def test_missing_model_key_fails_before_mcp_access(self):
        with patch.object(agent_service.settings, "LLM_API_KEY", ""), patch.object(
            agent_service, "_load_mcp_tools", AsyncMock()
        ) as load:
            with self.assertRaises(BusinessException) as caught:
                await agent_service.ask("Show my schedule", [], "Bearer alice")
        self.assertIn("LLM_API_KEY", caught.exception.message)
        load.assert_not_awaited()

    def test_text_blocks_exclude_internal_reasoning(self):
        result = agent_service._read_result([AIMessage(content=[
            {"type": "reasoning", "reasoning": "PRIVATE REASONING"},
            {"type": "text", "text": "  You have Python "},
            {"type": "text", "text": "tomorrow.  "},
        ])])
        self.assertEqual(result, {"answer": "You have Python tomorrow.", "tools_used": []})


if __name__ == "__main__":
    unittest.main()
