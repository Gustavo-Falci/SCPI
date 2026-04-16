import React, { useState, useEffect } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  Alert,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";

import { apiGet, apiPost } from "../../services/api";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function ListaPresenca() {
  const { turma_id, turma_nome } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [statusChamada, setStatusChamada] = useState<any>(null);
  const [alunos, setAlunos] = useState<any[]>([]);

  const carregarStatus = async () => {
    try {
      if (!turma_id) return;
      const statusResp = await apiGet(`/chamadas/status/${turma_id}`);
      setStatusChamada(statusResp);

      if (statusResp.status === "Aberta") {
         try {
             const listResp = await apiGet(`/chamadas/${statusResp.chamada_id}/alunos`);
             if(listResp && listResp.alunos) setAlunos(listResp.alunos);
         } catch(e) { console.log("Erro ao buscar alunos", e); }
      }
    } catch (err: any) {
      console.error("Erro ao carregar status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarStatus();
    const intervalId = setInterval(carregarStatus, 3000);
    return () => clearInterval(intervalId);
  }, [turma_id]);

  const fecharChamada = async () => {
    try {
        await apiPost(`/chamadas/fechar/${turma_id}`, {});
        Alert.alert("Sucesso", "Chamada encerrada e salva no histórico!");
        router.back();
    } catch(err: any) {
        Alert.alert("Erro", err.message || "Erro ao fechar chamada");
    }
  }

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/professor/home' },
    { icon: 'clipboard-outline', activeIcon: 'clipboard', route: '/professor/turmas' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/professor/horarios-turmas' },
    { icon: 'person-outline', activeIcon: 'person', route: '/professor/perfil' },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Chamada em Tempo Real</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.statusCard}>
          <View style={styles.statusHeader}>
            <View>
              <Text style={styles.classTitle}>{turma_nome || "Turma"}</Text>
              <View style={styles.badgeRow}>
                <View style={[styles.statusBadge, statusChamada?.status === "Aberta" ? styles.badgeOpen : styles.badgeClosed]}>
                  <Text style={styles.badgeText}>{statusChamada?.status || 'Aguardando'}</Text>
                </View>
              </View>
            </View>
            <Ionicons name="radio-outline" size={32} color={statusChamada?.status === "Aberta" ? "#22C55E" : Colors.brand.textSecondary} />
          </View>

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{statusChamada?.total_alunos || 0}</Text>
              <Text style={styles.statLabel}>Total</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>{statusChamada?.presentes || 0}</Text>
              <Text style={styles.statLabel}>Presentes</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: Colors.brand.error }]}>{statusChamada?.ausentes || 0}</Text>
              <Text style={styles.statLabel}>Ausentes</Text>
            </View>
          </View>

          {statusChamada?.status === "Aberta" && (
            <TouchableOpacity style={styles.closeCallBtn} onPress={fecharChamada}>
              <Text style={styles.closeCallText}>Encerrar e Salvar Chamada</Text>
            </TouchableOpacity>
          )}
        </View>

        <Text style={styles.sectionTitle}>Lista de Alunos</Text>

        {loading ? (
          <ActivityIndicator size="large" color={Colors.brand.primary} style={{ marginTop: 20 }} />
        ) : alunos.length > 0 ? (
          alunos.map((aluno) => (
            <View style={styles.studentCard} key={aluno.id}>
              <View style={styles.studentInfo}>
                <View style={[styles.avatar, { backgroundColor: aluno.presente ? 'rgba(34, 197, 94, 0.1)' : 'rgba(255, 75, 75, 0.1)' }]}>
                  <Text style={[styles.avatarText, { color: aluno.presente ? '#22C55E' : Colors.brand.error }]}>
                    {aluno.nome.charAt(0)}
                  </Text>
                </View>
                <Text style={styles.studentName}>{aluno.nome}</Text>
              </View>

              <View style={[styles.statusTag, aluno.presente ? styles.tagPresent : styles.tagAbsent]}>
                <Ionicons name={aluno.presente ? "checkmark-circle" : "close-circle"} size={14} color="#fff" />
                <Text style={styles.tagText}>{aluno.presente ? "Presente" : "Ausente"}</Text>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={40} color={Colors.brand.textSecondary} />
            <Text style={styles.emptyText}>
              {statusChamada?.status === "Aberta" ? "Nenhum aluno identificado ainda..." : "Aguardando início da chamada."}
            </Text>
          </View>
        )}

        <View style={{ height: 120 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, height: 60 },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff" },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.brand.card, justifyContent: "center", alignItems: "center" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 10 },
  statusCard: {
    backgroundColor: Colors.brand.card, borderRadius: 24, padding: 24, marginBottom: 32,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  statusHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  classTitle: { color: "#fff", fontSize: 20, fontWeight: "800" },
  badgeRow: { flexDirection: "row", marginTop: 8 },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  badgeOpen: { backgroundColor: "rgba(34, 197, 94, 0.15)" },
  badgeClosed: { backgroundColor: "rgba(255, 255, 255, 0.05)" },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  statsRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 20 },
  statBox: { alignItems: "center", flex: 1 },
  statValue: { color: "#fff", fontSize: 24, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 4 },
  closeCallBtn: { backgroundColor: Colors.brand.error, height: 50, borderRadius: 14, justifyContent: "center", alignItems: "center" },
  closeCallText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  sectionTitle: { color: "#fff", fontSize: 18, fontWeight: "700", marginBottom: 16, marginLeft: 4 },
  studentCard: {
    backgroundColor: Colors.brand.card, borderRadius: 20, padding: 12, marginBottom: 12,
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  studentInfo: { flexDirection: "row", alignItems: "center", flex: 1 },
  avatar: { width: 40, height: 40, borderRadius: 20, justifyContent: "center", alignItems: "center", marginRight: 12 },
  avatarText: { fontWeight: "800", fontSize: 16 },
  studentName: { color: "#fff", fontSize: 15, fontWeight: "600" },
  statusTag: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  tagPresent: { backgroundColor: "#22C55E" },
  tagAbsent: { backgroundColor: Colors.brand.error },
  tagText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  emptyContainer: { alignItems: "center", paddingVertical: 40 },
  emptyText: { color: Colors.brand.textSecondary, textAlign: "center", fontSize: 14, marginTop: 12 },
});
