// Supabase Edge Function: CORS proxy to the Blotato API.
//
// Blotato's backend only returns Access-Control-Allow-Origin to my.blotato.com,
// so the storefront calendar (on GitHub Pages) cannot call it from the browser.
// This function forwards the request to Blotato and adds the CORS header the
// browser needs. It is a Blotato-only relay — the target host is hard-coded, so
// it cannot be used as an open proxy to anywhere else. The blotato-api-key is
// passed straight through and never stored.

const BLOTATO_BASE = "https://backend.blotato.com/v2";
const SLUG = "/blotato-proxy";

function corsHeaders(origin: string): HeadersInit {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "content-type,blotato-api-key,authorization",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin") || "*";

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }

  // Everything after the function slug becomes the Blotato sub-path.
  const url = new URL(req.url);
  const idx = url.pathname.indexOf(SLUG);
  const sub = idx >= 0 ? url.pathname.slice(idx + SLUG.length) : url.pathname;
  const target = BLOTATO_BASE + sub + url.search;

  // Forward only the headers Blotato needs; drop hop-by-hop and Supabase auth.
  const fwd = new Headers();
  const ct = req.headers.get("content-type");
  const key = req.headers.get("blotato-api-key");
  if (ct) fwd.set("content-type", ct);
  if (key) fwd.set("blotato-api-key", key);

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers: fwd,
      body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.text(),
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ message: "proxy could not reach Blotato: " + String(err) }),
      { status: 502, headers: { ...corsHeaders(origin), "content-type": "application/json" } },
    );
  }

  const body = await upstream.text();
  const headers = new Headers(corsHeaders(origin));
  headers.set("content-type", upstream.headers.get("content-type") || "application/json");
  return new Response(body, { status: upstream.status, headers });
});
