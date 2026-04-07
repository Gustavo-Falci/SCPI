import React, { useEffect, useState, useCallback } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import * as SecureStore from "expo-secure-store";
import { buscarPerfilUsuario, buscarHistorico } from "../../services/api";

export default function HomeFuncionario() {
  const router = useRouter();
  const [nome, setNome] = useState("Funcionário");
  const [registrosHoje, setRegistrosHoje] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const token = await SecureStore.getItemAsync("access_token");
      if (!token) {
        router.replace("/auth/login");
        return;
      }

      const perfil = await buscarPerfilUsuario();
      setNome(perfil?.nome?.split(" ")[0] || "Funcionário");

      const funcionarioId = await SecureStore.getItemAsync("funcionario_id");
      if (funcionarioId) {
        const registros = await buscarHistorico(funcionarioId);
        const hoje = new Date().toISOString().split("T")[0];
        const regsHoje = (registros || []).filter((r: any) => {
          const regDate = String(r.data).split("T")[0];
          return regDate === hoje;
        });
        setRegistrosHoje(regsHoje);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(useCallback(() => { loadData(); }, []));

  const getHoraPorTipo = (tipo: string) => {
    const reg = registrosHoje.find((r) => r.tipo === tipo);
    return reg ? String(reg.hora).slice(0, 5) : "--:--";
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={["#5B3EFF", "#4B2FD6"]} style={styles.header}>
        <Text style={styles.headerTitle}>Olá, {nome}!</Text>
        <TouchableOpacity onPress={() => router.push("/funcionario/perfil")}>
          <Ionicons name="person-circle-outline" size={32} color="#fff" />
        </TouchableOpacity>
      </LinearGradient>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {/* CARD PONTO */}
        <TouchableOpacity
          style={styles.bigCard}
          onPress={() => router.push("/funcionario/ponto-facial")}
        >
          <LinearGradient colors={["#5B3EFF", "#4B2FD6"]} style={styles.bigCardGradient}>
            <MaterialCommunityIcons name="face-recognition" size={32} color="#fff" />
            <Text style={styles.bigCardTitle}>Bater Ponto</Text>
            <Text style={styles.bigCardSubtitle}>Reconhecimento facial</Text>
          </LinearGradient>
        </TouchableOpacity>

        {/* CARDS AÇÃO */}
        <View style={styles.row}>
          <TouchableOpacity style={styles.smallCard} onPress={() => router.push("/funcionario/historico")}>
            <Ionicons name="time-outline" size={28} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Histórico</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.smallCard} onPress={() => router.push("/funcionario/ponto-facial")}>
            <Ionicons name="log-in-outline" size={28} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Registrar</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.divider} />

        {/* RESUMO DO DIA */}
        <View style={styles.todayCard}>
          <View style={styles.todayHeader}>
            <Text style={styles.todayTitle}>Resumo de Hoje</Text>
            <Ionicons name="calendar-outline" size={18} color="#888" />
          </View>
          {loading ? (
            <ActivityIndicator color="#5B3EFF" />
          ) : (
            <>
              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Entrada</Text>
                  <Text style={styles.summaryValue}>{getHoraPorTipo("entrada")}</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Saída Almoço</Text>
                  <Text style={styles.summaryValue}>{getHoraPorTipo("intervalo_inicio")}</Text>
                </View>
              </View>
              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Retorno</Text>
                  <Text style={styles.summaryValue}>{getHoraPorTipo("intervalo_fim")}</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Saída</Text>
                  <Text style={[styles.summaryValue, getHoraPorTipo("saida") === "--:--" && { color: "#aaa" }]}>
                    {getHoraPorTipo("saida")}
                  </Text>
                </View>
              </View>
            </>
          )}
        </View>

        <View style={{ height: 90 }} />
      </ScrollView>

      {/* MENU INFERIOR */}
      <View style={styles.bottomMenu}>
        <TouchableOpacity onPress={() => router.replace("/funcionario/home")}>
          <Ionicons name="home" size={24} color="#5B3EFF" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/funcionario/historico")}>
          <Ionicons name="time-outline" size={24} color="#aaa" />
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
  container: { flex: 1, backgroundColor: "#F2F2F2" },
  header: {
    paddingTop: 60,
    paddingBottom: 24,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTitle: { color: "#fff", fontSize: 22, fontWeight: "700" },
  content: { paddingHorizontal: 20, paddingTop: 20 },
  bigCard: { borderRadius: 16, marginBottom: 22 },
  bigCardGradient: { borderRadius: 16, padding: 24, alignItems: "center" },
  bigCardTitle: { color: "#fff", fontSize: 18, fontWeight: "700", marginTop: 8 },
  bigCardSubtitle: { color: "#E0E0E0", fontSize: 13, marginTop: 4 },
  row: { flexDirection: "row", justifyContent: "space-between", marginBottom: 22 },
  smallCard: {
    width: "48%",
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 18,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  smallCardTitle: { color: "#333", fontSize: 14, fontWeight: "600", marginTop: 8 },
  divider: { height: 1, backgroundColor: "#D9D9D9", marginBottom: 22 },
  todayCard: { backgroundColor: "#fff", borderRadius: 16, padding: 18 },
  todayHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 14 },
  todayTitle: { color: "#333", fontSize: 16, fontWeight: "700" },
  summaryRow: { flexDirection: "row", marginBottom: 10 },
  summaryItem: { flex: 1 },
  summaryLabel: { color: "#888", fontSize: 12, marginBottom: 2 },
  summaryValue: { color: "#333", fontSize: 16, fontWeight: "600" },
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
