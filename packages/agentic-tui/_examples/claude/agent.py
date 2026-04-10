#!/usr/bin/env python3
"""Bridge between agentic-tui JSON-RPC and Claude CLI stream-json.

Spawns `claude -p` per message, translates streaming events.
"""
import sys
import json
import subprocess
import threading

CLAUDE_MODEL = "sonnet"  # fast + cheap for testing


def handle(method, params, req_id):
    if method == "listAgents":
        return {
            "result": [
                {"id": "claude", "name": "Claude", "role": "AI assistant", "model": CLAUDE_MODEL}
            ],
            "id": req_id,
        }
    elif method == "createConversation":
        return {"result": {"id": "conv-1", "agent_id": params.get("agent_id", "claude")}, "id": req_id}
    elif method == "sendMessage":
        content = params.get("content", "")
        stream_claude(content)
        return {"result": {"status": "complete"}, "id": req_id}
    elif method == "listConversations":
        return {"error": {"code": -32601, "message": "Method not found"}, "id": req_id}
    elif method == "getConversation":
        return {"error": {"code": -32601, "message": "Method not found"}, "id": req_id}
    else:
        return {"error": {"code": -32601, "message": f"Unknown method: {method}"}, "id": req_id}


def stream_claude(content):
    """Run claude -p and translate stream events to JSON-RPC notifications."""
    cmd = [
        "claude", "-p", content,
        "--output-format", "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--bare",
        "--no-session-persistence",
        "--model", CLAUDE_MODEL,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        tool_inputs = {}  # track tool input accumulation by tool_use_id

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            translate_event(event, tool_inputs)

        proc.wait()
    except FileNotFoundError:
        notify("message.delta", {"delta": "Error: `claude` CLI not found in PATH"})
    except Exception as e:
        notify("error", {"error_type": "bridge_error", "message": str(e)})

    notify("done", {})


def translate_event(event, tool_inputs):
    """Translate a Claude stream-json event to an agentic-tui stream.event notification."""
    etype = event.get("type")

    if etype == "stream_event":
        inner = event.get("event", {})
        inner_type = inner.get("type")

        if inner_type == "content_block_delta":
            delta = inner.get("delta", {})
            delta_type = delta.get("type")

            if delta_type == "text_delta":
                notify("message.delta", {"delta": delta.get("text", "")})
            elif delta_type == "thinking_delta":
                notify("thinking", {"content": delta.get("thinking", "")})
            elif delta_type == "input_json_delta":
                # Accumulate tool input
                pass

        elif inner_type == "content_block_start":
            block = inner.get("content_block", {})
            if block.get("type") == "tool_use":
                tool_id = block.get("id", "")
                tool_name = block.get("name", "")
                # Determine display type from tool name
                display_type = "generic"
                if tool_name in ("Bash", "bash"):
                    display_type = "bash"
                elif tool_name in ("Edit", "Write"):
                    display_type = "diff"
                elif tool_name in ("Read", "Glob", "Grep"):
                    display_type = "code"
                notify("tool.start", {
                    "tool_call_id": tool_id,
                    "tool_name": tool_name,
                    "display_type": display_type,
                })
            elif block.get("type") == "thinking":
                notify("thinking", {"content": ""})

        elif inner_type == "content_block_stop":
            pass

        elif inner_type == "message_delta":
            # End of message — we'll send done after the result event
            pass

    elif etype == "assistant":
        # Complete message — tool results come through here
        msg = event.get("message", {})
        for block in msg.get("content", []):
            if block.get("type") == "tool_result":
                tool_id = block.get("tool_use_id", "")
                content = block.get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        p.get("text", "") for p in content if p.get("type") == "text"
                    )
                is_error = block.get("is_error", False)
                notify("tool.end", {
                    "tool_call_id": tool_id,
                    "result": content if not is_error else "",
                    "error": content if is_error else "",
                })


def notify(event_type, data):
    """Send a JSON-RPC stream.event notification."""
    write({
        "jsonrpc": "2.0",
        "method": "stream.event",
        "params": {"type": event_type, "data": data},
    })


def write(obj):
    print(json.dumps(obj), flush=True)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id")

        resp = handle(method, params, req_id)
        if resp:
            write({"jsonrpc": "2.0", **resp})


if __name__ == "__main__":
    main()
