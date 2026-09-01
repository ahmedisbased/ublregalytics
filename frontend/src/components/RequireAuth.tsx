import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import api from "../services/api";

// Fast local check: kills missing / malformed / expired tokens with no server round-trip.
function tokenLooksValid(): boolean {
  const token = localStorage.getItem("token");
  if (!token) return false;
  try {
    const payload = JSON.parse(
      atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))
    );
    return typeof payload.exp === "number" && payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export default function RequireAuth({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"checking" | "ok" | "fail">("checking");

  useEffect(() => {
    if (!tokenLooksValid()) {
      setStatus("fail");
      return;
    }
    // Authoritative check: ask the backend. A forged/invalid token -> 401 -> fail.
    api
      .get("me")
      .then(() => setStatus("ok"))
      .catch(() => setStatus("fail"));
  }, []);

  if (status === "checking") return null; // or a spinner — prevents any flash of the page
  if (status === "fail") return <Navigate to="/login" replace />;
  return <>{children}</>;
}