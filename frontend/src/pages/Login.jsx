import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useI18n, LANGUAGES } from "../i18n";

const AVATARS = ["🦊", "🐱", "🐶", "🐼", "🦉", "🐸", "🦁", "🐨", "🐵", "🦄", "🐷", "🐯"];

const fieldClass =
  "mobile-field w-full rounded-2xl border-2 border-slate-200 bg-white px-4 text-slate-800 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200";

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
    <div className="login-screen">
      <div className="login-header">
        <div className="login-emoji">🌮</div>
        <h1 className="mt-3 text-2xl font-extrabold leading-tight">{t("appName")}</h1>
        <p className="mt-1.5 text-base text-teal-50">{t("tagline")}</p>

        <div className="mt-5 px-1">
          <p className="mb-2.5 text-xs font-bold uppercase tracking-wider text-teal-100">
            {t("interfaceLanguage")}
          </p>
          <div className="lang-row">
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                type="button"
                onClick={() => setLang(l.code)}
                aria-label={l.label}
                aria-pressed={lang === l.code}
                className={`lang-btn ${
                  lang === l.code ? "bg-white/30 ring-2 ring-white/80" : "bg-white/10"
                }`}
              >
                <span aria-hidden>{l.flag}</span>
                <span className="lang-btn-label text-white">{l.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="login-form-sheet animate-slideup">
        <h2 className="mb-5 text-center text-2xl font-extrabold text-slate-800">
          {mode === "login" ? t("welcomeBack") : t("joinFamily")}
        </h2>

        <form onSubmit={submit} className="flex flex-1 flex-col gap-5">
          {mode === "register" && (
            <>
              <input
                className={fieldClass}
                placeholder={t("name")}
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                required
              />
              <div>
                <p className="mb-3 text-sm font-bold text-slate-500">{t("chooseAvatar")}</p>
                <div className="grid grid-cols-4 gap-2.5 sm:grid-cols-6 sm:gap-3">
                  {AVATARS.map((a) => (
                    <button
                      type="button"
                      key={a}
                      onClick={() => setAvatar(a)}
                      className={`flex aspect-square items-center justify-center rounded-2xl text-3xl transition active:scale-95 ${
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
            className={fieldClass}
            placeholder={t("email")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            inputMode="email"
            required
          />
          <input
            type="password"
            className={fieldClass}
            placeholder={t("password")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={6}
          />

          {error && <p className="text-base font-semibold text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="mobile-btn mt-auto w-full rounded-2xl bg-teal-600 font-extrabold text-white shadow-lg shadow-teal-600/30 transition active:scale-[0.98] disabled:opacity-60"
          >
            {busy ? "..." : mode === "login" ? t("login") : t("createAccount")}
          </button>
        </form>

        <div className="mt-5 text-center text-base text-slate-500">
          {mode === "login" ? t("noAccount") : t("haveAccount")}{" "}
          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
            className="inline-flex min-h-[48px] items-center font-extrabold text-teal-600 underline-offset-2 active:underline"
          >
            {mode === "login" ? t("register") : t("login")}
          </button>
        </div>
      </div>
    </div>
  );
}
