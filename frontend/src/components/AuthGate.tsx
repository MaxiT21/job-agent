"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { useAgent } from "@/lib/agent-context";

/** Renders children only for a logged-in user; otherwise goes to /login. */
export function AuthGate({ children }: { children: ReactNode }) {
  const agent = useAgent();
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    agent.me().then((authenticated) => {
      if (authenticated) setOk(true);
      else router.replace("/login");
    });
  }, [agent, router]);

  return ok ? children : null;
}
