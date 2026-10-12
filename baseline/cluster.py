import json,re,sys,random
from collections import Counter,defaultdict
X=json.load(open(sys.argv[1]))
noise=re.compile(r"^(google|jj|k|creste|new on|\[closed\]|orion|https?://|sawit|iogeminis|main branch gutted|where is the solution)",re.I)
rules=[
("Docs, CI and dev setup",r"^docs:|docs update|documentation|quickstart|numbered steps|broken (repo )?links|link check|external links|linter|\btests?\b|\bci\b|mypy|publish|pypi|kubernetes|windows|dev ui|dev-ui|adk web|\(dev\)|mermaid|guides|greenlet|deprecated|opentelemetry-api"),
("Security, auth and data leaks",r"leak|cross-principal|forge|secret|exception (text|details)|raw exception|api key|oauth|credential|scope|oidc|verified email|dns-rebind|capability bleed|collide|de-identification|https for agent"),
("A2A interop",r"a2a"),
("Eval, tracing and observability",r"\beval|agentevaluator|evaluator\b|metric|rubric|judge|span|telemetry|safety_v|hallucination|conformance|analytics|logger"),
("Tools: OpenAPI, MCP and function tools",r"mcp|openapi|restapitool|functiontool|function ?tool|bigquery|skill|operationid|integration|tool result|tool:|schema|edit ?file|readfile|code_executor|preloadmemorytool|positional|toolset|google_search|tools limit|agent ?registry|semaprax|noveum|foundgine|settlement"),
("Sessions, state and memory storage",r"sessionservice|session service|session/|session:|firestore|sqlite|database|redis|timestamp|migrat|memory|compaction|app:|temp:|last_update_time|session keys|session record"),
("Human-in-the-loop, confirm and resume",r"confirm|approv|hitl|requestinput|resumable|resuming|rewind|replay|pause|input_required|asks the user|deny"),
("Multi-agent and workflow orchestration",r"loopagent|sequentialagent|parallelagent|parallel|workflow|agenttool|agent ?node|sub-agent|subagent|transfer|joinnode|single_turn|planner|agent graph|coordinator|task agent|find_agent|runconfig|stack|agent\.context|redeliver"),
("Model providers, streaming and live",r"stream|\blive\b|run_live|runlive|litellm|thought|gemini|anthropic|claude|apigee|sse|thinking|vertex|interactions|spring-ai|chrome|gemma|context cach|priority|partial|mojibak|chunk|webmcp"),
("Core runtime bugs (runner, templating, callbacks)",r"runner|instruction|\$\{|callback|nil|null|panic|deadlock|hang|artifact|bundle"),
]
out=defaultdict(list)
for x in X:
  t=x["title"]
  if "spam" in x["labels"] or noise.match(t.strip()): out["Noise (spam, empty)"].append(x);continue
  for name,p in rules:
    if re.search(p,t,re.I): out[name].append(x);break
  else: out["Other"].append(x)
for k,v in sorted(out.items(),key=lambda kv:-len(kv[1])):
  pre=sum(1 for x in v if x["created"]<"2026-10-01"); post=len(v)-pre
  print(f"{len(v):3} pre={pre:3} post={post:3}  {k}")
json.dump({k:[(x['repo'],x['n'],x['title']) for x in v] for k,v in out.items()},open(sys.argv[2],"w"),indent=0)
if len(sys.argv)>3:
  random.seed(7); flat=[(k,x) for k,v in out.items() if not k.startswith("Noise") for x in v]
  for k,x in random.sample(flat,10): print("SPOT|",k,"|",x["repo"],x["n"],x["title"][:90])
