import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Colors } from "../../constants/theme";

type Chamada = {
  chamada_id: string | number;
  nome_disciplina: string;
  codigo_turma: string;
  data_chamada: string;
  horario_inicio: string;
  horario_fim: string;
  percentual: number;
  total_alunos: number;
  presentes_alunos: number;
  ausentes_alunos: number;
  parciais_alunos: number;
};

/**
 * Card de uma chamada na lista de relatórios.
 *
 * Memoizado porque a FlatList re-renderiza itens fora da tela quando a
 * referência do item muda — sem isso a virtualização rende bem menos.
 */
export const RelatorioCard = React.memo(function RelatorioCard({
  chamada: c,
  onPress,
}: {
  chamada: Chamada;
  onPress: () => void;
}) {
  const bom = c.percentual >= 75;
  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.75}
      accessibilityRole="button"
      accessibilityLabel={`Ver relatório de ${c.nome_disciplina}`}
      onPress={onPress}
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
            { backgroundColor: bom ? "rgba(34,197,94,0.12)" : "rgba(255,75,75,0.12)" },
          ]}
        >
          <Text style={[styles.percentText, { color: bom ? "#22C55E" : Colors.brand.error }]}>
            {c.percentual}%
          </Text>
        </View>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{c.total_alunos}</Text>
          <Text style={styles.statLabel}>Alunos</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statItem}>
          <Text style={[styles.statValue, { color: "#22C55E" }]}>{c.presentes_alunos}</Text>
          <Text style={styles.statLabel}>Presentes</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statItem}>
          <Text style={[styles.statValue, { color: Colors.brand.error }]}>{c.ausentes_alunos}</Text>
          <Text style={styles.statLabel}>Ausentes</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statItem}>
          <Text style={[styles.statValue, { color: "#F59E0B" }]}>{c.parciais_alunos}</Text>
          <Text style={styles.statLabel}>Parciais</Text>
        </View>
        <Ionicons
          name="chevron-forward"
          size={20}
          color={Colors.brand.textSecondary}
          style={{ marginLeft: "auto" }}
        />
      </View>
    </TouchableOpacity>
  );
});

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.brand.card,
    borderRadius: 24,
    padding: 20,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 },
  disciplinaInfo: { flex: 1, marginRight: 12 },
  disciplinaNome: { color: Colors.brand.text, fontSize: 17, fontWeight: "800" },
  disciplinaCodigo: { color: Colors.brand.textSecondary, fontSize: 13, marginTop: 4 },
  disciplinaHorario: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 2 },
  percentBadge: { borderRadius: 16, paddingHorizontal: 14, paddingVertical: 10, alignItems: "center", justifyContent: "center" },
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
  statDivider: { width: 1, height: 28, backgroundColor: "rgba(255,255,255,0.06)" },
});
