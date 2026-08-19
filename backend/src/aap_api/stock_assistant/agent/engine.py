"""Gemini tool-calling agent, ported from AAP/AAP_AI_AGENT/streamlit_app.py.

The agent loops: model response -> execute tool calls -> feed results back,
until the model produces a text answer.
"""

import inspect
import re
import typing

from google.genai import types

from ...gemini import get_client
from .rag.knowledge_base import init_kb
from .tools import TOOL_REGISTRY, get_tools
from .tools.user_context import set_user_id

MODEL = "gemini-2.5-flash"
MAX_TURNS = 10

SYSTEM_PROMPT = """You are an Investment Research Assistant. You provide information, data, analysis, and suggestions only. You do not execute trades or provide financial advice.

RULES:
- ALWAYS cite your sources by including the source URL from the tool output.
- NEVER recommend buying, selling, or holding any security. You can provide suggestions, data, and analysis to inform the user's own decisions.
- If asked to execute a trade or perform an action on your behalf (e.g., "Buy $100 of AAPL", "Sell my shares", "Place an order"), explain that you can only give suggestions and cannot execute trades. Your function is to provide information, data, and analysis. Remind the user to trade with caution and consult a qualified financial advisor.
- When asked for buy/sell advice, respond with relevant data (price, analyst ratings, fundamentals) AND remind the user you can only give suggestions, not personalized advice. Lead with data, not refusal.
- ALWAYS perform any arithmetic or calculation through the calculation tools — calculate, calculate_returns, moving_average, volatility, correlation, portfolio_stats, time_value, cagr, linear_trend. NEVER compute numbers yourself. If a numeric result is needed (sums, differences, percentages, returns, averages, ratios, conversions, compound growth, CAGR, volatility, correlations), call the appropriate math tool and report its output exactly. Do not calculate by hand even for simple arithmetic — a query like "10% of 250" or "5 * 3" still requires a calculate call.
- When a user asks about investment strategy, how to invest, or what to do with money (e.g., "I have $50,000 to invest"), use the portfolio tools (read_portfolio, get_portfolio_summary) to analyze their holdings and provide data-driven observations. Always include a disclaimer. Do NOT refuse these queries.
- When asked about topics unrelated to investing, portfolio management, or financial markets, politely decline and explain that you can only assist with investment-related queries.
- When analyzing a portfolio, provide specific numbers, percentages, and actionable insights without making specific buy/sell recommendations. Compute figures and percentages with the calculate tool."""

_resources = None


def _to_schema_type(py_type):
    origin = typing.get_origin(py_type)
    if origin is typing.Union:
        for arg in typing.get_args(py_type):
            if arg is not type(None):
                return _to_schema_type(arg)
    return {
        str: types.Type.STRING,
        int: types.Type.INTEGER,
        float: types.Type.NUMBER,
        bool: types.Type.BOOLEAN,
    }.get(py_type, types.Type.STRING)


def _parse_args_section(doc_body: str) -> dict[str, str]:
    """Parse an 'Args:' block from a docstring into {param: description}."""
    result = {}
    in_args = False
    for line in (doc_body or "").split("\n"):
        stripped = line.strip()
        if stripped == "Args:":
            in_args = True
            continue
        if in_args:
            if not stripped:
                break
            m = re.match(r"^[-*]?\s*(\w+):\s*(.*)$", stripped)
            if m:
                result[m.group(1)] = m.group(2)
    return result


def make_tool_declarations():
    result = []
    entries = sorted(
        TOOL_REGISTRY.items(),
        key=lambda kv: (0 if kv[1]["category"] == "math" else 1, kv[0]),
    )
    for name, entry in entries:
        func = entry["function"]
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""
        doc_body = doc.strip()
        first_line, _, _ = doc_body.partition("\n")
        desc = first_line
        arg_docs = _parse_args_section(doc_body)

        props = {}
        required = []
        for pname, p in sig.parameters.items():
            if pname == "self":
                continue
            at = p.annotation if p.annotation is not inspect.Parameter.empty else str
            schema = types.Schema(type=_to_schema_type(at))
            if pname in arg_docs:
                schema.description = arg_docs[pname]
            props[pname] = schema
            if p.default is inspect.Parameter.empty:
                required.append(pname)

        result.append(types.Tool(
            function_declarations=[types.FunctionDeclaration(
                name=name,
                description=desc,
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=props,
                    required=required or None,
                ),
            )]
        ))
    return result


def get_resources():
    """Lazily initialize the client, tool declarations, and knowledge base."""
    global _resources
    if _resources is None:
        client = get_client()
        init_kb(client)
        config = types.GenerateContentConfig(
            tools=make_tool_declarations(),
            system_instruction=SYSTEM_PROMPT,
        )
        callables = {name: entry["function"] for name, entry in TOOL_REGISTRY.items()}
        _resources = (client, config, callables)
    return _resources


def agent_generate(history, user_text, user_id=None):
    """Run the agent loop. Yields ("tool_call", name, args), ("tool_result", name, result),
    ("text", reply), or ("error", message). history is a list of google.genai.types.Content.
    user_id is the authenticated user whose portfolio the tools read.
    """
    client, config, callables = get_resources()
    set_user_id(user_id)

    history.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_text)],
    ))

    for _ in range(MAX_TURNS):
        response = client.models.generate_content(
            model=MODEL, contents=history, config=config,
        )

        if not response.candidates:
            yield "error", "No response from model"
            return

        content = response.candidates[0].content
        fc_parts = [p for p in content.parts if p.function_call]
        text_parts = [p for p in content.parts if p.text]

        if fc_parts:
            history.append(content)
            resp_parts = []
            for part in fc_parts:
                fc = part.function_call
                args = dict(fc.args.items())
                yield "tool_call", fc.name, args
                func = callables[fc.name]
                try:
                    result = func(**args)
                except Exception as e:
                    result = f"Error: {e}"
                yield "tool_result", fc.name, str(result)
                resp_parts.append(types.Part.from_function_response(
                    name=fc.name, response={"result": result},
                ))
            history.append(types.Content(role="user", parts=resp_parts))
        elif text_parts:
            full_text = "\n".join(p.text for p in text_parts)
            yield "text", full_text
            history.append(content)
            return
        else:
            return

    yield "error", "Agent exceeded maximum turn limit"


def run_agent(history, user_text, user_id=None):
    """Convenience wrapper: returns (reply, tool_calls) where tool_calls is a list of
    {"name", "args", "result"} dicts for the frontend trace.
    """
    tool_calls = []
    reply = ""
    for event in agent_generate(history, user_text, user_id):
        kind = event[0]
        if kind == "tool_call":
            tool_calls.append({
                "name": event[1],
                "args": event[2],
                "result": "",
                "category": TOOL_REGISTRY.get(event[1], {}).get("category", "core"),
            })
        elif kind == "tool_result":
            if tool_calls:
                tool_calls[-1]["result"] = event[2]
        elif kind == "text":
            reply = event[1]
        elif kind == "error":
            reply = f"⚠️ {event[1]}"
    return reply, tool_calls
