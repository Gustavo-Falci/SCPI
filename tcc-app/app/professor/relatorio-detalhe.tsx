import React, { useState, useEffect } from "react";
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
import { useRouter, useLocalSearchParams } from "expo-router";

import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";

export default function RelatorioDetalhe() {
  const router = useRouter();
  const { chamada_id, turma_nome } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [detalhe, setDetalhe] = useState<any>(null);

  useEffect(() => {
    if (!chamada_id) return;
    const load = async () => {
      try {
        const data = await apiGet(`/professor/relatorios/chamadas/${chamada_id}`);
        setDetalhe(data);
      } catch (err) {
        console.error("Erro ao carregar detalhe:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [chamada_id]);

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
          {(turma_nome as string) || "Relatório"}
        </Text>
        <View style={{ width: 44 }} />
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.brand.primary} />
        </View>
      ) : !detalhe ? (
        <View style={styles.center}>
          <Ionicons name="alert-circle-outline" size={48} color={Colors.brand.textSecondary} />
          <Text style={styles.errorText}>Erro ao carregar relatório.</Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Chamada info */}
          <View style={styles.infoCard}>
            <Text style={styles.infoTitle}>{detalhe.nome_disciplina}</Text>
            <View style={styles.infoMetaRow}>
              <Ionicons name="calendar-outline" size={14} color={Colors.brand.textSecondary} />
              <Text style={styles.infoMeta}>{detalhe.data_chamada}</Text>
            </View>
            <View style={styles.infoMetaRow}>
              <Ionicons name="time-outline" size={14} color={Colors.brand.textSecondary} />
              <Text style={styles.infoMeta}>
                {detalhe.horario_inicio} – {detalhe.horario_fim}
              </Text>
            </View>
            <View style={styles.infoMetaRow}>
              <Ionicons name="barcode-outline" size={14} color={Colors.brand.textSecondary} />
              <Text style={styles.infoMeta}>{detalhe.codigo_turma}</Text>
            </View>
          </View>

          {/* Stats */}
          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{detalhe.total_alunos}</Text>
              <Text style={styles.statLabel}>Total</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>
                {detalhe.presentes}
              </Text>
              <Text style={styles.statLabel}>Presentes</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: Colors.brand.error }]}>
                {detalhe.ausentes}
              </Text>
              <Text style={styles.statLabel}>Ausentes</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text
                style={[
                  styles.statValue,
                  {
                    color:
                      detalhe.percentual >= 75
                        ? "#22C55E"
                        : Colors.brand.error,
                  },
                ]}
              >
                {detalhe.percentual}%
              </Text>
              <Text style={styles.statLabel}>Presença</Text>
            </View>
          </View>

          {/* Student list */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Lista de Alunos</Text>
            <Text style={styles.sectionCount}>
              {detalhe.alunos.length} aluno{detalhe.alunos.length !== 1 ? "s" : ""}
            </Text>
          </View>

          {detalhe.alunos.map((a: any) => (
            <View
              key={a.aluno_id}
              style={[
                styles.studentCard,
                a.presente ? styles.cardPresente : styles.cardAusente,
              ]}
            >
              <View
                style={[
                  styles.avatar,
                  {
                    backgroundColor: a.presente
                      ? "rgba(34,197,94,0.12)"
                      : "rgba(255,75,75,0.12)",
                  },
                ]}
              >
                <Text
                  style={[
                    styles.avatarText,
                    { color: a.presente ? "#22C55E" : Colors.brand.error },
                  ]}
                >
                  {a.nome.charAt(0).toUpperCase()}
                </Text>
              </View>

              <View style={{ flex: 1 }}>
                <Text style={styles.studentName} numberOfLines={1}>
                  {a.nome}
                </Text>
                <Text style={styles.studentRa}>RA {a.ra}</Text>
              </View>

              <View style={styles.tagGroup}>
                {a.presente && a.tipo_registro !== "—" && (
                  <View style={styles.tipoTag}>
                    <Text style={styles.tipoTagText}>{a.tipo_registro}</Text>
                  </View>
                )}
                <View
                  style={[
                    styles.statusTag,
                    a.presente ? styles.tagPresent : styles.tagAbsent,
                  ]}
                >
                  <Ionicons
                    name={a.presente ? "checkmark-circle" : "close-circle"}
                    size={13}
                    color="#fff"
                  />
                  <Text style={styles.tagText}>
                    {a.presente ? "Presente" : "Ausente"}
                  </Text>
                </View>
              </View>
            </View>
          ))}

          <View style={{ height: 48 }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  center: { flex: 1, justifyContent: "center", alignItems: "center", gap: 12 },
  errorText: { color: Colors.brand.textSecondary, fontSize: 15 },
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
  infoCard: {
    backgroundColor: Colors.brand.card,
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
    gap: 8,
  },
  infoTitle: { color: Colors.brand.text, fontSize: 20, fontWeight: "800", marginBottom: 4 },
  infoMetaRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  infoMeta: { color: Colors.brand.textSecondary, fontSize: 13 },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.brand.card,
    borderRadius: 20,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
  },
  statBox: { flex: 1, alignItems: "center" },
  statValue: { color: Colors.brand.text, fontSize: 22, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 11, marginTop: 4 },
  statDivider: {
    width: 1,
    height: 36,
    backgroundColor: "rgba(255,255,255,0.07)",
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  sectionTitle: { color: Colors.brand.text, fontSize: 17, fontWeight: "700" },
  sectionCount: { color: Colors.brand.textSecondary, fontSize: 13, fontWeight: "600" },
  studentCard: {
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 10,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
  },
  cardPresente: {
    backgroundColor: "rgba(34,197,94,0.04)",
    borderColor: "rgba(34,197,94,0.12)",
  },
  cardAusente: {
    backgroundColor: "rgba(255,75,75,0.04)",
    borderColor: "rgba(255,75,75,0.10)",
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
    color: Colors.brand.text,
    fontSize: 15,
    fontWeight: "600",
  },
  studentRa: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 2 },
  tagGroup: { flexDirection: "row", gap: 6, alignItems: "center", flexShrink: 0 },
  tipoTag: {
    backgroundColor: "rgba(255,255,255,0.07)",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  tipoTagText: { color: Colors.brand.textSecondary, fontSize: 10, fontWeight: "700" },
  statusTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    minWidth: 80,
    justifyContent: "center",
  },
  tagPresent: { backgroundColor: "rgba(34,197,94,0.85)" },
  tagAbsent: { backgroundColor: "rgba(255,75,75,0.85)" },
  tagText: { color: "#fff", fontSize: 11, fontWeight: "700" },
});
