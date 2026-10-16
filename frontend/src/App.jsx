import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import { useAuth } from "./auth.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";

export default function App() {
  const { user } = useAuth();
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={user ? <DashboardPage /> : <AuthPage />} />
        <Route path="/u/:ownerId" element={<ProfilePage />} />
        <Route path="/settings" element={user ? <SettingsPage /> : <AuthPage />} />
        <Route path="/stats" element={<AnalyticsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
