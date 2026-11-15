import Link from "next/link";

const LINKS = [
  { href: "/", label: "New application" },
  { href: "/applications", label: "Applications" },
  { href: "/profile", label: "Profile" },
];

export function Nav() {
  return (
    <header className="border-b border-line">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 sm:px-6">
        <Link href="/" className="mr-auto font-serif text-xl">
          Job Agent
        </Link>
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="text-sm text-muted hover:text-ink">
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
