import { useEffect, useState } from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl } from "react-native";
import api from "../services/api";

export default function Dashboard() {
  const [stats, setStats]       = useState({});
  const [alertes, setAlertes]   = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [s, a] = await Promise.all([
        api.get("/api/reports/stats"),
        api.get("/api/alertes?traitee=false&limit=5"),
      ]);
      setStats(s.data); setAlertes(a.data);
    } catch {}
  };

  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, []);

  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false); };

  const CARDS = [
    { k:"vehicules_today",   label:"Véhicules\naujourd'hui", color:"#1a3a6b" },
    { k:"pietons_today",     label:"Piétons\naujourd'hui",   color:"#4a3a0a" },
    { k:"alertes_actives",   label:"Alertes\nactives",       color:"#3a1a1a" },
    { k:"employes_actifs",   label:"Employés\nactifs",       color:"#1a4a2e" },
  ];

  return (
    <ScrollView style={s.container} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <Text style={s.title}>Tableau de Bord</Text>
      <View style={s.grid}>
        {CARDS.map(({ k, label, color }) => (
          <View key={k} style={[s.card, { backgroundColor: color }]}>
            <Text style={s.cardNum}>{stats[k] ?? "—"}</Text>
            <Text style={s.cardLbl}>{label}</Text>
          </View>
        ))}
      </View>
      {alertes.length > 0 && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>🔔 Alertes actives</Text>
          {alertes.map(a => (
            <View key={a.id} style={s.alertRow}>
              <Text style={s.alertType}>{a.type}</Text>
              <Text style={s.alertMsg} numberOfLines={1}>{a.message}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:"#0f1117", padding:16 },
  title:     { fontSize:20, fontWeight:"700", color:"#c9d1d9", marginBottom:16 },
  grid:      { flexDirection:"row", flexWrap:"wrap", gap:12, marginBottom:20 },
  card:      { width:"47%", borderRadius:10, padding:16 },
  cardNum:   { fontSize:30, fontWeight:"700", color:"white" },
  cardLbl:   { fontSize:11, color:"rgba(255,255,255,.7)", marginTop:4 },
  section:   { marginBottom:20 },
  sectionTitle: { fontSize:14, fontWeight:"600", color:"#c9d1d9", marginBottom:8 },
  alertRow:  { backgroundColor:"#1c2128", borderRadius:8, padding:12, marginBottom:6, flexDirection:"row", gap:8, alignItems:"center" },
  alertType: { fontSize:11, color:"#f85149", fontWeight:"600", minWidth:80 },
  alertMsg:  { fontSize:12, color:"#8b949e", flex:1 },
});
