import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from "react-native";
import { login } from "../services/api";

export default function Login({ navigation }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);

  const submit = async () => {
    setLoading(true);
    try {
      await login(username, password);
      navigation.replace("Home");
    } catch {
      Alert.alert("Erreur", "Identifiants incorrects");
    } finally { setLoading(false); }
  };

  return (
    <View style={s.container}>
      <Text style={s.title}>🏨 Système d'Accès</Text>
      <Text style={s.sub}>Enregistrement Automatique</Text>
      <TextInput style={s.input} placeholder="Nom d'utilisateur"
        placeholderTextColor="#8b949e" value={username}
        onChangeText={setUsername} autoCapitalize="none" />
      <TextInput style={s.input} placeholder="Mot de passe"
        placeholderTextColor="#8b949e" value={password}
        onChangeText={setPassword} secureTextEntry />
      <TouchableOpacity style={s.btn} onPress={submit} disabled={loading}>
        <Text style={s.btnText}>{loading ? "Connexion…" : "Se connecter"}</Text>
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:"#0f1117", justifyContent:"center", padding:32 },
  title:  { fontSize:24, fontWeight:"700", color:"#c9d1d9", textAlign:"center", marginBottom:4 },
  sub:    { fontSize:13, color:"#8b949e", textAlign:"center", marginBottom:32 },
  input:  { backgroundColor:"#161b22", borderWidth:1, borderColor:"#30363d", borderRadius:8, padding:12, color:"#c9d1d9", marginBottom:12, fontSize:14 },
  btn:    { backgroundColor:"#1a73e8", borderRadius:8, padding:14, alignItems:"center", marginTop:8 },
  btnText:{ color:"white", fontWeight:"600", fontSize:15 },
});
