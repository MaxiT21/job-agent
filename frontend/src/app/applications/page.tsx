"use client";

import { ApplicationsTable } from "@/components/ApplicationsTable";
import { AuthGate } from "@/components/AuthGate";

export default function ApplicationsPage() {
  return (
    <AuthGate>
      <div className="space-y-6">
        <header className="space-y-2">
          <h1 className="font-serif text-4xl">Applications</h1>
          <p className="text-muted">
            Every approved application. The agent never sends anything: you apply, then update
            the status here.
          </p>
        </header>
        <ApplicationsTable />
      </div>
    </AuthGate>
  );
}
