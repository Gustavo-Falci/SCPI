import React, { useState, useEffect, useRef } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  StatusBar,
  Animated,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";

import { apiGet, apiPost } from "../../services/api";
import { useErrorToast } from "../../hooks/useErrorToast";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function ListaPresenca() {
  const { turma_id, turma_nome } = useLocalSearchParams();
  const router = useRouter();
  const { showError } = useErrorToast();

  const [loading, setLoading] = useState(true);
  const [statusChamada, setStatusChamada] = useState<any>(null);
  const [alunos, setAlunos] = useState<any[]>([]);

  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  const carregarStatus = async () => {
    try {
      if (!turma_id) return;
      const statusResp = await apiGet(`/chamadas/status/${turma_id}`);
      setStatusChamada(statusResp);

      if (statusResp.status === "Aberta") {
        try {
          const listResp = await apiGet(`/chamadas/${statusResp.chamada_id}/alunos`);
          if (listResp && listResp.alunos) setAlunos(listResp.alunos);
        } catch (e) {
          console.log("Erro ao buscar alunos", e);
        }
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

  const [encerrandoChamada, setEncerrandoChamada] = useState(false);

  const encerrarERevisar = async () => {
    if (!statusChamada?.chamada_id || encerrandoChamada) return;
    try {
      setEncerrandoChamada(true);
      await apiPost(`/chamadas/fechar/${turma_id}`, {});
      router.push({
        pathname: "/professor/revisar-chamada",
        params: {
          chamada_id: String(statusChamada.chamada_id),
          turma_id: String(turma_id),
          turma_nome: String(turma_nome),
        },
      });
    } catch (err: any) {
      showError(err, "Erro ao encerrar chamada");
    } finally {
      setEncerrandoChamada(false);
    }
  };

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/professor/home', label: 'Início' },
    { icon: 'clipboard-outline', activeIcon: 'clipboard', route: '/professor/turmas', label: 'Turmas' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/professor/horarios-turmas', label: 'Agenda' },
    { icon: 'person-outline', activeIcon: 'person', route: '/professor/perfil', label: 'Perfil' },
  ];

  const isAberta = statusChamada?.status === "Aberta";

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />

      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>Chamada em Tempo Real</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.statusCard}>
          <View style={styles.statusHeader}>
            <View style={styles.statusHeaderLeft}>
              <Text style={styles.classTitle} numberOfLines={2}>{turma_nome || "Turma"}</Text>
              <View style={styles.badgeRow}>
                {isAberta ? (
                  <View style={[styles.statusBadge, styles.badgeOpen]}>
                    <Animated.View style={[styles.liveDot, { opacity: pulseAnim }]} />
                    <Text style={styles.badgeText}>Ao Vivo</Text>
                  </View>
                ) : (
                  <View style={[styles.statusBadge, styles.badgeClosed]}>
                    <Text style={styles.badgeText}>{statusChamada?.status || 'Aguardando'}</Text>
                  </View>
                )}
              </View>
            </View>
            <Ionicons
              name="radio-outline"
              size={32}
              color={isAberta ? "#22C55E" : Colors.brand.textSecondary}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{statusChamada?.total_alunos || 0}</Text>
              <Text style={styles.statLabel}>Total</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>{statusChamada?.presentes || 0}</Text>
              <Text style={styles.statLabel}>Presentes</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: Colors.brand.error }]}>{statusChamada?.ausentes || 0}</Text>
              <Text style={styles.statLabel}>Ausentes</Text>
            </View>
          </View>

          {isAberta && (
            <TouchableOpacity
              style={[styles.closeCallBtn, encerrandoChamada && { opacity: 0.75 }]}
              onPress={encerrarERevisar}
              activeOpacity={0.8}
              disabled={encerrandoChamada}
              accessibilityRole="button"
              accessibilityLabel="Encerrar chamada"
            >
              {encerrandoChamada ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Ionicons name="stop-circle-outline" size={20} color="#fff" />
                  <Text style={styles.closeCallText}>Encerrar Chamada</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Lista de Alunos</Text>
          {alunos.length > 0 && (
            <Text style={styles.sectionCount}>{alunos.length} aluno{alunos.length !== 1 ? 's' : ''}</Text>
          )}
        </View>

        {loading ? (
          <ActivityIndicator size="large" color={Colors.brand.primary} style={{ marginTop: 20 }} />
        ) : alunos.length > 0 ? (
          alunos.map((aluno) => {
            const presente = (aluno.aulas_presentes?.length ?? 0) > 0;
            return (
              <View style={styles.studentCard} key={aluno.id}>
                <View
                  style={[
                    styles.avatar,
                    { backgroundColor: presente ? 'rgba(34, 197, 94, 0.12)' : 'rgba(255, 75, 75, 0.12)' },
                  ]}
                >
                  <Text style={[styles.avatarText, { color: presente ? '#22C55E' : Colors.brand.error }]}>
                    {aluno.nome.charAt(0).toUpperCase()}
                  </Text>
                </View>

                <Text style={styles.studentName} numberOfLines={1} ellipsizeMode="tail">
                  {aluno.nome}
                </Text>

                <View style={[styles.statusTag, presente ? styles.tagPresent : styles.tagAbsent]}>
                  <Ionicons
                    name={presente ? "checkmark-circle" : "close-circle"}
                    size={13}
                    color="#fff"
                  />
                  <Text style={styles.tagText}>{presente ? "Presente" : "Ausente"}</Text>
                </View>
              </View>
            );
          })
        ) : (
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={48} color={Colors.brand.textSecondary} />
            <Text style={styles.emptyTitle}>
              {isAberta ? "Nenhum aluno identificado" : "Chamada não iniciada"}
            </Text>
            <Text style={styles.emptyText}>
              {isAberta
                ? "Os alunos aparecem aqui conforme são reconhecidos pelo sistema."
                : "Aguardando o início da chamada biométrica."}
            </Text>
          </View>
        )}

        <View style={{ height: 148 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    height: 60,
  },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff", flex: 1, textAlign: "center" },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.brand.card,
    justifyContent: "center",
    alignItems: "center",
  },

  scrollContent: { paddingHorizontal: 20, paddingTop: 12 },

  statusCard: {
    backgroundColor: Colors.brand.card,
    borderRadius: 24,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
  },
  statusHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  statusHeaderLeft: { flex: 1, marginRight: 12 },
  classTitle: { color: "#fff", fontSize: 19, fontWeight: "800", lineHeight: 24 },
  badgeRow: { flexDirection: "row", marginTop: 8 },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    alignSelf: "flex-start",
  },
  badgeOpen: { backgroundColor: "rgba(34, 197, 94, 0.15)" },
  badgeClosed: { backgroundColor: "rgba(255, 255, 255, 0.07)" },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  liveDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#22C55E",
  },

  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.06)",
    marginBottom: 16,
  },

  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  statBox: { alignItems: "center", flex: 1 },
  statValue: { color: "#fff", fontSize: 26, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 4 },
  statDivider: { width: 1, height: 36, backgroundColor: "rgba(255,255,255,0.07)" },

  closeCallBtn: {
    backgroundColor: "#F59E0B",
    height: 52,
    borderRadius: 14,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  closeCallText: { color: "#fff", fontWeight: "700", fontSize: 15 },

  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 14,
    paddingHorizontal: 4,
  },
  sectionTitle: { color: "#fff", fontSize: 17, fontWeight: "700" },
  sectionCount: {
    color: Colors.brand.textSecondary,
    fontSize: 13,
    fontWeight: "600",
  },

  studentCard: {
    backgroundColor: Colors.brand.card,
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 10,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  avatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
    flexShrink: 0,
  },
  avatarText: { fontWeight: "800", fontSize: 16 },
  studentName: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
    flex: 1,
    marginRight: 10,
  },
  statusTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    flexShrink: 0,
    minWidth: 80,
    justifyContent: "center",
  },
  tagPresent: { backgroundColor: "rgba(34, 197, 94, 0.85)" },
  tagAbsent: { backgroundColor: "rgba(255, 75, 75, 0.85)" },
  tagText: { color: "#fff", fontSize: 11, fontWeight: "700" },

  emptyContainer: { alignItems: "center", paddingVertical: 48, paddingHorizontal: 24 },
  emptyTitle: { color: "#fff", fontSize: 16, fontWeight: "700", marginTop: 14 },
  emptyText: {
    color: Colors.brand.textSecondary,
    textAlign: "center",
    fontSize: 13,
    marginTop: 6,
    lineHeight: 20,
  },
});
