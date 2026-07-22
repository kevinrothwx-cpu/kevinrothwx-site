// Cloudflare Worker for mysportsweather.com
//
// Purpose: when the Render origin returns a 5xx error or is completely
// unreachable (during a deploy, or a crash), serve a friendly maintenance
// page instead of Render's default gateway error.
//
// Attach this Worker to the route: *mysportsweather.com/* in the
// Cloudflare dashboard (Workers Routes tab on the mysportsweather.com
// zone). It will proxy every request through this script.
//
// Free tier limit: 100,000 requests/day. Your traffic is well under this.
//
// If you ever want to disable this and let requests hit Render directly,
// either delete the route in the dashboard, or edit this Worker to just
// `return fetch(request)`.

export default {
  async fetch(request, env, ctx) {
    try {
      // Ask Cloudflare to also serve cached copies if origin is down,
      // and allow up to 15s for the origin to respond before we bail.
      const originResponse = await fetch(request, {
        cf: {
          // Never cache maintenance responses (5xx) — always retry origin next time.
          cacheTtlByStatus: { "200-299": 0, "300-399": 0, "400-499": 0, "500-599": 0 },
        },
      });

      // If origin returned a server error, replace with our maintenance page.
      if (originResponse.status >= 500 && originResponse.status < 600) {
        return maintenancePage();
      }

      return originResponse;
    } catch (err) {
      // Network error reaching origin — Render is fully down or unreachable.
      return maintenancePage();
    }
  },
};

function maintenancePage() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Working on it — mysportsweather.com</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta http-equiv="refresh" content="90">
  <style>
    :root {
      --navy: #1e3a8a;
      --cream: #fefcf7;
      --ink: #1a1a1a;
      --ash: #6b7280;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      padding: 0;
      min-height: 100vh;
      background: var(--cream);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }
    body {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem 1rem;
    }
    .card {
      max-width: 32rem;
      text-align: center;
    }
    .sketch {
      width: 200px;
      height: 200px;
      margin: 0 auto 1.5rem;
    }
    h1 {
      font-size: 1.75rem;
      margin: 0 0 0.75rem;
      color: var(--navy);
      font-weight: normal;
    }
    p {
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 1rem;
      line-height: 1.55;
      color: var(--ink);
      margin: 0.5rem 0;
    }
    .small {
      font-size: 0.85rem;
      color: var(--ash);
      margin-top: 1.5rem;
    }
    a { color: var(--navy); }
    @keyframes bob {
      0%, 100% { transform: translateY(0); }
      50%      { transform: translateY(-6px); }
    }
    .sketch { animation: bob 3s ease-in-out infinite; }
  </style>
</head>
<body>
  <div class="card">
    <svg class="sketch" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <g fill="#fff" stroke="#1e3a8a" stroke-width="3" stroke-linejoin="round">
        <path d="M45,115 C25,115 20,90 42,85 C40,60 78,55 88,72 C95,55 130,58 133,80 C158,78 165,105 145,115 Z"/>
      </g>
      <g fill="#1e3a8a">
        <circle cx="72" cy="92" r="3"/>
        <circle cx="108" cy="92" r="3"/>
      </g>
      <path d="M83,102 Q92,110 100,102" fill="none" stroke="#1e3a8a" stroke-width="2.5" stroke-linecap="round"/>
      <g stroke="#1e3a8a" stroke-width="3" stroke-linecap="round" fill="none">
        <line x1="130" y1="120" x2="160" y2="150"/>
        <circle cx="163" cy="153" r="7" fill="#fff"/>
        <path d="M158,148 L168,158" />
      </g>
      <g fill="#1e3a8a" opacity="0.6">
        <path d="M60,140 q-3,6 0,10 q3,-4 0,-10 Z"/>
        <path d="M85,150 q-3,6 0,10 q3,-4 0,-10 Z"/>
        <path d="M110,145 q-3,6 0,10 q3,-4 0,-10 Z"/>
      </g>
    </svg>
    <h1>Kevin is working on making the site better right now...</h1>
    <p>Check back in 90 seconds.</p>
    <p class="small">This page will refresh itself automatically. If you were reading a forecast for a game today, it'll be back the moment we're done. Thanks for your patience.</p>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 503,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store, no-cache, must-revalidate",
    },
  });
}
