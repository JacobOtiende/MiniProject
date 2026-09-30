"""
Assembles the single ReAct agent: one model, one toolbelt, one system
prompt, running LangGraph's prebuilt tool-call loop. This replaces the old
custom multi-node graph entirely — there's no fixed node order here; the
loop is "call the model, if it asked for tools run them and feed results
back, repeat until it returns a final answer," which is what lets the model
decide its own sequence of actions instead of following a wired pipeline.
"""
from __future__ import annotations

from langchain.agents import create_agent

from agent.deps import Deps
from agent.system_prompt import SYSTEM_PROMPT
from agent.tools import build_tools


def build_agent(deps: Deps):
    tools = build_tools(deps)
    # The model has no clock; without this it can't turn "this Friday" into a due date.
    today = deps.now().strftime("%A, %Y-%m-%d")
    system_prompt = f"{SYSTEM_PROMPT}\n\nToday is {today}."
    return create_agent(model=deps.model, tools=tools, system_prompt=system_prompt)
