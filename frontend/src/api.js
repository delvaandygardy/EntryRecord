import axios from "axios";

const api = axios.create({ baseURL: "" });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const isLoginRequest = err.config?.url?.includes("/api/auth/login");
    const alreadyOnLogin = window.location.pathname === "/login";
    if (err.response?.status === 401 && !isLoginRequest && !alreadyOnLogin) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;
