import { useEffect, useState } from "react";
import api from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";

const medal = (rank) => (rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : null);

export default function Leaderboard() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [rows, setRows] = useState(null);
  const [rewards, setRewards] = useState(null);
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    api.get("/leaderboard").then(({ data }) => setRows(data));
    api.get("/rewards/summary").then(({ data }) => setRewards(data)).catch(() => {});
    if (user?.is_admin) {
      api.get("/admin/family-overview").then(({ data }) => setOverview(data)).catch(() => {});
    }
  }, [user?.is_admin]);

  if (!rows) return <div className="p-10 text-center text-4xl">🌮</div>;

  const isAdmin = user?.is_admin;
  const me = rewards?.me;

  return (
    <div className="px-4 py-4">
      {isAdmin && (
        <div className="mb-4 rounded-2xl border border-violet-200 bg-violet-50 px-4 py-3">
          <p className="text-sm font-extrabold text-violet-800">👑 {t("adminBadge")}</p>
          <p className="mt-1 text-xs text-violet-600">{t("adminExcluded")}</p>
        </div>
      )}

      {/* Monthly pesos challenge — competitors only */}
      {rewards && (
        <div className="mb-5 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 p-4 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-extrabold">💰 {t("monthlyChallenge")}</h1>
            <span className="rounded-full bg-white/25 px-2.5 py-1 text-xs font-black">
              {rewards.days_left} {t("daysLeftLabel")}
            </span>
          </div>
          <p className="mt-1 text-xs text-amber-50">{t("challengeSub")}</p>

          <div className="mt-3 space-y-2">
            {rewards.entries.map((e) => (
              <div
                key={e.id}
                className={`flex items-center gap-3 rounded-xl px-3 py-2 ${
                  e.is_me ? "bg-white/30" : "bg-white/10"
                }`}
              >
                <div className="w-7 text-center text-lg font-black">{medal(e.rank) || e.rank}</div>
                <span className="text-2xl">{e.avatar}</span>
                <div className="flex-1">
                  <p className="font-extrabold leading-tight">
                    {e.name} {e.is_me && <span className="text-[10px] font-bold">({t("you")})</span>}
                  </p>
                  {e.spend_percent > 0 && (
                    <p className="text-[10px] font-semibold text-amber-50">
                      {e.spend_percent}% · {e.spendable} 💰 {t("canSpend")}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-lg font-black">{e.month_pesos}</p>
                  <p className="text-[9px] font-bold uppercase text-amber-50">{t("pesos")}</p>
                </div>
              </div>
            ))}
          </div>

          {isAdmin && me?.excluded && (
            <p className="mt-3 rounded-xl bg-white/15 px-3 py-2 text-center text-xs font-semibold text-amber-50">
              {t("adminExcluded")} ({me.month_pesos} 💰 {t("monthPesos")} — {t("notInRanking")})
            </p>
          )}

          <p className="mt-3 text-[11px] leading-snug text-amber-50">{t("prizeNote")}</p>
        </div>
      )}

      {/* Admin: full family dashboard */}
      {isAdmin && overview && (
        <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-extrabold text-slate-800">📊 {t("familyOverview")}</h2>
          <p className="mb-3 text-xs text-slate-500">{t("familyOverviewSub")}</p>
          <div className="space-y-2">
            {overview.members.map((m) => (
              <div
                key={m.id}
                className={`rounded-xl border px-3 py-3 ${
                  m.is_admin ? "border-violet-200 bg-violet-50" : "border-slate-100 bg-slate-50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{m.avatar}</span>
                  <div className="flex-1">
                    <p className="font-extrabold text-slate-800">
                      {m.name}
                      {m.is_admin && (
                        <span className="ml-2 rounded-full bg-violet-200 px-2 py-0.5 text-[10px] font-bold text-violet-700">
                          {t("adminBadge")}
                        </span>
                      )}
                      {!m.is_admin && m.rank && (
                        <span className="ml-2 text-xs font-bold text-amber-600">
                          #{m.rank}
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-slate-500">
                      {m.cefr_level} · {m.lessons_completed} {t("lessonsDone")} · 🔥 {m.current_streak}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-black text-amber-600">{m.month_pesos} 💰</p>
                    <p className="text-[10px] text-slate-400">{t("monthPesos")}</p>
                    <p className="text-xs font-bold text-teal-600">{m.xp} XP</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All-time XP ranking — competitors only */}
      <h2 className="mb-2 px-1 text-sm font-extrabold uppercase tracking-wide text-slate-500">
        {t("allTimePoints")}
      </h2>
      <div className="space-y-2">
        {rows.map((r) => (
          <div
            key={r.id}
            className={`flex items-center gap-3 rounded-2xl border px-4 py-3 shadow-sm ${
              r.is_me ? "border-teal-300 bg-teal-50" : "border-slate-100 bg-white"
            }`}
          >
            <div className="w-8 text-center text-lg font-black text-slate-400">
              {medal(r.rank) || r.rank}
            </div>
            <span className="text-3xl">{r.avatar}</span>
            <div className="flex-1">
              <p className="font-extrabold text-slate-800">
                {r.name} {r.is_me && <span className="text-xs font-bold text-teal-600">({t("you")})</span>}
              </p>
              <p className="text-xs font-semibold text-orange-500">🔥 {r.current_streak}</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black text-teal-600">{r.xp}</p>
              <p className="text-[10px] font-bold uppercase text-slate-400">{t("totalXp")}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
