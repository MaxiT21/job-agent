import type { AgentClient } from "./client";
import { HttpClient } from "./http-client";

export const isDemo = process.env.NEXT_PUBLIC_DEMO === "1";

let client: AgentClient | undefined;

/** The client for this build. The demo client is loaded lazily so the private bundle never ships recordings. */
export async function getAgent(): Promise<AgentClient> {
  if (!client) {
    client = isDemo ? new (await import("./demo-client")).DemoClient() : new HttpClient();
  }
  return client;
}
