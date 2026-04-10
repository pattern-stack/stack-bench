#!/usr/bin/env python3
"""Bridge between agentic-tui's JSON-RPC stdio protocol and Claude Code CLI.

Translates JSON-RPC requests into `claude -p` invocations and streams
Claude's stream-json output back as JSON-RPC stream.event notifications.

Usage (with agentic-tui):
    BackendStdio: &tui.StdioConfig{Command: "python3", Args: []string{"agent.py"}}
"""

import json
import subprocess
import sys
import uuid

MODEL = "sonnet"

# Track session IDs for multi-turn conversations
sessions = {}


def write(obj):
    print(json.dumps(obj), flush=True)


def notify(event_type, data):
    write({"jsonrpc": "2.0", "method": "stream.event", "params": {"type": event_type, "data": data}})


def respond(req_id, result):
    write({"jsonrpc": "2.0", "result": result, "id": req_id})


def respond_error(req_id, code, message):
    write({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id})


def display_type_for(tool_name):
    if tool_name in ("Bash",):
        return "bash"
    if tool_name in ("Edit", "Write"):
        return "diff"
    if tool_name in ("Read", "Glob", "Grep"):
        return "code"
    return "generic"


def handle_send_message(params, req_id):
    content = params.get("content", "")
    conversation_id = params.get("conversation_id", "")

    cmd = [
        "claude", "-p",
        "--output-format", "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--bare",
        "--model", MODEL,
    ]

    # Resume existing session for multi-turn
    session_id = sessions.get(conversation_id)
    if session_id:
        cmd.extend(["--resume", session_id])

    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        proc.stdin.write(content)
        proc.stdin.close()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            translate(event, conversation_id)

        proc.wait()
    except FileNotFoundError:
        notify("message.delta", {"delta": "Error: `claude` CLI not found in PATH\n"})
    except Exception as e:
        notify("error", {"error_type": "bridge_error", "message": str(e)})

    notify("done", {})
    respond(req_id, {"status": "complete"})


def translate(event, conversation_id):
    etype = event.get("type", "")

    if etype == "system" and event.get("subtype") == "init":
        sid = event.get("session_id")
        if sid and conversation_id:
            sessions[conversation_id] = sid

    elif etype == "stream_event":
        inner = event.get("event", {})
        itype = inner.get("type", "")

        if itype == "content_block_delta":
            delta = inner.get("delta", {})
            dt = delta.get("type", "")
            if dt == "text_delta":
                notify("message.delta", {"delta": delta.get("text", "")})
            elif dt == "thinking_delta":
                notify("thinking", {"content": delta.get("thinking", "")})

        elif itype == "content_block_start":
            block = inner.get("content_block", {})
            if block.get("type") == "tool_use":
                notify("tool.start", {
                    "tool_call_id": block.get("id", ""),
                    "tool_name": block.get("name", ""),
                    "display_type": display_type_for(block.get("name", "")),
                })
            elif block.get("type") == "thinking":
                notify("thinking", {"content": ""})

        elif itype == "message_delta":
            delta = inner.get("delta", {})
            if delta.get("stop_reason") == "end_turn":
                usage = inner.get("usage", {})
                notify("message.complete", {
                    "content": "",
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                })

    elif etype == "assistant":
        # Check for tool results in the message
        msg = event.get("message", {})
        for part in msg.get("content", []):
            if part.get("type") == "tool_result":
                result_text = ""
                for c in (part.get("content") or []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        result_text += c.get("text", "")
                    elif isinstance(c, str):
                        result_text += c
                is_error = part.get("is_error", False)
                notify("tool.end", {
                    "tool_call_id": part.get("tool_use_id", ""),
                    "result": result_text if not is_error else "",
                    "error": result_text if is_error else "",
                    "display_type": "generic",
                })


def handle(method, params, req_id):
    if method == "listAgents":
        respond(req_id, [{"id": "claude", "name": "Claude", "role": "AI assistant", "model": MODEL}])
    elif method == "createConversation":
        respond(req_id, {"id": f"conv-{uuid.uuid4().hex[:8]}", "agent_id": params.get("agent_id", "claude")})
    elif method == "sendMessage":
        handle_send_message(params, req_id)
    elif method in ("listConversations", "getConversation"):
        respond_error(req_id, -32601, "Method not supported")
    else:
        respond_error(req_id, -32601, f"Method not found: {method}")


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
    except json.JSONDecodeError:
        continue
    handle(req.get("method", ""), req.get("params", {}), req.get("id"))
