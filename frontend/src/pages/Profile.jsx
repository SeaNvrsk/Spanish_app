import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../auth";
import { useI18n, LANGUAGES } from "../i18n";
import { RulesModal } from "../components/RulesGate";

const AVATARS = ["🦊", "🐱", "🐶", "🐼", "🦉", "🐸", "🦁", "🐨", "🐵", "🦄", "🐷", "🐯"];

function StatCard({ icon, label, value, color }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="text-2xl">{icon}</div>
      <div className={`mt-1 text-2xl font-black ${color}`}>{value}</div>
      <div className="text-xs font-semibold text-slate-400">{label}</div>
    </div>
  );
}

function ActivityChart({ activity }) {
  const { t } = useI18n();
  // Build last 30 days array
  const days = [];
  const map = {};
  activity.forEach((a) => (map[a.day] = a.xp));
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    days.push({ key, xp: map[key] || 0 });
  }
  const max = Math.max(10, ...days.map((d) => d.xp));
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <p className="mb-3 text-sm font-extrabold text-slate-700">{t("last30days")}</p>
      <div className="flex h-24 items-end gap-0.5">
        {days.map((d) => (
          <div
            key={d.key}
            title={`${d.key}: ${d.xp} XP`}
            className="flex-1 rounded-t bg-teal-400"
            style={{ height: `${Math.max(4, (d.xp / max) * 100)}%`, opacity: d.xp ? 1 : 0.25 }}
          />
        ))}
      </div>
    </div>
  );
}

export default function Profile() {
  const { user, logout, updateUser, refresh } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [stats, setStats] = useState(null);
  const [name, setName] = useState(user?.name || "");
  const [avatar, setAvatar] = useState(user?.avatar || "🦊");
  const [savedMsg, setSavedMsg] = useState(false);
  const [showRules, setShowRules] = useState(false);

  useEffect(() => {
    api.get("/stats").then(({ data }) => setStats(data));
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
    <div className="px-4 py-4">
      {/* Header card */}
      <div className="mb-5 flex items-center gap-4 rounded-2xl bg-gradient-to-br from-teal-600 to-emerald-600 p-5 text-white shadow-lg">
        <span className="text-5xl">{user.avatar}</span>
        <div>
          <h1 className="text-xl font-extrabold">{user.name}</h1>
          <p className="text-sm text-teal-100">
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

      {/* Stats grid */}
      {stats && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3">
            <StatCard icon="💰" label={t("pesosEarned")} value={stats.total_pesos} color="text-amber-500" />
            <StatCard icon="⚡" label={t("totalXp")} value={stats.total_xp} color="text-teal-600" />
            <StatCard icon="📚" label={t("lessonsCompleted")} value={stats.lessons_completed} color="text-indigo-600" />
            <StatCard icon="🔥" label={t("currentStreak")} value={stats.current_streak} color="text-orange-500" />
            <StatCard icon="🏅" label={t("longestStreak")} value={stats.longest_streak} color="text-purple-500" />
          </div>
          <div className="mb-4">
            <ActivityChart activity={stats.activity} />
          </div>
        </>
      )}

      {/* Settings */}
      <div className="mb-4 rounded-2xl bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wide text-slate-500">{t("settings")}</h2>

        <label className="mb-1 block text-xs font-bold text-slate-500">{t("name")}</label>
        <div className="mb-4 flex gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 rounded-xl border border-slate-200 px-3 py-2 font-semibold text-slate-800 outline-none focus:border-teal-500"
          />
          <button
            onClick={() => save({ name, avatar })}
            className="rounded-xl bg-teal-600 px-4 font-extrabold text-white active:scale-95"
          >
            {savedMsg ? t("saved") : t("save")}
          </button>
        </div>

        <label className="mb-2 block text-xs font-bold text-slate-500">{t("chooseAvatar")}</label>
        <div className="mb-4 flex flex-wrap gap-1.5">
          {AVATARS.map((a) => (
            <button
              key={a}
              onClick={() => {
                setAvatar(a);
                save({ name, avatar: a });
              }}
              className={`rounded-xl p-1.5 text-2xl ${
                avatar === a ? "bg-teal-100 ring-2 ring-teal-500" : "bg-slate-50"
              }`}
            >
              {a}
            </button>
          ))}
        </div>

        <label className="mb-2 block text-xs font-bold text-slate-500">{t("interfaceLanguage")}</label>
        <div className="flex gap-2">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => save({ ui_language: l.code })}
              className={`flex-1 rounded-xl border-2 py-2 text-sm font-bold ${
                lang === l.code ? "border-teal-500 bg-teal-50 text-teal-700" : "border-slate-100 text-slate-500"
              }`}
            >
              {l.flag} {l.label}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => setShowRules(true)}
        className="mb-4 w-full rounded-2xl border border-amber-200 bg-amber-50 py-3 font-extrabold text-amber-700 active:scale-95"
      >
        📜 {t("viewRules")}
      </button>

      <button
        onClick={logout}
        className="w-full rounded-2xl bg-red-50 py-3 font-extrabold text-red-500 active:scale-95"
      >
        {t("logout")}
      </button>

      <RulesModal open={showRules} onClose={() => setShowRules(false)} />
    </div>
  );
}
