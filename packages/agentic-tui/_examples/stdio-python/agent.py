#!/usr/bin/env python3
"""Minimal agentic-tui stdio backend. Zero dependencies."""
import sys, json

def handle(method, params, req_id):
    if method == "listAgents":
        return {"result": [{"id": "default", "name": "Assistant", "role": "Helpful assistant"}], "id": req_id}
    elif method == "createConversation":
        return {"result": {"id": "conv-1", "agent_id": params.get("agent_id", "default")}, "id": req_id}
    elif method == "sendMessage":
        content = params["content"]
        for word in f"You said: {content}".split():
            notify({"type": "message.delta", "data": {"delta": word + " "}})
        notify({"type": "done", "data": {}})
        return {"result": {"status": "complete"}, "id": req_id}
    else:
        return {"error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id}

def notify(params):
    write({"jsonrpc": "2.0", "method": "stream.event", "params": params})

def write(obj):
    print(json.dumps(obj), flush=True)

for line in sys.stdin:
    req = json.loads(line.strip())
    resp = handle(req["method"], req.get("params", {}), req.get("id"))
    if resp:
        write({"jsonrpc": "2.0", **resp})
