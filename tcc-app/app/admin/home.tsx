import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
} from "react-native";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import * as SecureStore from "expo-secure-store";
import { buscarFuncionarios, buscarSetores, buscarEmpresa } from "../../services/api";

type TabType = "funcionarios" | "setores" | "empresa";

export default function AdminHome() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>("funcionarios");
  const [search, setSearch] = useState("");
  const [funcionarios, setFuncionarios] = useState<any[]>([]);
  const [setores, setSetores] = useState<any[]>([]);
  const [empresa, setEmpresa] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const empresaId = await SecureStore.getItemAsync("empresa_id");
      if (!empresaId) return;
      const [funcs, sets, emp] = await Promise.all([
        buscarFuncionarios(empresaId),
        buscarSetores(empresaId),
        buscarEmpresa(empresaId),
      ]);
      setFuncionarios(funcs || []);
      setSetores(sets || []);
      setEmpresa(emp);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(useCallback(() => { loadData(); }, []));

  const tabs: { key: TabType; label: string; icon: any }[] = [
    { key: "funcionarios", label: "Funcionários", icon: "people-outline" },
    { key: "setores", label: "Setores", icon: "business-outline" },
    { key: "empresa", label: "Empresa", icon: "business-outline" },
  ];

  const renderFuncionarios = () => (
    <>
      <TouchableOpacity
        style={styles.addButton}
        onPress={() => router.push("/admin/funcionarios")}
      >
        <Ionicons name="add" size={18} color="#fff" />
        <Text style={styles.addButtonText}>Novo Funcionário</Text>
      </TouchableOpacity>

      <View style={styles.searchBox}>
        <Ionicons name="search-outline" size={18} color="#9CA3AF" />
        <TextInput
          placeholder="Buscar funcionário..."
          placeholderTextColor="#9CA3AF"
          style={styles.searchInput}
          value={search}
          onChangeText={setSearch}
        />
      </View>

      {funcionarios
        .filter((f) => f.nome.toLowerCase().includes(search.toLowerCase()))
        .map((f) => (
          <View key={f.funcionario_id} style={styles.card}>
            <View style={styles.avatarSmall}>
              <Ionicons name="person" size={22} color="#5B3EFF" />
            </View>
            <View style={styles.cardInfo}>
              <Text style={styles.cardTitle}>{f.nome}</Text>
              <Text style={styles.cardSubtitle}>
                {f.cargo || "Sem cargo"} • {f.setor || "Sem setor"}
              </Text>
            </View>
            <TouchableOpacity style={styles.cardAction}>
              <Ionicons name="ellipsis-vertical" size={18} color="#888" />
            </TouchableOpacity>
          </View>
        ))}

      {funcionarios.length === 0 && !loading && (
        <Text style={styles.emptyText}>Nenhum funcionário cadastrado.</Text>
      )}
    </>
  );

  const renderSetores = () => (
    <>
      <TouchableOpacity
        style={styles.addButton}
        onPress={() => router.push("/admin/setores")}
      >
        <Ionicons name="add" size={18} color="#fff" />
        <Text style={styles.addButtonText}>Novo Setor</Text>
      </TouchableOpacity>

      {setores.map((s) => (
        <View key={s.setor_id} style={styles.card}>
          <View style={styles.avatarSmall}>
            <Ionicons name="business" size={22} color="#5B3EFF" />
          </View>
          <View style={styles.cardInfo}>
            <Text style={styles.cardTitle}>{s.nome}</Text>
            <Text style={styles.cardSubtitle}>
              {funcionarios.filter((f) => f.setor === s.nome).length} funcionário(s)
            </Text>
          </View>
        </View>
      ))}

      {setores.length === 0 && !loading && (
        <Text style={styles.emptyText}>Nenhum setor cadastrado.</Text>
      )}
    </>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Painel Admin</Text>
        <TouchableOpacity onPress={() => router.push("/admin/relatorios")}>
          <Ionicons name="stats-chart-outline" size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      <View style={styles.tabBar}>
        {tabs.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Ionicons
              name={tab.icon}
              size={18}
              color={activeTab === tab.key ? "#5B3EFF" : "#888"}
            />
            <Text
              style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#5B3EFF" />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {activeTab === "funcionarios" && renderFuncionarios()}
          {activeTab === "setores" && renderSetores()}
          {activeTab === "empresa" && empresa && (
            <View style={styles.empresaCard}>
              <MaterialCommunityIcons name="domain" size={40} color="#5B3EFF" />
              <Text style={styles.empresaNome}>{empresa.nome}</Text>
              <Text style={styles.empresaCnpj}>CNPJ: {empresa.cnpj}</Text>
              <Text style={styles.empresaPlano}>Plano: {empresa.plano}</Text>
            </View>
          )}
          <View style={{ height: 90 }} />
        </ScrollView>
      )}

      <View style={styles.bottomMenu}>
        <TouchableOpacity>
          <Ionicons name="home" size={24} color="#5B3EFF" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/admin/relatorios")}>
          <Ionicons name="stats-chart-outline" size={24} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setActiveTab("funcionarios")}>
          <Ionicons name="people-outline" size={24} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/admin/perfil")}>
          <Ionicons name="person-outline" size={24} color="#aaa" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F5F5F5" },
  header: {
    backgroundColor: "#5B3EFF",
    paddingTop: 55,
    paddingBottom: 16,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTitle: { color: "#fff", fontSize: 20, fontWeight: "700" },
  tabBar: {
    flexDirection: "row",
    backgroundColor: "#fff",
    paddingHorizontal: 10,
    paddingTop: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#eee",
  },
  tab: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabActive: { borderBottomColor: "#5B3EFF" },
  tabText: { marginLeft: 6, fontSize: 13, color: "#888", fontWeight: "500" },
  tabTextActive: { color: "#5B3EFF", fontWeight: "600" },
  content: { padding: 16 },
  loadingContainer: { flex: 1, justifyContent: "center", alignItems: "center" },
  addButton: {
    backgroundColor: "#5B3EFF",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    padding: 12,
    borderRadius: 12,
    marginBottom: 12,
  },
  addButtonText: { color: "#fff", marginLeft: 6, fontWeight: "600", fontSize: 14 },
  searchBox: {
    backgroundColor: "#fff",
    borderRadius: 12,
    height: 44,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    marginBottom: 12,
  },
  searchInput: { marginLeft: 8, flex: 1, fontSize: 14, color: "#333" },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  avatarSmall: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#EEF0FF",
    justifyContent: "center",
    alignItems: "center",
  },
  cardInfo: { flex: 1, marginLeft: 12 },
  cardTitle: { fontSize: 14, fontWeight: "600", color: "#333" },
  cardSubtitle: { fontSize: 12, color: "#888", marginTop: 2 },
  cardAction: { padding: 4 },
  emptyText: { textAlign: "center", color: "#888", marginTop: 20, fontSize: 14 },
  empresaCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
  },
  empresaNome: { fontSize: 18, fontWeight: "700", color: "#333", marginTop: 12 },
  empresaCnpj: { fontSize: 14, color: "#888", marginTop: 4 },
  empresaPlano: {
    fontSize: 13,
    color: "#5B3EFF",
    marginTop: 4,
    fontWeight: "500",
    backgroundColor: "#EEF0FF",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  bottomMenu: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    height: 70,
    backgroundColor: "#fff",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: "#eee",
  },
});
