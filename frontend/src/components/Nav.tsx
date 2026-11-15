"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAgent } from "@/lib/agent-context";

const LINKS = [
  { href: "/", label: "New application" },
  { href: "/applications", label: "Applications" },
  { href: "/profile", label: "Profile" },
];

export function Nav() {
  const agent = useAgent();
  const router = useRouter();
  const path = usePathname();
  if (path === "/login") return null;

  async function logout() {
    await agent.logout();
    router.replace("/login");
  }

  return (
    <header className="border-b border-line">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 sm:px-6">
        <Link href="/" className="mr-auto font-serif text-xl">
          Job Agent
        </Link>
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`text-sm hover:text-ink ${path === l.href ? "text-ink" : "text-muted"}`}
          >
            {l.label}
          </Link>
        ))}
        {!agent.demo && (
          <button onClick={logout} className="text-sm text-muted hover:text-ink">
            Log out
          </button>
        )}
      </nav>
    </header>
  );
}
