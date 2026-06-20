import { useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet, TextInput, TouchableOpacity, RefreshControl } from "react-native";
import api from "../services/api";

export default function Vehicules() {
  const [rows, setRows]           = useState([]);
  const [q, setQ]                 = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = () => api.get(`/api/vehicules?q=${q}&limit=100`).then(r => setRows(r.data)).catch(() => {});

  useEffect(() => { load(); }, [q]);

  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false); };

  return (
    <View style={s.container}>
      <TextInput style={s.search} placeholder="Rechercher plaque…" placeholderTextColor="#8b949e"
        value={q} onChangeText={setQ} />
      <FlatList data={rows} keyExtractor={i => String(i.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text style={s.empty}>Aucun véhicule</Text>}
        renderItem={({ item }) => (
          <View style={s.row}>
            <View style={s.plate}><Text style={s.plateText}>{item.plaque}</Text></View>
            <View style={{ flex:1 }}>
              <Text style={s.entry}>{item.point_entree}</Text>
              <Text style={s.time}>{item.timestamp?.slice(0,16)}</Text>
            </View>
            {item.confidence && (
              <Text style={s.conf}>{(item.confidence*100).toFixed(0)}%</Text>
            )}
          </View>
        )} />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:"#0f1117" },
  search:    { margin:12, padding:10, backgroundColor:"#161b22", borderWidth:1, borderColor:"#30363d", borderRadius:8, color:"#c9d1d9" },
  row:       { flexDirection:"row", alignItems:"center", padding:12, borderBottomWidth:1, borderBottomColor:"#21262d", gap:12 },
  plate:     { backgroundColor:"#1a3a6b", paddingHorizontal:10, paddingVertical:5, borderRadius:6 },
  plateText: { color:"#58a6ff", fontWeight:"700", fontFamily:"monospace" },
  entry:     { color:"#c9d1d9", fontSize:13 },
  time:      { color:"#8b949e", fontSize:11, marginTop:2 },
  conf:      { color:"#3fb950", fontSize:12, fontWeight:"600" },
  empty:     { textAlign:"center", color:"#8b949e", marginTop:40 },
});
