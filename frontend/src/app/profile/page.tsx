"use client";

import { AuthGate } from "@/components/AuthGate";
import { ProfileBuilder } from "@/components/profile/ProfileBuilder";

export default function ProfilePage() {
  return (
    <AuthGate>
      <div className="space-y-6">
        <header className="space-y-2">
          <h1 className="font-serif text-4xl">Your profile</h1>
          <p className="max-w-2xl text-muted">
            Everything the agent may say about you comes from here. Write freely in each section;
            the AI organises it into a structured profile, asks about gaps, and you review it before
            saving. Your answers are saved as you type and stay on your machine.
          </p>
        </header>
        <ProfileBuilder />
      </div>
    </AuthGate>
  );
}
