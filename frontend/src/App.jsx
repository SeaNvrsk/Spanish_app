import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Lesson from "./pages/Lesson";
import Review from "./pages/Review";
import Leaderboard from "./pages/Leaderboard";
import Profile from "./pages/Profile";
import Vocabulary from "./pages/Vocabulary";
import BottomNav from "./components/BottomNav";
import TopBar from "./components/TopBar";
import RulesGate from "./components/RulesGate";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="flex h-screen items-center justify-center text-4xl">🌮</div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Shell({ children }) {
  const location = useLocation();
  const hideChrome = location.pathname.startsWith("/lesson/") || location.pathname.startsWith("/review");
  return (
    <RulesGate>
      <div className="flex h-dvh max-h-[100dvh] w-full flex-col overflow-hidden bg-slate-50 lg:mx-auto lg:max-w-lg lg:shadow-xl">
        {!hideChrome && <TopBar />}
        <main
          className={`min-h-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-y-contain ${
            hideChrome ? "" : "pb-nav"
          }`}
        >
          {children}
        </main>
        {!hideChrome && <BottomNav />}
      </div>
    </RulesGate>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Shell>
              <Dashboard />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/lesson/:lessonId"
        element={
          <Protected>
            <Shell>
              <Lesson />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/review"
        element={
          <Protected>
            <Shell>
              <Review />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/ranking"
        element={
          <Protected>
            <Shell>
              <Leaderboard />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/profile"
        element={
          <Protected>
            <Shell>
              <Profile />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/vocabulary"
        element={
          <Protected>
            <Shell>
              <Vocabulary />
            </Shell>
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
