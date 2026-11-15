import type { NextConfig } from "next";

// Two builds from one codebase:
//  - private app (default): /api/* is proxied to the FastAPI backend (same-origin cookie,
//    the backend URL stays server-side)
//  - public demo (NEXT_PUBLIC_DEMO=1): no backend at all, recorded runs only
const demo = process.env.NEXT_PUBLIC_DEMO === "1";
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
const PORTFOLIO = "https://maximotorassa.vercel.app";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  experimental: {
    // The profile draft is one LLM call that can take up to a minute.
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return demo ? [] : [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          // The demo may be embedded by the portfolio; the private app never.
          {
            key: "Content-Security-Policy",
            value: `frame-ancestors ${demo ? `'self' ${PORTFOLIO}` : "'none'"}`,
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
