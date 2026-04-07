import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { buscarRegistrosDia, buscarFuncionarios } from "../../services/api";

export default function Relatorios() {
  const router = useRouter();
  const [registros, setRegistros] = useState<any[]>([]);
  const [totalFuncionarios, setTotalFuncionarios] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const empresaId = await SecureStore.getItemAsync("empresa_id");
        if (!empresaId) return;
        const [regs, funcs] = await Promise.all([
          buscarRegistrosDia(empresaId),
          buscarFuncionarios(empresaId),
        ]);
        setRegistros(regs || []);
        setTotalFuncionarios(funcs?.length || 0);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const presentes = new Set(registros.filter((r) => r.tipo === "entrada").map((r) => r.funcionario)).size;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Relatórios</Text>
        <View style={{ width: 22 }} />
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#5B3EFF" />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.summaryCard}>
            <Text style={styles.monthTitle}>Hoje</Text>
            <View style={styles.summaryRow}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryNumber}>{totalFuncionarios}</Text>
                <Text style={styles.summaryLabel}>Funcionários</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryNumber, { color: "#22C55E" }]}>{presentes}</Text>
                <Text style={styles.summaryLabel}>Presentes</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryNumber, { color: "#EF4444" }]}>
                  {totalFuncionarios - presentes}
                </Text>
                <Text style={styles.summaryLabel}>Ausentes</Text>
              </View>
            </View>
          </View>

          <Text style={styles.sectionTitle}>Registros de Hoje</Text>
          {registros.length === 0 ? (
            <Text style={styles.emptyText}>Nenhum registro hoje.</Text>
          ) : (
            registros.map((r, i) => (
              <View key={r.registro_id || i} style={styles.regCard}>
                <View style={styles.regInfo}>
                  <Text style={styles.regNome}>{r.funcionario}</Text>
                  <Text style={styles.regTipo}>{r.tipo} • {r.setor || "Sem setor"}</Text>
                </View>
                <Text style={styles.regHora}>{String(r.hora).slice(0, 5)}</Text>
              </View>
            ))
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
  summaryCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  monthTitle: { fontSize: 16, fontWeight: "700", color: "#333", marginBottom: 14 },
  summaryRow: { flexDirection: "row", justifyContent: "space-around" },
  summaryItem: { alignItems: "center" },
  summaryNumber: { fontSize: 22, fontWeight: "700", color: "#333" },
  summaryLabel: { fontSize: 11, color: "#888", marginTop: 2 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#333", marginBottom: 10 },
  emptyText: { textAlign: "center", color: "#888", marginTop: 20 },
  regCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  regInfo: { flex: 1 },
  regNome: { fontSize: 14, fontWeight: "600", color: "#333" },
  regTipo: { fontSize: 12, color: "#888", marginTop: 2 },
  regHora: { fontSize: 16, fontWeight: "700", color: "#333" },
});
