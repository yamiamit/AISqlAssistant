import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardLayout from "./pages/DashboardLayout";
import ChatPage from "./pages/ChatPage";
import ChatHistoryPage from "./pages/ChatHistoryPage";
import SavedQueriesPage from "./pages/SavedQueriesPage";
import ConnectDatabasePage from "./pages/ConnectDatabasePage";
import SchemaViewerPage from "./pages/SchemaViewerPage";
import ProtectedRoute from "./components/layout/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ChatPage />} />
        <Route path="chat/:conversationId" element={<ChatPage />} />
        <Route path="history" element={<ChatHistoryPage />} />
        <Route path="saved-queries" element={<SavedQueriesPage />} />
        <Route path="connections" element={<ConnectDatabasePage />} />
        <Route path="schema" element={<SchemaViewerPage />} />
      </Route>

      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}
