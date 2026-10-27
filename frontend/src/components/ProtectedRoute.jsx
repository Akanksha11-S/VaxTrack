import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { Spinner } from "./Feedback.jsx";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner label="Checking your session" className="min-h-screen" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}
