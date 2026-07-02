import { useAuth } from "../auth";
import { useI18n } from "../i18n";

export default function TopBar() {
  const { user } = useAuth();
  const { t } = useI18n();
  if (!user) return null;
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-2 border-b border-slate-100 bg-white/90 px-3 py-2.5 backdrop-blur sm:px-4 sm:py-3">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <span className="shrink-0 text-xl sm:text-2xl">{user.avatar}</span>
        <span className="truncate font-extrabold text-slate-800">{user.name}</span>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">
        <div className="flex items-center gap-1 rounded-full bg-orange-50 px-2 py-1 text-xs font-bold text-orange-600 sm:px-3 sm:text-sm">
          <span aria-hidden>🔥</span>
          <span>{user.current_streak}</span>
        </div>
        <div className="flex items-center gap-0.5 rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 sm:px-3 sm:text-sm">
          <span aria-hidden>{t("pesoSymbol")}</span>
          <span>{user.pesos}</span>
        </div>
      </div>
    </header>
  );
}
