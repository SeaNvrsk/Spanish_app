import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../auth";
import { useI18n, LANGUAGES, achievementLabel } from "../i18n";
import { RulesModal } from "../components/RulesGate";
import { Link } from "react-router-dom";

const AVATARS = ["🦊", "🐱", "🐶", "🐼", "🦉", "🐸", "🦁", "🐨", "🐵", "🦄", "🐷", "🐯"];

function StatCard({ icon, label, value, color }) {
  return (
    <div className="rounded-2xl bg-white p-3 shadow-sm sm:p-4">
      <div className="text-xl sm:text-2xl">{icon}</div>
      <div className={`mt-0.5 text-xl font-black sm:mt-1 sm:text-2xl ${color}`}>{value}</div>
      <div className="text-[11px] font-semibold leading-tight text-slate-400 sm:text-xs">{label}</div>
    </div>
  );
}

function ActivityChart({ activity, t }) {
  const days = [];
  const map = {};
  activity.forEach((a) => (map[a.day] = a.pesos));
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    days.push({ key, pesos: map[key] || 0 });
  }
  const max = Math.max(2, ...days.map((d) => d.pesos));
  return (
    <div className="overflow-hidden rounded-2xl bg-white p-3 shadow-sm sm:p-4">
      <p className="mb-2 text-sm font-extrabold text-slate-700 sm:mb-3">{t("last30days")}</p>
      <div className="flex h-20 min-w-0 items-end gap-px sm:h-24 sm:gap-0.5">
        {days.map((d) => (
          <div
            key={d.key}
            title={`${d.key}: $${d.pesos}`}
            className="min-w-0 flex-1 rounded-t bg-amber-400"
            style={{ height: `${Math.max(4, (d.pesos / max) * 100)}%`, opacity: d.pesos ? 1 : 0.25 }}
          />
        ))}
      </div>
    </div>
  );
}

function AchievementBadge({ ach, t }) {
  return (
    <div
      className={`flex flex-col items-center rounded-2xl border p-2 text-center sm:p-3 ${
        ach.unlocked
          ? "border-amber-200 bg-amber-50 shadow-sm"
          : "border-slate-100 bg-slate-50 opacity-45 grayscale"
      }`}
      title={achievementLabel(ach.id, t)}
    >
      <span className="text-2xl sm:text-3xl">{ach.icon}</span>
      <p className="mt-1 line-clamp-2 text-[10px] font-bold leading-tight text-slate-600 sm:text-[11px]">
        {achievementLabel(ach.id, t)}
      </p>
    </div>
  );
}

