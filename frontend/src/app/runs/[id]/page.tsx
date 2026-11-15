"use client";

import { useParams } from "next/navigation";
import { Suspense } from "react";

import { AuthGate } from "@/components/AuthGate";
import { RunDetail } from "@/components/run/RunDetail";
import { Spinner } from "@/components/ui";

function RunFromUrl() {
  const { id } = useParams<{ id: string }>();
  return <RunDetail runId={id} />;
}

export default function RunPage() {
  return (
    <AuthGate>
      {/* The run id comes from the URL, which is only known at request time. */}
      <Suspense fallback={<Spinner label="Loading…" />}>
        <RunFromUrl />
      </Suspense>
    </AuthGate>
  );
}
