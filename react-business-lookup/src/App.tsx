import { Navigate, Route, Routes } from 'react-router-dom';
import { LookupApp } from './LookupApp';
import { ConsoleApp } from './ConsoleApp';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { LoginPage } from './pages/LoginPage';
import { ProtectedRoute } from './components/ProtectedRoute';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/bulk" element={<ProtectedRoute><LookupApp initialTab="bulk" activeNav="business-lookup" /></ProtectedRoute>} />
      <Route path="/single" element={<ProtectedRoute><LookupApp initialTab="single" activeNav="business-lookup" /></ProtectedRoute>} />
      <Route path="/console" element={<Navigate to="/console/manual" replace />} />
      <Route path="/console/manual" element={<ProtectedRoute><ConsoleApp /></ProtectedRoute>} />
      <Route path="/console/bulk" element={<ProtectedRoute><ConsoleApp /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
