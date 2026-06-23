import { Routes, Route, Navigate } from "react-router-dom";
import { Component } from "react";
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Vehicules from "./pages/Vehicules";
import Personnes from "./pages/Personnes";
import Employes from "./pages/Employes";
import Presences from "./pages/Presences";
import Blacklist from "./pages/Blacklist";
import Alertes from "./pages/Alertes";
import Reports from "./pages/Reports";
import Cameras from "./pages/Cameras";
import Admin from "./pages/Admin";
import Scanner from "./pages/Scanner";
import PointsAcces from "./pages/PointsAcces";

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(e) { return { error: e }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, color: "#f85149", fontFamily: "monospace" }}>
          <h2>Erreur de rendu</h2>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{String(this.state.error)}</pre>
          <button onClick={() => { localStorage.clear(); window.location.href = "/login"; }}
            style={{ marginTop: 16, padding: "8px 16px", cursor: "pointer" }}>
            Réinitialiser la session
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function PrivateRoute({ children }) {
  return localStorage.getItem("token") ? children : <Navigate to="/login" replace />;
}

function Layout({ children }) {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
      <Route path="/vehicules" element={<PrivateRoute><Layout><Vehicules /></Layout></PrivateRoute>} />
      <Route path="/conducteurs" element={<PrivateRoute><Layout><Personnes mode="conducteur" /></Layout></PrivateRoute>} />
      <Route path="/pietons" element={<PrivateRoute><Layout><Personnes mode="pieton" /></Layout></PrivateRoute>} />
      <Route path="/employes" element={<PrivateRoute><Layout><Employes /></Layout></PrivateRoute>} />
      <Route path="/presences" element={<PrivateRoute><Layout><Presences /></Layout></PrivateRoute>} />
      <Route path="/blacklist" element={<PrivateRoute><Layout><Blacklist /></Layout></PrivateRoute>} />
      <Route path="/alertes" element={<PrivateRoute><Layout><Alertes /></Layout></PrivateRoute>} />
      <Route path="/cameras" element={<PrivateRoute><Layout><Cameras /></Layout></PrivateRoute>} />
      <Route path="/rapports" element={<PrivateRoute><Layout><Reports /></Layout></PrivateRoute>} />
      <Route path="/admin" element={<PrivateRoute><Layout><Admin /></Layout></PrivateRoute>} />
      <Route path="/scanner" element={<PrivateRoute><Layout><Scanner /></Layout></PrivateRoute>} />
      <Route path="/points_acces" element={<PrivateRoute><Layout><PointsAcces /></Layout></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </ErrorBoundary>
  );
}
