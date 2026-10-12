"""Keyword-rule baseline from Discover (01-discover/cluster.py), as a function.

First matching rule wins. Used only to compare against the Sonnet classifier.
"""
import re

RULES = [
    ("Docs, CI and dev setup", r"^docs:|docs update|documentation|quickstart|numbered steps|broken (repo )?links|"
     r"link check|external links|linter|\btests?\b|\bci\b|mypy|publish|pypi|kubernetes|windows|dev ui|dev-ui|"
     r"adk web|\(dev\)|mermaid|guides|greenlet|deprecated|opentelemetry-api"),
    ("Security, auth and data leaks", r"leak|cross-principal|forge|secret|exception (text|details)|raw exception|"
     r"api key|oauth|credential|scope|oidc|verified email|dns-rebind|capability bleed|collide|de-identification|"
     r"https for agent"),
    ("A2A interop", r"a2a"),
    ("Eval, tracing and observability", r"\beval|agentevaluator|evaluator\b|metric|rubric|judge|span|telemetry|"
     r"safety_v|hallucination|conformance|analytics|logger"),
    ("Tools", r"mcp|openapi|restapitool|functiontool|function ?tool|bigquery|skill|operationid|integration|"
     r"tool result|tool:|schema|edit ?file|readfile|code_executor|preloadmemorytool|positional|toolset|"
     r"google_search|tools limit|agent ?registry|semaprax|noveum|foundgine|settlement"),
    ("Sessions, state and memory", r"sessionservice|session service|session/|session:|firestore|sqlite|database|"
     r"redis|timestamp|migrat|memory|compaction|app:|temp:|last_update_time|session keys|session record"),
    ("Human-in-the-loop", r"confirm|approv|hitl|requestinput|resumable|resuming|rewind|replay|pause|"
     r"input_required|asks the user|deny"),
    ("Multi-agent orchestration", r"loopagent|sequentialagent|parallelagent|parallel|workflow|agenttool|"
     r"agent ?node|sub-agent|subagent|transfer|joinnode|single_turn|planner|agent graph|coordinator|task agent|"
     r"find_agent|runconfig|stack|agent\.context|redeliver"),
    ("Model providers and streaming", r"stream|\blive\b|run_live|runlive|litellm|thought|gemini|anthropic|"
     r"claude|apigee|sse|thinking|vertex|interactions|spring-ai|chrome|gemma|context cach|priority|partial|"
     r"mojibak|chunk|webmcp"),
    ("Core runtime", r"runner|instruction|\$\{|callback|nil|null|panic|deadlock|hang|artifact|bundle"),
]


def rules_classify(issues: list[dict]) -> dict:
    out = {}
    for x in issues:
        out[x["url"]] = next((name for name, p in RULES if re.search(p, x["title"], re.I)), "Other")
    return out
