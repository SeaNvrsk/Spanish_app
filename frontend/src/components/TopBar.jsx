import { useAuth } from "../auth";

export default function TopBar() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-100 bg-white/90 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{user.avatar}</span>
        <span className="font-extrabold text-slate-800">{user.name}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 rounded-full bg-orange-50 px-3 py-1 text-sm font-bold text-orange-600">
          <span>🔥</span>
          <span>{user.current_streak}</span>
        </div>
        <div className="flex items-center gap-1 rounded-full bg-amber-50 px-3 py-1 text-sm font-bold text-amber-600">
          <span>⭐</span>
          <span>{user.xp}</span>
        </div>
      </div>
    </header>
  );
}
