import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from "react-native";
import api from "../services/api";

export default function Badge() {
  const [matricule, setMatricule] = useState("");
  const [lastBadge, setLastBadge] = useState(null);
  const [loading, setLoading]     = useState(false);

  const badge = async () => {
    if (!matricule.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.post("/api/employes/badge", {
        matricule: matricule.trim().toUpperCase(),
        point_entree: "Principal",
      });
      setLastBadge(data);
      setMatricule("");
    } catch (err) {
      Alert.alert("Erreur", err.response?.data?.detail || "Matricule introuvable");
    } finally { setLoading(false); }
  };

  const isEntree = lastBadge?.type === "ENTREE";

  return (
    <View style={s.container}>
      <Text style={s.title}>📋 Badgeage Employé</Text>
      <TextInput style={s.input} placeholder="Matricule (ex: EMP001)"
        placeholderTextColor="#8b949e" value={matricule}
        onChangeText={v => setMatricule(v.toUpperCase())}
        autoCapitalize="characters" autoFocus />
      <TouchableOpacity style={s.btn} onPress={badge} disabled={loading}>
        <Text style={s.btnText}>{loading ? "Traitement…" : "Badger"}</Text>
      </TouchableOpacity>

      {lastBadge && (
        <View style={[s.result, { borderColor: isEntree ? "#3fb950" : "#d29922" }]}>
          <Text style={[s.resultType, { color: isEntree ? "#3fb950" : "#d29922" }]}>
            {isEntree ? "✅ ENTRÉE" : "🚪 SORTIE"}
          </Text>
          <Text style={s.resultName}>
            {lastBadge.employe?.prenom} {lastBadge.employe?.nom}
          </Text>
          <Text style={s.resultMat}>{lastBadge.employe?.matricule}</Text>
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:"#0f1117", padding:24 },
  title:     { fontSize:20, fontWeight:"700", color:"#c9d1d9", marginBottom:24 },
  input:     { backgroundColor:"#161b22", borderWidth:1, borderColor:"#30363d", borderRadius:8, padding:16, color:"#c9d1d9", fontSize:20, fontFamily:"monospace", marginBottom:12, textAlign:"center" },
  btn:       { backgroundColor:"#1a73e8", borderRadius:8, padding:16, alignItems:"center" },
  btnText:   { color:"white", fontWeight:"600", fontSize:16 },
  result:    { marginTop:24, borderWidth:2, borderRadius:12, padding:20, alignItems:"center" },
  resultType:{ fontSize:24, fontWeight:"700", marginBottom:8 },
  resultName:{ fontSize:18, color:"#c9d1d9", fontWeight:"600" },
  resultMat: { fontSize:13, color:"#8b949e", marginTop:4 },
});
