"use client";

import { useParams } from "next/navigation";

import { AuthGate } from "@/components/AuthGate";
import { RunDetail } from "@/components/run/RunDetail";

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <AuthGate>
      <RunDetail runId={id} />
    </AuthGate>
  );
}
