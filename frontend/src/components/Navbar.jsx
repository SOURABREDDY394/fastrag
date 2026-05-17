import { BookOpen, Home, Layers3, Workflow } from "lucide-react";

const navItems = [
  { label: "Home", href: "#home", icon: Home },
  { label: "Features", href: "#story", icon: Layers3 },
  { label: "Workspace", href: "#workspace", icon: BookOpen },
  { label: "How It Works", href: "#story", icon: Workflow },
];

function Navbar() {
  return (
    <nav className="sticky top-0 z-40 border-b border-charcoal/10 bg-paper/88 backdrop-blur-xl">
      <div className="mx-auto flex h-[4.75rem] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <a href="#home" className="flex min-w-0 items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center border border-charcoal bg-white text-teal-700 shadow-[6px_6px_0_#111315]">
            <BookOpen size={23} strokeWidth={2.4} />
          </div>
          <span className="text-xl font-black tracking-normal text-charcoal">
            Study<span className="text-teal-700">RAG</span>
          </span>
        </a>

        <div className="hidden items-center gap-1 lg:flex">
          {navItems.map((item) => {
            const Icon = item.icon;

            return (
              <a
                key={item.label}
                href={item.href}
                className="flex items-center gap-2 px-4 py-2 text-sm font-black text-slate-600 transition hover:bg-charcoal hover:text-white"
              >
                <Icon size={16} />
                {item.label}
              </a>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
