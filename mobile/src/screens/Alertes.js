import { useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet, TouchableOpacity, RefreshControl, Alert } from "react-native";
import api from "../services/api";

export default function Alertes() {
  const [alertes, setAlertes]     = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = () => api.get("/api/alertes?traitee=false&limit=50").then(r => setAlertes(r.data)).catch(() => {});

  useEffect(() => { load(); }, []);

  const traiter = async (id) => {
    Alert.alert("Traiter", "Marquer cette alerte comme traitée ?", [
      { text: "Annuler", style: "cancel" },
      { text: "Confirmer", onPress: async () => {
        await api.patch(`/api/alertes/${id}`, { traitee: true });
        load();
      }},
    ]);
  };

  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false); };

  const sevColor = (s) => s === "CRITIQUE" ? "#f85149" : s === "HAUTE" ? "#d29922" : "#8b949e";

  return (
    <View style={s.container}>
      <Text style={s.header}>{alertes.length} alerte(s) active(s)</Text>
      <FlatList data={alertes} keyExtractor={i => String(i.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text style={s.empty}>✅ Aucune alerte active</Text>}
        renderItem={({ item }) => (
          <View style={[s.card, { borderLeftColor: sevColor(item.severite) }]}>
            <View style={{ flex:1 }}>
              <Text style={[s.type, { color: sevColor(item.severite) }]}>{item.type}</Text>
              <Text style={s.msg} numberOfLines={2}>{item.message || "—"}</Text>
              <Text style={s.time}>{item.timestamp?.slice(0,16)}</Text>
            </View>
            <TouchableOpacity style={s.btn} onPress={() => traiter(item.id)}>
              <Text style={s.btnText}>✓</Text>
            </TouchableOpacity>
          </View>
        )} />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:"#0f1117", padding:12 },
  header:    { fontSize:14, color:"#8b949e", marginBottom:12 },
  card:      { backgroundColor:"#161b22", borderRadius:8, padding:12, marginBottom:8, borderLeftWidth:3, flexDirection:"row", alignItems:"center", gap:12 },
  type:      { fontSize:12, fontWeight:"700", marginBottom:4 },
  msg:       { fontSize:13, color:"#c9d1d9" },
  time:      { fontSize:11, color:"#8b949e", marginTop:4 },
  btn:       { backgroundColor:"#3fb95022", borderWidth:1, borderColor:"#3fb95044", borderRadius:6, padding:8 },
  btnText:   { color:"#3fb950", fontWeight:"700" },
  empty:     { textAlign:"center", color:"#3fb950", marginTop:40, fontSize:16 },
});
