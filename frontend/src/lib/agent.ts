import type { AgentClient } from "./client";
import { DemoClient } from "./demo-client";
import { HttpClient } from "./http-client";

export const isDemo = process.env.NEXT_PUBLIC_DEMO === "1";

/** The client for this build. The demo client fetches its recordings at runtime, so it is tiny. */
export function createAgent(): AgentClient {
  return isDemo ? new DemoClient() : new HttpClient();
}
