import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";

import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function Relatorios() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [chamadas, setChamadas] = useState<any[]>([]);

  const loadRelatorios = async () => {
    setLoading(true);
    try {
      const data = await apiGet("/professor/relatorios/chamadas");
      setChamadas(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Erro ao carregar relatórios:", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadRelatorios();
    }, [])
  );

  const menuItems: any[] = [
    { icon: "home-outline", activeIcon: "home", route: "/professor/home", label: "Início" },
    { icon: "clipboard-outline", activeIcon: "clipboard", route: "/professor/turmas", label: "Turmas" },
    { icon: "document-text-outline", activeIcon: "document-text", route: "/professor/relatorios", label: "Relatórios" },
    { icon: "person-outline", activeIcon: "person", route: "/professor/perfil", label: "Perfil" },
  ];

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <StatusBar barStyle="light-content" />

      <View style={styles.header}>
        <Text style={styles.headerTitle}>Relatórios</Text>
        <Text style={styles.headerSubtitle}>Histórico imutável de chamadas realizadas</Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.brand.primary} />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {chamadas.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Ionicons name="document-text-outline" size={48} color={Colors.brand.textSecondary} />
              <Text style={styles.emptyTitle}>Nenhuma chamada realizada</Text>
              <Text style={styles.emptyText}>
                Suas chamadas encerradas aparecerão aqui.
              </Text>
            </View>
          ) : (
            chamadas.map((c) => (
              <TouchableOpacity
                key={c.chamada_id}
                style={styles.card}
                activeOpacity={0.75}
                accessibilityRole="button"
                accessibilityLabel={`Ver relatório de ${c.nome_disciplina}`}
                onPress={() =>
                  router.push({
                    pathname: "/professor/relatorio-detalhe",
                    params: { chamada_id: c.chamada_id, turma_nome: c.nome_disciplina },
                  })
                }
              >
                <View style={styles.cardTop}>
                  <View style={styles.disciplinaInfo}>
                    <Text style={styles.disciplinaNome} numberOfLines={1}>
                      {c.nome_disciplina}
                    </Text>
                    <Text style={styles.disciplinaCodigo}>
                      {c.codigo_turma} • {c.data_chamada}
                    </Text>
                    <Text style={styles.disciplinaHorario}>
                      {c.horario_inicio} – {c.horario_fim}
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.percentBadge,
                      {
                        backgroundColor:
                          c.percentual >= 75
                            ? "rgba(34,197,94,0.12)"
                            : "rgba(255,75,75,0.12)",
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.percentText,
                        {
                          color:
                            c.percentual >= 75 ? "#22C55E" : Colors.brand.error,
                        },
                      ]}
                    >
                      {c.percentual}%
                    </Text>
                  </View>
                </View>

                <View style={styles.statsRow}>
                  <View style={styles.statItem}>
                    <Text style={styles.statValue}>{c.total_alunos}</Text>
                    <Text style={styles.statLabel}>Total</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text style={[styles.statValue, { color: "#22C55E" }]}>
                      {c.presentes}
                    </Text>
                    <Text style={styles.statLabel}>Presentes</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text
                      style={[styles.statValue, { color: Colors.brand.error }]}
                    >
                      {c.ausentes}
                    </Text>
                    <Text style={styles.statLabel}>Ausentes</Text>
                  </View>
                  <Ionicons
                    name="chevron-forward"
                    size={20}
                    color={Colors.brand.textSecondary}
                    style={{ marginLeft: "auto" }}
                  />
                </View>
              </TouchableOpacity>
            ))
          )}
          <View style={{ height: 120 }} />
        </ScrollView>
      )}

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 24 },
  headerTitle: { color: Colors.brand.text, fontSize: 28, fontWeight: "800" },
  headerSubtitle: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    marginTop: 4,
  },
  scrollContent: { paddingHorizontal: 24, paddingTop: 4 },
  card: {
    backgroundColor: Colors.brand.card,
    borderRadius: 24,
    padding: 20,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  cardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  disciplinaInfo: { flex: 1, marginRight: 12 },
  disciplinaNome: {
    color: Colors.brand.text,
    fontSize: 17,
    fontWeight: "800",
  },
  disciplinaCodigo: {
    color: Colors.brand.textSecondary,
    fontSize: 13,
    marginTop: 4,
  },
  disciplinaHorario: {
    color: Colors.brand.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
  percentBadge: {
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  percentText: { fontSize: 18, fontWeight: "800" },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.05)",
    paddingTop: 14,
  },
  statItem: { flex: 1, alignItems: "center" },
  statValue: { color: Colors.brand.text, fontSize: 18, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 11, marginTop: 2 },
  statDivider: {
    width: 1,
    height: 28,
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  emptyContainer: {
    alignItems: "center",
    paddingVertical: 60,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.07)",
    borderRadius: 24,
    borderStyle: "dashed",
  },
  emptyTitle: {
    color: Colors.brand.text,
    fontSize: 16,
    fontWeight: "700",
    marginTop: 14,
  },
  emptyText: {
    color: Colors.brand.textSecondary,
    fontSize: 13,
    marginTop: 6,
    textAlign: "center",
    paddingHorizontal: 24,
  },
});
