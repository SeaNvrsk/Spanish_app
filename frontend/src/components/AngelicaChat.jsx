import { useEffect, useRef, useState } from "react";
import api from "../api";
import { useI18n } from "../i18n";
import { useKeyboardInset } from "../useKeyboardInset";
import { useSpeak } from "../tts";
import { ToolSheet } from "./ToolsFooter";

function AngelicaSpeakButton({ text }) {
  const { t } = useI18n();
  const { speak, speaking } = useSpeak("angelica");
  return (
    <button
      type="button"
      onClick={() => speak(text)}
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pink-500 text-sm text-white shadow-md shadow-pink-500/30 transition active:scale-90 ${
        speaking ? "animate-pulse" : ""
      }`}
      aria-label={t("playAudio")}
    >
      🔊
    </button>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 sm:max-w-[85%] ${
          isUser
            ? "rounded-br-md bg-teal-600 text-white"
            : "rounded-bl-md border border-pink-100 bg-gradient-to-br from-pink-50 to-violet-50 text-slate-800"
        }`}
      >
        {!isUser && (
          <p className="mb-1 text-[10px] font-extrabold uppercase tracking-wide text-pink-500">Angélica</p>
        )}
        <div className="flex items-end gap-2">
          <p className="min-w-0 flex-1 whitespace-pre-wrap text-[15px] font-semibold leading-snug">{msg.content}</p>
          {!isUser && <AngelicaSpeakButton text={msg.content} />}
        </div>
      </div>
    </div>
  );
}

export function AngelicaPanel({ onClose }) {
  const { t } = useI18n();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState(null);
  const listRef = useRef(null);
  const { keyboardInset } = useKeyboardInset(true);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
    });
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/angelica/history");
        if (!cancelled) setMessages(data.messages || []);
      } catch {
        if (!cancelled) setError(t("angelicaError"));
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    const optimistic = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setLoading(true);
    try {
      const { data } = await api.post("/angelica/send", { message: text });
      setMessages((prev) => [...prev.filter((m) => m.id !== optimistic.id), optimistic, data.message]);
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
      setInput(text);
      setError(err.response?.data?.detail || t("angelicaError"));
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    if (!window.confirm(t("angelicaClearConfirm"))) return;
    try {
      await api.delete("/angelica/history");
      const { data } = await api.get("/angelica/history");
      setMessages(data.messages || []);
      setError(null);
    } catch {
      setError(t("angelicaError"));
    }
  };

  const footer = (
    <div
      className="shrink-0 border-t border-slate-100 bg-white px-3 pt-2 sm:px-5"
      style={{ paddingBottom: `calc(0.75rem + ${keyboardInset}px + env(safe-area-inset-bottom, 0px))` }}
    >
      {error && <p className="mb-2 text-center text-xs font-semibold text-red-600">{String(error)}</p>}
      <div className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("angelicaPlaceholder")}
          rows={1}
          enterKeyHint="send"
          className="mobile-field max-h-28 min-h-[2.75rem] flex-1 resize-none rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-[15px] font-medium text-slate-800 outline-none focus:border-pink-400"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button
          type="button"
          disabled={loading || !input.trim()}
          onClick={send}
          className="mobile-btn shrink-0 rounded-2xl bg-pink-500 px-4 font-extrabold text-white disabled:opacity-50 active:scale-[0.99]"
        >
          {loading ? "…" : "➤"}
        </button>
      </div>
      <p className="mt-1.5 text-center text-[10px] font-medium text-slate-400">{t("angelicaHint")}</p>
    </div>
  );

  return (
    <ToolSheet
      open
      title={t("angelica")}
      icon="👩‍🎓"
      onClose={onClose}
      footer={footer}
    >
      <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-3 flex shrink-0 items-start gap-3 rounded-2xl border border-pink-100 bg-pink-50/80 p-3">
        <span className="text-3xl">👩‍🎓</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-extrabold text-pink-800">{t("angelicaBio")}</p>
          <p className="mt-0.5 text-[11px] font-medium leading-snug text-pink-700/80">{t("angelicaBioSub")}</p>
        </div>
        <button
          type="button"
          onClick={clearChat}
          className="shrink-0 rounded-full px-2 py-1 text-[10px] font-bold text-slate-400 active:bg-pink-100"
        >
          {t("angelicaClear")}
        </button>
      </div>

      <div ref={listRef} className="min-h-0 flex-1 space-y-2.5 overflow-y-auto overscroll-y-contain pb-2">
        {booting ? (
          <p className="py-8 text-center text-sm font-semibold text-slate-400">{t("angelicaLoading")}</p>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)
        )}
        {loading && (
          <p className="text-center text-xs font-semibold text-pink-500 animate-pulse">{t("angelicaTyping")}</p>
        )}
      </div>
      </div>
    </ToolSheet>
  );
}
