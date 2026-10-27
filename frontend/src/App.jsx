import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AppLayout from "./layouts/AppLayout.jsx";
import { useAuth } from "./hooks/useAuth.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Upload from "./pages/Upload.jsx";
import History from "./pages/History.jsx";
import Timeline from "./pages/Timeline.jsx";
import ScheduleStatus from "./pages/ScheduleStatus.jsx";
import Vaccines from "./pages/Vaccines.jsx";
import Reminders from "./pages/Reminders.jsx";
import Profile from "./pages/Profile.jsx";
import Report from "./pages/Report.jsx";
import NotFound from "./pages/NotFound.jsx";

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (!loading && user) return <Navigate to="/app" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
      <Route path="/app" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="history" element={<History />} />
        <Route path="timeline" element={<Timeline />} />
        <Route path="schedule" element={<ScheduleStatus />} />
        <Route path="vaccines" element={<Vaccines />} />
        <Route path="reminders" element={<Reminders />} />
        <Route path="report" element={<Report />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
