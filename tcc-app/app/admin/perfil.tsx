import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { buscarPerfilUsuario, buscarEmpresa } from "../../services/api";

export default function PerfilAdmin() {
  const router = useRouter();
  const [perfil, setPerfil] = useState<any>(null);
  const [empresa, setEmpresa] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const empresaId = await SecureStore.getItemAsync("empresa_id");
        const [perfilData, empresaData] = await Promise.all([
          buscarPerfilUsuario(),
          empresaId ? buscarEmpresa(empresaId) : null,
        ]);
        setPerfil(perfilData);
        setEmpresa(empresaData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync("access_token");
    await SecureStore.deleteItemAsync("user_role");
    await SecureStore.deleteItemAsync("usuario_id");
    await SecureStore.deleteItemAsync("empresa_id");
    router.replace("/auth/login");
  };

  const confirmLogout = () => {
    Alert.alert("Sair", "Deseja realmente sair?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Sair", onPress: handleLogout, style: "destructive" },
    ]);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Perfil</Text>
        <View style={{ width: 22 }} />
      </View>

      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator size="large" color="#5B3EFF" />
        ) : (
          <>
            <View style={styles.avatarContainer}>
              <Ionicons name="person-circle" size={80} color="#5B3EFF" />
            </View>
            <Text style={styles.nome}>{perfil?.nome || "Administrador"}</Text>
            <Text style={styles.email}>{perfil?.email || ""}</Text>
            <View style={styles.roleBadge}>
              <Text style={styles.roleBadgeText}>Admin</Text>
            </View>

            {empresa && (
              <View style={styles.empresaCard}>
                <Text style={styles.empresaNome}>{empresa.nome}</Text>
                <Text style={styles.empresaCnpj}>CNPJ: {empresa.cnpj}</Text>
                <Text style={styles.empresaPlano}>Plano: {empresa.plano}</Text>
              </View>
            )}

            <View style={styles.divider} />

            <TouchableOpacity style={styles.menuItem}>
              <Ionicons name="settings-outline" size={22} color="#333" />
              <Text style={styles.menuText}>Configurações</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.menuItem}>
              <Ionicons name="help-circle-outline" size={22} color="#333" />
              <Text style={styles.menuText}>Ajuda</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.logoutButton} onPress={confirmLogout}>
              <Ionicons name="log-out-outline" size={22} color="#EF4444" />
              <Text style={styles.logoutText}>Sair da conta</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F5F5F5" },
  header: {
    backgroundColor: "#5B3EFF",
    paddingTop: 55,
    paddingBottom: 22,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  content: { padding: 20, alignItems: "center" },
  avatarContainer: { marginBottom: 10 },
  nome: { fontSize: 22, fontWeight: "700", color: "#333" },
  email: { fontSize: 14, color: "#888", marginTop: 2 },
  roleBadge: {
    marginTop: 8,
    backgroundColor: "#EEF0FF",
    paddingHorizontal: 14,
    paddingVertical: 4,
    borderRadius: 12,
  },
  roleBadgeText: { color: "#5B3EFF", fontWeight: "600", fontSize: 13 },
  empresaCard: {
    marginTop: 16,
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    width: "100%",
    alignItems: "center",
  },
  empresaNome: { fontSize: 16, fontWeight: "700", color: "#333" },
  empresaCnpj: { fontSize: 13, color: "#888", marginTop: 4 },
  empresaPlano: { fontSize: 13, color: "#5B3EFF", marginTop: 4, fontWeight: "500" },
  divider: { height: 1, backgroundColor: "#ddd", width: "100%", marginVertical: 20 },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    width: "100%",
    padding: 14,
    backgroundColor: "#fff",
    borderRadius: 12,
    marginBottom: 8,
  },
  menuText: { fontSize: 15, color: "#333", marginLeft: 12 },
  logoutButton: {
    flexDirection: "row",
    alignItems: "center",
    width: "100%",
    padding: 14,
    backgroundColor: "#fff",
    borderRadius: 12,
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#EF4444",
  },
  logoutText: { fontSize: 15, color: "#EF4444", marginLeft: 12, fontWeight: "600" },
});
