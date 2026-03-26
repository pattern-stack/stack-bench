const ROUTES = {
  'stack-bench.pattern-stack.com': 'stack-bench-frontend-280512658750.northamerica-northeast2.run.app',
  'api.stack-bench.pattern-stack.com': 'stack-bench-backend-280512658750.northamerica-northeast2.run.app',
};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = ROUTES[url.hostname];

    if (!origin) {
      return new Response('Not found', { status: 404 });
    }

    // Rewrite to Cloud Run origin with correct Host header
    const newUrl = new URL(request.url);
    newUrl.hostname = origin;
    newUrl.protocol = 'https:';

    const newRequest = new Request(newUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow',
    });

    // Set the Host header to the Cloud Run hostname
    const headers = new Headers(newRequest.headers);
    headers.set('Host', origin);

    return fetch(newUrl, {
      method: request.method,
      headers,
      body: request.body,
    });
  },
};
