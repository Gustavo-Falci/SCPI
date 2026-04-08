import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { buscarHistorico } from "../../services/api";

const tipoLabel: Record<string, string> = {
  entrada: "Entrada",
  intervalo_inicio: "Saída Almoço",
  intervalo_fim: "Retorno Almoço",
  saida: "Saída",
};

const tipoIcone: Record<string, any> = {
  entrada: "log-in-outline",
  intervalo_inicio: "restaurant-outline",
  intervalo_fim: "refresh-outline",
  saida: "log-out-outline",
};

const tipoCor: Record<string, string> = {
  entrada: "#22C55E",
  intervalo_inicio: "#F59E0B",
  intervalo_fim: "#6366F1",
  saida: "#EF4444",
};

export default function HistoricoFuncionario() {
  const router = useRouter();
  const [registros, setRegistros] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistorico = async () => {
      try {
        const funcionarioId = await SecureStore.getItemAsync("funcionario_id");
        if (!funcionarioId) {
          setLoading(false);
          return;
        }
        const data = await buscarHistorico(funcionarioId);
        setRegistros(data || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    loadHistorico();
  }, []);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Histórico de Ponto</Text>
        <View style={{ width: 22 }} />
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#5B3EFF" />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {registros.length === 0 ? (
            <Text style={styles.emptyText}>Nenhum registro encontrado.</Text>
          ) : (
            registros.map((r, i) => (
              <View key={r.registro_id || i} style={styles.card}>
                <View style={[styles.iconCircle, { backgroundColor: (tipoCor[r.tipo] || "#888") + "20" }]}>
                  <Ionicons name={tipoIcone[r.tipo] || "time-outline"} size={22} color={tipoCor[r.tipo] || "#888"} />
                </View>
                <View style={styles.cardInfo}>
                  <Text style={styles.cardTipo}>{tipoLabel[r.tipo] || r.tipo}</Text>
                  <Text style={styles.cardData}>{formatDate(r.data)}</Text>
                </View>
                <Text style={styles.cardHora}>{String(r.hora).slice(0, 5)}</Text>
              </View>
            ))
          )}
          <View style={{ height: 80 }} />
        </ScrollView>
      )}

      <View style={styles.bottomMenu}>
        <TouchableOpacity onPress={() => router.push("/funcionario/home")}>
          <Ionicons name="home-outline" size={24} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity>
          <Ionicons name="time" size={24} color="#5B3EFF" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/funcionario/ponto-facial")}>
          <Ionicons name="scan-outline" size={24} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/funcionario/perfil")}>
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
    paddingBottom: 22,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  content: { padding: 20 },
  loadingContainer: { flex: 1, justifyContent: "center", alignItems: "center" },
  emptyText: { textAlign: "center", color: "#888", marginTop: 40, fontSize: 14 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: "center",
    alignItems: "center",
  },
  cardInfo: { flex: 1, marginLeft: 14 },
  cardTipo: { fontSize: 14, fontWeight: "600", color: "#333" },
  cardData: { fontSize: 12, color: "#888", marginTop: 2 },
  cardHora: { fontSize: 16, fontWeight: "700", color: "#333" },
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
