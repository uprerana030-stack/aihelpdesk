import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import EmployeePage from './pages/EmployeePage';
import AgentPage from './pages/AgentPage';
import ManagerPage from './pages/ManagerPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import DatabasePage from './pages/DatabasePage';
import EscalationsPage from './pages/EscalationsPage';
import {
  AGENT_ROLES,
  KB_WRITER_ROLES,
  MANAGER_ROLES,
  homePathForRole,
  useUser,
} from './context/UserContext';

// Roles allowed to view the Knowledge Base — everyone except plain employees.
const KB_ROLES = new Set([...AGENT_ROLES, ...MANAGER_ROLES, ...KB_WRITER_ROLES]);

// The manual team (agents + managers) may view the Escalations dashboard.
const MANUAL_TEAM_ROLES = new Set([...AGENT_ROLES, ...MANAGER_ROLES]);

function RequireUser({ children }) {
  const { user } = useUser();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// Redirects a plain employee away from the Knowledge Base to their home.
function RequireKbAccess({ children }) {
  const { role } = useUser();
  if (!KB_ROLES.has(role)) return <Navigate to={homePathForRole(role)} replace />;
  return <>{children}</>;
}

// Restricts the Escalations dashboard to the manual team (agents + managers).
function RequireManualTeam({ children }) {
  const { role } = useUser();
  if (!MANUAL_TEAM_ROLES.has(role)) return <Navigate to={homePathForRole(role)} replace />;
  return <>{children}</>;
}

export default function App() {
  const { user, role } = useUser();

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to={homePathForRole(role)} replace /> : <LoginPage />}
      />
      <Route
        element={
          <RequireUser>
            <Layout />
          </RequireUser>
        }
      >
        <Route index element={<Navigate to={homePathForRole(role)} replace />} />
        <Route path="/employee" element={<EmployeePage />} />
        <Route path="/agent" element={<AgentPage />} />
        <Route path="/manager" element={<ManagerPage />} />
        <Route path="/database" element={<DatabasePage />} />
        <Route
          path="/escalations"
          element={
            <RequireManualTeam>
              <EscalationsPage />
            </RequireManualTeam>
          }
        />
        <Route
          path="/kb"
          element={
            <RequireKbAccess>
              <KnowledgeBasePage />
            </RequireKbAccess>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
