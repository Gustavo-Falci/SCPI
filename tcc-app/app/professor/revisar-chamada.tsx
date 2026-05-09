import React, { useState, useEffect } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  StatusBar,
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
  aulasPresentes: boolean[]; // índice 0 = Aula 1, comprimento = totalAulas
};

export default function RevisarChamada() {
  const { chamada_id, turma_nome } = useLocalSearchParams();
  const router = useRouter();
  const { showError, showSuccess } = useErrorToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [totalAulas, setTotalAulas] = useState(1);
  const [alunos, setAlunos] = useState<Aluno[]>([]);

  useEffect(() => {
    carregarAlunos();
  }, [chamada_id]);

  const carregarAlunos = async () => {
    try {
      const resp = await apiGet(`/chamadas/${chamada_id}/alunos`);
      const n = resp?.total_aulas ?? 1;
      setTotalAulas(n);
      setAlunos(
        (resp?.alunos ?? []).map((a: any) => ({
          id: a.id,
          nome: a.nome,
          aulasPresentes: Array.from({ length: n }, (_, i) =>
            (a.aulas_presentes ?? []).includes(i + 1)
          ),
        }))
      );
    } catch (err: any) {
      showError(err, "Erro ao carregar alunos");
    } finally {
      setLoading(false);
    }
  };

  const toggleCard = (alunoId: string) => {
    setAlunos((prev) =>
      prev.map((a) => {
        if (a.id !== alunoId) return a;
        const todasPresentes = a.aulasPresentes.every(Boolean);
        return {
          ...a,
          aulasPresentes: a.aulasPresentes.map(() => !todasPresentes),
        };
      })
    );
  };

  const toggleAula = (alunoId: string, aulaIdx: number) => {
    setAlunos((prev) =>
      prev.map((a) => {
        if (a.id !== alunoId) return a;
        const novo = [...a.aulasPresentes];
        novo[aulaIdx] = !novo[aulaIdx];
        return { ...a, aulasPresentes: novo };
      })
    );
  };

  const totalPresencas = alunos.reduce(
    (sum, a) => sum + a.aulasPresentes.filter(Boolean).length,
    0
  );
  const totalPossivel = alunos.length * totalAulas;
  const totalFaltas = totalPossivel - totalPresencas;

  const salvar = async () => {
    if (saving) return;
    try {
      setSaving(true);
      await apiPost(`/chamadas/${chamada_id}/ajustar`, {
        alunos: alunos.map((a) => ({
          aluno_id: a.id,
          aulas_presentes: a.aulasPresentes
            .map((presente, i) => (presente ? i + 1 : null))
            .filter((n): n is number => n !== null),
        })),
      });
      showSuccess("Presenças salvas com sucesso!");
      setTimeout(() => router.replace("/professor/home"), 800);
    } catch (err: any) {
      showError(err, "Erro ao salvar presenças");
    } finally {
      setSaving(false);
    }
  };

  const cardBorderColor = (a: Aluno) => {
    const qtd = a.aulasPresentes.filter(Boolean).length;
    if (qtd === 0) return "rgba(255, 75, 75, 0.25)";
    if (qtd === totalAulas) return "rgba(34, 197, 94, 0.25)";
    return "rgba(234, 179, 8, 0.35)";
  };

  const tagColor = (a: Aluno) => {
    const qtd = a.aulasPresentes.filter(Boolean).length;
    if (qtd === 0) return "rgba(255, 75, 75, 0.85)";
    if (qtd === totalAulas) return "rgba(34, 197, 94, 0.85)";
    return "rgba(234, 179, 8, 0.85)";
  };

  const tagText = (a: Aluno) => {
    const qtd = a.aulasPresentes.filter(Boolean).length;
    return `${qtd}/${totalAulas} aula${totalAulas > 1 ? "s" : ""}`;
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
            Toque no card para alternar todas as aulas. Toque em cada aula para ajuste individual.
          </Text>

          <View style={styles.divider} />

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{alunos.length}</Text>
              <Text style={styles.statLabel}>Alunos</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>{totalPresencas}</Text>
              <Text style={styles.statLabel}>Presenças</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: Colors.brand.error }]}>{totalFaltas}</Text>
              <Text style={styles.statLabel}>Faltas</Text>
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
          <Text style={styles.sectionHint}>{totalAulas} aula{totalAulas > 1 ? "s" : ""} nesta chamada</Text>
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
              style={[styles.studentCard, { borderColor: cardBorderColor(aluno) }]}
              onPress={() => toggleCard(aluno.id)}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel={`${aluno.nome}: ${tagText(aluno)}. Toque para alternar todas.`}
            >
              <View style={styles.cardTop}>
                <View
                  style={[
                    styles.avatar,
                    {
                      backgroundColor:
                        aluno.aulasPresentes.filter(Boolean).length === 0
                          ? "rgba(255, 75, 75, 0.12)"
                          : aluno.aulasPresentes.every(Boolean)
                          ? "rgba(34, 197, 94, 0.15)"
                          : "rgba(234, 179, 8, 0.15)",
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.avatarText,
                      {
                        color:
                          aluno.aulasPresentes.filter(Boolean).length === 0
                            ? Colors.brand.error
                            : aluno.aulasPresentes.every(Boolean)
                            ? "#22C55E"
                            : "#EAB308",
                      },
                    ]}
                  >
                    {aluno.nome.charAt(0).toUpperCase()}
                  </Text>
                </View>

                <Text style={styles.studentName} numberOfLines={1} ellipsizeMode="tail">
                  {aluno.nome}
                </Text>

                <View style={[styles.statusTag, { backgroundColor: tagColor(aluno) }]}>
                  <Text style={styles.tagText}>{tagText(aluno)}</Text>
                </View>
              </View>

              {totalAulas > 1 && (
                <View style={styles.aulasRow}>
                  {aluno.aulasPresentes.map((presente, idx) => (
                    <TouchableOpacity
                      key={idx}
                      style={styles.aulaChip}
                      onPress={() => toggleAula(aluno.id, idx)}
                      activeOpacity={0.7}
                      accessibilityRole="checkbox"
                      accessibilityLabel={`Aula ${idx + 1}: ${presente ? "presente" : "ausente"}`}
                      accessibilityState={{ checked: presente }}
                    >
                      <Ionicons
                        name={presente ? "checkbox" : "square-outline"}
                        size={18}
                        color={presente ? "#22C55E" : Colors.brand.textSecondary}
                      />
                      <Text style={[styles.aulaLabel, { color: presente ? "#22C55E" : Colors.brand.textSecondary }]}>
                        Aula {idx + 1}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
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
    backgroundColor: Colors.brand.card,
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 10,
    borderWidth: 1,
  },
  cardTop: {
    flexDirection: "row",
    alignItems: "center",
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
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    flexShrink: 0,
    minWidth: 68,
    alignItems: "center",
  },
  tagText: { color: "#fff", fontSize: 11, fontWeight: "700" },

  aulasRow: {
    flexDirection: "row",
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.06)",
    gap: 16,
    flexWrap: "wrap",
  },
  aulaChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingVertical: 2,
  },
  aulaLabel: { fontSize: 13, fontWeight: "600" },

  emptyContainer: {
    alignItems: "center",
    paddingVertical: 48,
    paddingHorizontal: 24,
  },
  emptyTitle: { color: "#fff", fontSize: 16, fontWeight: "700", marginTop: 14 },
});
