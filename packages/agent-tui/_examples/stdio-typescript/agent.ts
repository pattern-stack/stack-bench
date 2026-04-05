#!/usr/bin/env npx tsx
/** Minimal agent-tui stdio backend. Zero dependencies beyond Node. */
import * as readline from 'readline';

const rl = readline.createInterface({ input: process.stdin });

function write(obj: any) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function notify(params: any) {
  write({ jsonrpc: '2.0', method: 'stream.event', params });
}

rl.on('line', (line) => {
  const req = JSON.parse(line);
  const { method, params = {}, id } = req;

  if (method === 'listAgents') {
    write({ jsonrpc: '2.0', result: [{ id: 'default', name: 'Assistant', role: 'Helpful' }], id });
  } else if (method === 'createConversation') {
    write({ jsonrpc: '2.0', result: { id: 'conv-1', agent_id: params.agent_id ?? 'default' }, id });
  } else if (method === 'sendMessage') {
    for (const word of `You said: ${params.content}`.split(' ')) {
      notify({ type: 'message.delta', data: { delta: word + ' ' } });
    }
    notify({ type: 'done', data: {} });
    write({ jsonrpc: '2.0', result: { status: 'complete' }, id });
  } else {
    write({ jsonrpc: '2.0', error: { code: -32601, message: `Unknown: ${method}` }, id });
  }
});