export default function Profile() {
  const { user, logout, updateUser } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [stats, setStats] = useState(null);
  const [achievements, setAchievements] = useState(null);
  const [name, setName] = useState(user?.name || "");
  const [avatar, setAvatar] = useState(user?.avatar || "🦊");
  const [savedMsg, setSavedMsg] = useState(false);
  const [showRules, setShowRules] = useState(false);

  useEffect(() => {
    api.get("/stats").then(({ data }) => setStats(data));
    api.get("/achievements").then(({ data }) => setAchievements(data)).catch(() => {});
  }, []);

  const save = async (patch) => {
    const { data } = await api.patch("/users/me", patch);
    updateUser(data);
    if (patch.ui_language) setLang(patch.ui_language);
    setSavedMsg(true);
    setTimeout(() => setSavedMsg(false), 1500);
  };

  if (!user) return null;

  return (
    <div className="min-w-0 px-3 py-3 sm:px-4 sm:py-4">
      <div className="mb-4 flex items-center gap-3 rounded-2xl bg-gradient-to-br from-teal-600 to-emerald-600 p-4 text-white shadow-lg sm:mb-5 sm:gap-4 sm:p-5">
        <span className="shrink-0 text-4xl sm:text-5xl">{user.avatar}</span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-extrabold sm:text-xl">{user.name}</h1>
          <p className="mt-0.5 text-xs leading-snug text-teal-100 sm:text-sm">
            {stats?.is_admin ? (
              <>👑 {t("adminBadge")} · {t("notInRanking")}</>
            ) : (
              <>
                {t("currentLevel")}: {stats?.cefr_level || "A1"} · {t("rank")} #{stats?.rank ?? "-"} {t("of")}{" "}
                {stats?.total_users ?? "-"}
              </>
            )}
          </p>
        </div>
      </div>

      {stats && (
        <>
          <div className="mb-3 grid grid-cols-2 gap-2 sm:mb-4 sm:gap-3">
            <StatCard icon="$" label={t("pesosEarned")} value={stats.total_pesos} color="text-amber-600" />
            <StatCard icon="📚" label={t("lessonsCompleted")} value={stats.lessons_completed} color="text-indigo-600" />
            <StatCard icon="🔥" label={t("currentStreak")} value={stats.current_streak} color="text-orange-500" />
            <StatCard icon="🏅" label={t("longestStreak")} value={stats.longest_streak} color="text-purple-500" />
          </div>
          <div className="mb-3 sm:mb-4">
            <ActivityChart activity={stats.activity} t={t} />
          </div>
        </>
      )}

      {achievements && (
        <div className="mb-3 rounded-2xl bg-white p-3 shadow-sm sm:mb-4 sm:p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-extrabold uppercase tracking-wide text-slate-500">{t("achievements")}</h2>
              <p className="text-xs text-slate-400">{t("achievementsSub")}</p>
            </div>
            <span className="shrink-0 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-black text-amber-700">
              {achievements.unlocked_count}/{achievements.total_count}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {achievements.achievements.map((ach) => (
              <AchievementBadge key={ach.id} ach={ach} t={t} />
            ))}
          </div>
        </div>
      )}

      <Link
        to="/vocabulary"
        className="mb-3 flex items-center gap-3 rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3.5 text-left shadow-sm active:scale-[0.99] sm:mb-4"
      >
        <span className="text-2xl">📖</span>
        <div className="min-w-0 flex-1">
          <p className="font-extrabold text-teal-800">{t("myVocabulary")}</p>
          <p className="text-xs text-teal-600">{t("vocabularySub")}</p>
        </div>
        <span className="text-teal-500">→</span>
      </Link>

      <div className="mb-3 rounded-2xl bg-white p-3 shadow-sm sm:mb-4 sm:p-4">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wide text-slate-500">{t("settings")}</h2>

        <label className="mb-1 block text-xs font-bold text-slate-500">{t("name")}</label>
        <div className="mb-3 flex min-w-0 flex-col gap-2 sm:mb-4 sm:flex-row sm:items-center">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="min-w-0 w-full flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-base font-semibold text-slate-800 outline-none focus:border-teal-500"
          />
          <button
            type="button"
            onClick={() => save({ name, avatar })}
            className="w-full shrink-0 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-extrabold text-white active:scale-95 sm:w-auto"
          >
            {savedMsg ? t("saved") : t("save")}
          </button>
        </div>

        <label className="mb-2 block text-xs font-bold text-slate-500">{t("chooseAvatar")}</label>
        <div className="mb-3 grid grid-cols-6 gap-1.5 sm:mb-4 sm:flex sm:flex-wrap sm:gap-1.5">
          {AVATARS.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => {
                setAvatar(a);
                save({ name, avatar: a });
              }}
              className={`flex aspect-square items-center justify-center rounded-xl text-2xl sm:p-1.5 ${
                avatar === a ? "bg-teal-100 ring-2 ring-teal-500" : "bg-slate-50"
              }`}
            >
              {a}
            </button>
          ))}
        </div>

        <label className="mb-2 block text-xs font-bold text-slate-500">{t("interfaceLanguage")}</label>
        <div className="grid grid-cols-3 gap-2">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => save({ ui_language: l.code })}
              className={`min-h-[44px] rounded-xl border-2 px-1 py-2 text-xs font-bold ${
                lang === l.code ? "border-teal-500 bg-teal-50 text-teal-700" : "border-slate-100 text-slate-500"
              }`}
            >
              <span className="block text-base">{l.flag}</span>
              <span className="mt-0.5 block truncate text-[10px] leading-tight">{l.label}</span>
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowRules(true)}
        className="mb-3 w-full rounded-2xl border border-amber-200 bg-amber-50 py-3 text-sm font-extrabold text-amber-700 active:scale-95 sm:mb-4"
      >
        📜 {t("viewRules")}
      </button>

      <button
        type="button"
        onClick={logout}
        className="mb-2 w-full rounded-2xl bg-red-50 py-3 text-sm font-extrabold text-red-500 active:scale-95"
      >
        {t("logout")}
      </button>

      <RulesModal open={showRules} onClose={() => setShowRules(false)} />
    </div>
  );
}
