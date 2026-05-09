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

import { storage } from "../../services/storage";
import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";

export default function FrequenciaDetalhe() {
  const router = useRouter();
  const { turma_id, turma_nome } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [detalhe, setDetalhe] = useState<any>(null);

  useEffect(() => {
    if (!turma_id) return;
    const load = async () => {
      try {
        const userId = await storage.getItem("user_id");
        if (!userId) { router.replace("/auth/login"); return; }
        const data = await apiGet(
          `/aluno/historico-chamadas/${userId}?turma_id=${turma_id}`
        );
        setDetalhe(data);
      } catch (err) {
        console.error("Erro ao carregar histórico:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [turma_id]);

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
          {(turma_nome as string) || "Frequência"}
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
          <Text style={styles.errorText}>Erro ao carregar histórico.</Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Disciplina info */}
          <View style={styles.infoCard}>
            <Text style={styles.infoTitle}>{detalhe.nome_disciplina}</Text>
            <Text style={styles.infoCodigo}>{detalhe.codigo_turma}</Text>

            {/* Barra de progresso */}
            <View style={styles.progressWrap}>
              <View style={styles.progressBg}>
                <View
                  style={[
                    styles.progressFill,
                    { width: `${detalhe.percentual}%` },
                    detalhe.percentual < 75 && { backgroundColor: Colors.brand.error },
                  ]}
                />
              </View>
              <Text
                style={[
                  styles.progressLabel,
                  detalhe.percentual < 75 && { color: Colors.brand.error },
                ]}
              >
                {detalhe.percentual}%
              </Text>
            </View>

            {detalhe.percentual < 75 && (
              <View style={styles.alertBadge}>
                <Ionicons name="warning-outline" size={14} color="#F59E0B" />
                <Text style={styles.alertText}>
                  Frequência abaixo do mínimo exigido (75%)
                </Text>
              </View>
            )}
          </View>

          {/* Stats */}
          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{detalhe.total}</Text>
              <Text style={styles.statLabel}>Total aulas</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={[styles.statValue, { color: "#22C55E" }]}>
                {detalhe.presentes}
              </Text>
              <Text style={styles.statLabel}>Presenças</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text
                style={[
                  styles.statValue,
                  detalhe.ausentes > 0 && { color: Colors.brand.error },
                ]}
              >
                {detalhe.ausentes}
              </Text>
              <Text style={styles.statLabel}>Faltas</Text>
            </View>
          </View>

          {/* Call history */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Histórico de Aulas</Text>
            <Text style={styles.sectionCount}>
              {detalhe.chamadas.length} aula{detalhe.chamadas.length !== 1 ? "s" : ""}
            </Text>
          </View>

          {detalhe.chamadas.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Ionicons
                name="calendar-outline"
                size={40}
                color={Colors.brand.textSecondary}
              />
              <Text style={styles.emptyText}>
                Nenhuma aula realizada ainda nesta disciplina.
              </Text>
            </View>
          ) : (
            detalhe.chamadas.map((c: any, idx: number) => {
              const parcial = c.aulas_presentes_count > 0 && c.aulas_presentes_count < c.total_aulas;
              const ausente = c.aulas_presentes_count === 0;
              const cardStyle = ausente ? styles.cardAusente : parcial ? styles.cardParcial : styles.cardPresente;
              const dayBg = ausente ? "rgba(255,75,75,0.12)" : parcial ? "rgba(245,158,11,0.12)" : "rgba(34,197,94,0.12)";
              const dayColor = ausente ? Colors.brand.error : parcial ? "#F59E0B" : "#22C55E";
              const tagStyle = ausente ? styles.tagAbsent : parcial ? styles.tagParcial : styles.tagPresent;
              const tagLabel = ausente ? "Falta" : parcial ? "Parcial" : "Presente";
              const tagIcon = ausente ? "close-circle" : parcial ? "remove-circle" : "checkmark-circle";
              return (
                <View key={c.chamada_id ?? idx} style={[styles.callCard, cardStyle]}>
                  {/* Linha 1: dia + data + badge */}
                  <View style={styles.cardRow}>
                    <View style={[styles.dayBadge, { backgroundColor: dayBg }]}>
                      <Text style={[styles.dayText, { color: dayColor }]}>
                        {c.dia_semana}
                      </Text>
                    </View>

                    <Text style={styles.callDate}>{c.data_chamada}</Text>

                    <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexShrink: 0 }}>
                      {c.total_aulas > 1 && (
                        <View style={styles.tipoTag}>
                          <Text style={styles.tipoTagText}>
                            {c.aulas_presentes_count}/{c.total_aulas}
                          </Text>
                        </View>
                      )}
                      <View style={[styles.statusTag, tagStyle]}>
                        <Ionicons name={tagIcon as any} size={13} color="#fff" />
                        <Text style={styles.tagText}>{tagLabel}</Text>
                      </View>
                    </View>
                  </View>

                  {/* Linha 2: horário + tipo de registro */}
                  <View style={styles.cardSubRow}>
                    <Ionicons
                      name="time-outline"
                      size={13}
                      color={Colors.brand.textSecondary}
                    />
                    <Text style={styles.callTime}>
                      {c.horario_inicio} – {c.horario_fim}
                    </Text>
                    {c.aulas_presentes_count > 0 && c.tipo_registro !== "—" && (
                      <View style={styles.tipoTag}>
                        <Text style={styles.tipoTagText}>{c.tipo_registro}</Text>
                      </View>
                    )}
                  </View>
                </View>
              );
            })
          )}

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
    borderRadius: 24,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
    gap: 8,
  },
  infoTitle: { color: Colors.brand.text, fontSize: 20, fontWeight: "800" },
  infoCodigo: { color: Colors.brand.textSecondary, fontSize: 13 },
  progressWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 4,
  },
  progressBg: {
    flex: 1,
    height: 8,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 4,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: "#22C55E",
    borderRadius: 4,
  },
  progressLabel: {
    color: "#22C55E",
    fontSize: 15,
    fontWeight: "800",
    minWidth: 44,
    textAlign: "right",
  },
  alertBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "rgba(245,158,11,0.1)",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 4,
  },
  alertText: { color: "#F59E0B", fontSize: 12, fontWeight: "600", flex: 1 },

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
  statValue: { color: Colors.brand.text, fontSize: 24, fontWeight: "800" },
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
  sectionCount: {
    color: Colors.brand.textSecondary,
    fontSize: 13,
    fontWeight: "600",
  },

  callCard: {
    borderRadius: 16,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 10,
    borderWidth: 1,
    gap: 10,
  },
  cardPresente: {
    backgroundColor: "rgba(34,197,94,0.04)",
    borderColor: "rgba(34,197,94,0.12)",
  },
  cardParcial: {
    backgroundColor: "rgba(245,158,11,0.04)",
    borderColor: "rgba(245,158,11,0.12)",
  },
  cardAusente: {
    backgroundColor: "rgba(255,75,75,0.04)",
    borderColor: "rgba(255,75,75,0.10)",
  },

  /* Linha 1: badge dia + data + status */
  cardRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  dayBadge: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
    flexShrink: 0,
  },
  dayText: { fontSize: 12, fontWeight: "800" },
  callDate: {
    color: Colors.brand.text,
    fontSize: 15,
    fontWeight: "700",
    flex: 1,
  },
  statusTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    flexShrink: 0,
  },
  tagPresent: { backgroundColor: "rgba(34,197,94,0.85)" },
  tagParcial: { backgroundColor: "rgba(245,158,11,0.85)" },
  tagAbsent: { backgroundColor: "rgba(255,75,75,0.85)" },
  tagText: { color: "#fff", fontSize: 11, fontWeight: "700" },

  /* Linha 2: horário + tipo */
  cardSubRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingLeft: 52, // alinha com o texto da linha acima (40px badge + 12px gap)
  },
  callTime: { color: Colors.brand.textSecondary, fontSize: 13, flex: 1 },
  tipoTag: {
    backgroundColor: "rgba(255,255,255,0.07)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  tipoTagText: {
    color: Colors.brand.textSecondary,
    fontSize: 10,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },

  emptyContainer: {
    alignItems: "center",
    paddingVertical: 48,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.07)",
    borderRadius: 20,
    borderStyle: "dashed",
  },
  emptyText: {
    color: Colors.brand.textSecondary,
    fontSize: 13,
    marginTop: 12,
    textAlign: "center",
    paddingHorizontal: 24,
  },
});
