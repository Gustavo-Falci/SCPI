import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { buscarSetores, criarSetor, buscarFuncionarios } from "../../../services/api";

export default function Setores() {
  const router = useRouter();
  const [novoSetor, setNovoSetor] = useState("");
  const [setores, setSetores] = useState<any[]>([]);
  const [funcionarios, setFuncionarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  const loadData = async () => {
    try {
      const empresaId = await SecureStore.getItemAsync("empresa_id");
      if (!empresaId) return;
      const [sets, funcs] = await Promise.all([
        buscarSetores(empresaId),
        buscarFuncionarios(empresaId),
      ]);
      setSetores(sets || []);
      setFuncionarios(funcs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleAdicionar = async () => {
    if (!novoSetor.trim()) {
      Alert.alert("Erro", "Digite o nome do setor.");
      return;
    }
    setAdding(true);
    try {
      const empresaId = await SecureStore.getItemAsync("empresa_id");
      if (!empresaId) return;
      await criarSetor(empresaId, novoSetor.trim());
      Alert.alert("Sucesso", `Setor "${novoSetor}" criado!`);
      setNovoSetor("");
      setLoading(true);
      await loadData();
    } catch (e: any) {
      Alert.alert("Erro", e.message || "Falha ao criar setor.");
    } finally {
      setAdding(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Setores</Text>
        <View style={{ width: 22 }} />
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#5B3EFF" />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.addRow}>
            <TextInput
              style={styles.rowInput}
              placeholder="Nome do novo setor..."
              placeholderTextColor="#aaa"
              value={novoSetor}
              onChangeText={setNovoSetor}
            />
            <TouchableOpacity style={styles.rowButton} onPress={handleAdicionar} disabled={adding}>
              {adding ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Ionicons name="add" size={20} color="#fff" />
              )}
            </TouchableOpacity>
          </View>

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

          {setores.length === 0 && (
            <Text style={styles.emptyText}>Nenhum setor cadastrado.</Text>
          )}

          <View style={{ height: 30 }} />
        </ScrollView>
      )}
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
  content: { padding: 20 },
  loadingContainer: { flex: 1, justifyContent: "center", alignItems: "center" },
  addRow: {
    flexDirection: "row",
    marginBottom: 16,
    gap: 10,
  },
  rowInput: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    fontSize: 14,
    borderWidth: 1,
    borderColor: "#e0e0e0",
  },
  rowButton: {
    backgroundColor: "#5B3EFF",
    width: 50,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },
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
  emptyText: { textAlign: "center", color: "#888", marginTop: 20, fontSize: 14 },
});
