import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

// Change to your server IP for physical device
const BASE_URL = "http://192.168.1.100:8000";

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use(async (cfg) => {
  const token = await AsyncStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export const login = async (username, password) => {
  const { data } = await api.post("/api/auth/login", { username, password });
  await AsyncStorage.setItem("token", data.access_token);
  await AsyncStorage.setItem("user", JSON.stringify(data.user));
  return data;
};

export const logout = async () => {
  await AsyncStorage.removeItem("token");
  await AsyncStorage.removeItem("user");
};

export default api;
