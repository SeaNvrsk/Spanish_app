import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useI18n, LANGUAGES } from "../i18n";

const AVATARS = ["🦊", "🐱", "🐶", "🐼", "🦉", "🐸", "🦁", "🐨", "🐵", "🦄", "🐷", "🐯"];

export default function Login() {
  const { user, login, register } = useAuth();
  const { t, lang, setLang } = useI18n();
  const navigate = useNavigate();

  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [avatar, setAvatar] = useState("🦊");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register({ email: email.trim(), name: name.trim(), password, avatar, ui_language: lang });
      }
      navigate("/");
    } catch {
      setError(mode === "login" ? t("loginError") : t("registerError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-teal-600 to-emerald-700 px-5 py-8">
      <div className="mx-auto flex max-w-md flex-col">
        <div className="mb-4 flex justify-end gap-1">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => setLang(l.code)}
              className={`rounded-full px-2.5 py-1 text-lg ${
                lang === l.code ? "bg-white/25" : "opacity-60"
              }`}
              title={l.label}
            >
              {l.flag}
            </button>
          ))}
        </div>

        <div className="mb-6 text-center text-white">
          <div className="text-6xl">🌮</div>
          <h1 className="mt-2 text-2xl font-extrabold">{t("appName")}</h1>
          <p className="mt-1 text-sm text-teal-50">{t("tagline")}</p>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-2xl animate-slideup">
          <h2 className="mb-4 text-center text-lg font-extrabold text-slate-800">
            {mode === "login" ? t("welcomeBack") : t("joinFamily")}
          </h2>

          <form onSubmit={submit} className="space-y-3">
            {mode === "register" && (
              <>
                <input
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 outline-none focus:border-teal-500"
                  placeholder={t("name")}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
                <div>
                  <p className="mb-2 text-xs font-bold text-slate-500">{t("chooseAvatar")}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {AVATARS.map((a) => (
                      <button
                        type="button"
                        key={a}
                        onClick={() => setAvatar(a)}
                        className={`rounded-xl p-1.5 text-2xl transition ${
                          avatar === a ? "bg-teal-100 ring-2 ring-teal-500" : "bg-slate-50"
                        }`}
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
            <input
              type="email"
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 outline-none focus:border-teal-500"
              placeholder={t("email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input
              type="password"
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 outline-none focus:border-teal-500"
              placeholder={t("password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />

            {error && <p className="text-sm font-semibold text-red-500">{error}</p>}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-xl bg-teal-600 py-3 font-extrabold text-white shadow-lg shadow-teal-600/30 transition active:scale-95 disabled:opacity-60"
            >
              {busy ? "..." : mode === "login" ? t("login") : t("createAccount")}
            </button>
          </form>

          <div className="mt-4 text-center text-sm text-slate-500">
            {mode === "login" ? t("noAccount") : t("haveAccount")}{" "}
            <button
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
              }}
              className="font-extrabold text-teal-600"
            >
              {mode === "login" ? t("register") : t("login")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
