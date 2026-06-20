import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import toast from "react-hot-toast";

export default function Login() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  if (localStorage.getItem("token")) { nav("/"); return null; }

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/api/auth/login", form);
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      nav("/");
    } catch {
      toast.error("Identifiants incorrects");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>🏨 Système d'Accès</h1>
        <p>Enregistrement Automatique</p>
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Nom d'utilisateur</label>
            <input className="form-control" value={form.username} autoFocus
              onChange={e => setForm({ ...form, username: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Mot de passe</label>
            <input className="form-control" type="password" value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })} />
          </div>
          <button className="btn btn-primary" style={{ width: "100%", marginTop: 8 }}
            disabled={loading}>
            {loading ? "Connexion…" : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
