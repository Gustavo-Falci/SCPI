import React, { useState, useCallback } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  StatusBar,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";

import { storage } from "../../services/storage";
import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function Frequencia() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const loadFrequencias = async () => {
    setLoading(true);
    setError(null);
    try {
      const userId = await storage.getItem("user_id");
      if (!userId) {
        router.replace("/auth/login");
        return;
      }
      const resp = await apiGet(`/aluno/frequencias/${userId}`);
      setData(resp);
    } catch (err: any) {
      console.error("Erro ao carregar frequencias aluno:", err);
      setError(err?.message || "Erro ao carregar frequências.");
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadFrequencias();
    }, [])
  );

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/aluno/home', label: 'Início' },
    { icon: 'stats-chart-outline', activeIcon: 'stats-chart', route: '/aluno/frequencia', label: 'Frequência' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/aluno/horarios', label: 'Horários' },
    { icon: 'person-outline', activeIcon: 'person', route: '/aluno/perfil', label: 'Perfil' },
  ];

  if (loading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color={Colors.brand.primary} />
      </View>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <StatusBar barStyle="light-content" />
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.backBtn}
            activeOpacity={0.7}
          >
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Minhas Frequências</Text>
          <View style={{ width: 44 }} />
        </View>
        <View style={[styles.center, { flex: 1 }]}>
          <Ionicons name="warning-outline" size={48} color={Colors.brand.error} />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={loadFrequencias} activeOpacity={0.75}>
            <Text style={styles.retryLabel}>Tentar novamente</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

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
        <Text style={styles.headerTitle}>Minhas Frequências</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.summaryCard}>
          <View style={styles.summaryInfo}>
            <Text style={styles.summaryLabel}>Média Geral</Text>
            <Text style={styles.summaryValue}>{data?.media_geral || 0}%</Text>
          </View>
          <View style={styles.iconCircle}>
            <Ionicons name="trending-up" size={32} color={Colors.brand.primary} />
          </View>
        </View>

        <Text style={styles.sectionTitle}>Disciplinas</Text>

        {data?.frequencias && data.frequencias.length > 0 ? (
          data.frequencias.map((item: any, index: number) => {
            const isLow = item.presenca < 75;
            return (
              <TouchableOpacity
                key={index}
                style={styles.card}
                activeOpacity={0.75}
                accessibilityRole="button"
                accessibilityLabel={`Ver histórico de ${item.nome}`}
                onPress={() =>
                  router.push({
                    pathname: "/aluno/frequencia-detalhe",
                    params: { turma_id: item.turma_id, turma_nome: item.nome },
                  })
                }
              >
                <View style={styles.cardHeader}>
                  <Text style={styles.subjectName} numberOfLines={1}>{item.nome}</Text>
                  <View style={styles.percentRow}>
                    <Text style={[styles.percentageText, isLow && { color: Colors.brand.error }]}>
                      {item.presenca}%
                    </Text>
                    <Ionicons name="chevron-forward" size={16} color={isLow ? Colors.brand.error : "#22C55E"} />
                  </View>
                </View>

                <View style={styles.progressBarBg}>
                  <View
                    style={[
                      styles.progressBarFill,
                      { width: `${item.presenca}%` },
                      isLow && { backgroundColor: Colors.brand.error },
                    ]}
                  />
                </View>

                <View style={styles.cardFooter}>
                  <View style={styles.footerItem}>
                    <Text style={styles.footerLabel}>Aulas Totais</Text>
                    <Text style={styles.footerValue}>{item.total}</Text>
                  </View>
                  <View style={styles.footerItem}>
                    <Text style={styles.footerLabel}>Presenças</Text>
                    <Text style={styles.footerValue}>{item.presencas_count}</Text>
                  </View>
                  <View style={styles.footerItem}>
                    <Text style={styles.footerLabel}>Faltas</Text>
                    <Text style={[styles.footerValue, isLow && { color: Colors.brand.error }]}>
                      {item.faltas_count}
                    </Text>
                  </View>
                </View>
              </TouchableOpacity>
            );
          })
        ) : (
          <View style={styles.emptyContainer}>
            <Ionicons name="stats-chart-outline" size={50} color={Colors.brand.textSecondary} />
            <Text style={styles.emptyText}>Você ainda não possui frequências registradas.</Text>
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
  center: { justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, height: 60 },
  headerTitle: { fontSize: 18, fontWeight: "800", color: "#fff" },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.brand.card, justifyContent: "center", alignItems: "center" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 10 },
  summaryCard: {
    backgroundColor: Colors.brand.card, borderRadius: 24, padding: 24, marginBottom: 32,
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  summaryInfo: { flex: 1 },
  summaryLabel: { color: Colors.brand.textSecondary, fontSize: 14, fontWeight: "600" },
  summaryValue: { color: "#fff", fontSize: 32, fontWeight: "800", marginTop: 4 },
  iconCircle: { width: 60, height: 60, borderRadius: 30, backgroundColor: "rgba(75, 57, 239, 0.1)", justifyContent: "center", alignItems: "center" },
  sectionTitle: { color: "#fff", fontSize: 18, fontWeight: "700", marginBottom: 16, marginLeft: 4 },
  card: {
    backgroundColor: Colors.brand.card, borderRadius: 24, padding: 20, marginBottom: 16,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  subjectName: { color: "#fff", fontSize: 16, fontWeight: "700", flex: 1, marginRight: 10 },
  percentRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  percentageText: { color: "#22C55E", fontSize: 18, fontWeight: "800" },
  progressBarBg: { height: 8, backgroundColor: "rgba(255,255,255,0.05)", borderRadius: 4, overflow: "hidden", marginBottom: 16 },
  progressBarFill: { height: "100%", backgroundColor: "#22C55E", borderRadius: 4 },
  cardFooter: { flexDirection: "row", justifyContent: "space-between", borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.05)", paddingTop: 16 },
  footerItem: { alignItems: "center" },
  footerLabel: { color: Colors.brand.textSecondary, fontSize: 10, fontWeight: "600", textTransform: "uppercase", marginBottom: 4 },
  footerValue: { color: "#fff", fontSize: 14, fontWeight: "700" },
  emptyContainer: {
    alignItems: "center", paddingVertical: 48,
    backgroundColor: Colors.brand.card, borderRadius: 24,
    borderStyle: "dashed", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  emptyText: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    marginTop: 12,
    textAlign: 'center',
    paddingHorizontal: 24,
  },
  errorText: {
    color: Colors.brand.error,
    fontSize: 14,
    marginTop: 12,
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  retryBtn: {
    marginTop: 20,
    backgroundColor: Colors.brand.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  retryLabel: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
