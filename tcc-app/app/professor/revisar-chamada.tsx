import React, { useState, useEffect } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  StatusBar,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";

import { apiGet, apiPost } from "../../services/api";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";
import { useErrorToast } from "../../hooks/useErrorToast";

type Aluno = {
  id: string;
  nome: string;
  presente: boolean;
};

export default function RevisarChamada() {
  const { chamada_id, turma_id, turma_nome } = useLocalSearchParams();
  const router = useRouter();
  const { showError, showSuccess } = useErrorToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [alunos, setAlunos] = useState<Aluno[]>([]);

  useEffect(() => {
    carregarAlunos();
  }, [chamada_id]);

  const carregarAlunos = async () => {
    try {
      const resp = await apiGet(`/chamadas/${chamada_id}/alunos`);
      if (resp?.alunos) setAlunos(resp.alunos);
    } catch (err: any) {
      showError(err, "Erro ao carregar alunos");
    } finally {
      setLoading(false);
    }
  };

  const togglePresenca = (alunoId: string) => {
    setAlunos((prev) =>
      prev.map((a) =>
        a.id === alunoId ? { ...a, presente: !a.presente } : a
      )
    );
  };

  const presentes = alunos.filter((a) => a.presente).length;
  const ausentes = alunos.length - presentes;

  const salvar = async () => {
    if (saving) return;
    try {
      setSaving(true);
      await apiPost(`/chamadas/${chamada_id}/ajustar`, {
        alunos: alunos.map((a) => ({ aluno_id: a.id, presente: a.presente })),
      });
      showSuccess("Presenças salvas com sucesso!");
      setTimeout(() => router.replace("/professor/home"), 800);
    } catch (err: any) {
      showError(err, "Erro ao salvar presenças");
    } finally {
      setSaving(false);
    }
  };

  const menuItems: any[] = [
    { icon: "home-outline", activeIcon: "home", route: "/professor/home", label: "Início" },
    { icon: "clipboard-outline", activeIcon: "clipboard", route: "/professor/turmas", label: "Turmas" },
    { icon: "calendar-outline", activeIcon: "calendar", route: "/professor/horarios-turmas", label: "Agenda" },
    { icon: "person-outline", activeIcon: "person", route: "/professor/perfil", label: "Perfil" },
  ];

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
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
        <Text style={styles.headerTitle} numberOfLines={1}>
          Revisão da Chamada
        </Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.summaryCard}>
          <Text style={styles.classTitle} numberOfLines={2}>
            {turma_nome || "Turma"}
          </Text>
          <Text style={styles.infoText}>
            Revise e ajuste as presenças antes de salvar.
          </Text>

          <View style={styles.divider} />

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{alunos.length}</Text>
              <Text style={styles.statLabel}>Total</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>{presentes}</Text>
              <Text style={styles.statLabel}>Presentes</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: Colors.brand.error }]}>{ausentes}</Text>
              <Text style={styles.statLabel}>Ausentes</Text>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.saveBtn, saving && { opacity: 0.75 }]}
            onPress={salvar}
            activeOpacity={0.8}
            disabled={saving}
            accessibilityRole="button"
            accessibilityLabel="Salvar presenças"
          >
            {saving ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="checkmark-circle-outline" size={20} color="#fff" />
                <Text style={styles.saveBtnText}>Salvar</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Lista de Alunos</Text>
          <Text style={styles.sectionHint}>Toque para alternar presença</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color={Colors.brand.primary} style={{ marginTop: 20 }} />
        ) : alunos.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={48} color={Colors.brand.textSecondary} />
            <Text style={styles.emptyTitle}>Nenhum aluno encontrado</Text>
          </View>
        ) : (
          alunos.map((aluno) => (
            <TouchableOpacity
              key={aluno.id}
              style={[
                styles.studentCard,
                aluno.presente ? styles.cardPresent : styles.cardAbsent,
              ]}
              onPress={() => togglePresenca(aluno.id)}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel={`${aluno.nome}: ${aluno.presente ? "Presente" : "Ausente"}. Toque para alternar.`}
            >
              <View
                style={[
                  styles.avatar,
                  {
                    backgroundColor: aluno.presente
                      ? "rgba(34, 197, 94, 0.15)"
                      : "rgba(255, 75, 75, 0.12)",
                  },
                ]}
              >
                <Text
                  style={[
                    styles.avatarText,
                    { color: aluno.presente ? "#22C55E" : Colors.brand.error },
                  ]}
                >
                  {aluno.nome.charAt(0).toUpperCase()}
                </Text>
              </View>

              <Text style={styles.studentName} numberOfLines={1} ellipsizeMode="tail">
                {aluno.nome}
              </Text>

              <View
                style={[
                  styles.statusTag,
                  aluno.presente ? styles.tagPresent : styles.tagAbsent,
                ]}
              >
                <Ionicons
                  name={aluno.presente ? "checkmark-circle" : "close-circle"}
                  size={13}
                  color="#fff"
                />
                <Text style={styles.tagText}>
                  {aluno.presente ? "Presente" : "Ausente"}
                </Text>
              </View>
            </TouchableOpacity>
          ))
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
  headerTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#fff",
    flex: 1,
    textAlign: "center",
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.brand.card,
    justifyContent: "center",
    alignItems: "center",
  },

  scrollContent: { paddingHorizontal: 20, paddingTop: 12 },

  summaryCard: {
    backgroundColor: Colors.brand.card,
    borderRadius: 24,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
  },
  classTitle: { color: "#fff", fontSize: 19, fontWeight: "800", lineHeight: 24 },
  infoText: {
    color: Colors.brand.textSecondary,
    fontSize: 13,
    marginTop: 6,
    marginBottom: 4,
  },
  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.06)",
    marginVertical: 16,
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
  statDivider: {
    width: 1,
    height: 36,
    backgroundColor: "rgba(255,255,255,0.07)",
  },

  saveBtn: {
    backgroundColor: "#22C55E",
    height: 52,
    borderRadius: 14,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  saveBtnText: { color: "#fff", fontWeight: "700", fontSize: 15 },

  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 14,
    paddingHorizontal: 4,
  },
  sectionTitle: { color: "#fff", fontSize: 17, fontWeight: "700" },
  sectionHint: { color: Colors.brand.textSecondary, fontSize: 12 },

  studentCard: {
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 10,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
  },
  cardPresent: {
    backgroundColor: Colors.brand.card,
    borderColor: "rgba(34, 197, 94, 0.15)",
  },
  cardAbsent: {
    backgroundColor: Colors.brand.card,
    borderColor: "rgba(255, 75, 75, 0.10)",
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

  emptyContainer: {
    alignItems: "center",
    paddingVertical: 48,
    paddingHorizontal: 24,
  },
  emptyTitle: { color: "#fff", fontSize: 16, fontWeight: "700", marginTop: 14 },
});
