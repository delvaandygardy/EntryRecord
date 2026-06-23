import { useEffect, useState } from "react";
import api from "../api";

export function usePoints() {
  const [points, setPoints] = useState([]);
  useEffect(() => {
    api.get("/api/points_acces")
      .then(r => setPoints(Array.isArray(r.data) ? r.data.map(p => p.nom) : []))
      .catch(() => setPoints(["Principal"]));
  }, []);
  return points;
}
