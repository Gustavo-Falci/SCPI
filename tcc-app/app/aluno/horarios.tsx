import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  StatusBar,
  ActivityIndicator,
  Animated,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";

import { storage } from "../../services/storage";
import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

function isAulaAoVivo(horario: string): boolean {
  const parts = horario.split(' - ');
  if (parts.length !== 2) return false;
  const [inicioStr, fimStr] = parts;
  const now = new Date();
  const [hI, mI] = inicioStr.split(':').map(Number);
  const [hF, mF] = fimStr.split(':').map(Number);
  const nowMin = now.getHours() * 60 + now.getMinutes();
  const inicioMin = hI * 60 + mI;
  const fimMin = hF * 60 + mF;
  return nowMin >= inicioMin && nowMin <= fimMin;
}

function PulsingDot() {
  const anim = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 0.2, duration: 700, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 1, duration: 700, useNativeDriver: true }),
      ])
    ).start();
  }, []);
  return <Animated.View style={[styles.dot, { opacity: anim }]} />;
}

export default function Horarios() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [aulas, setAulas] = useState<any[]>([]);

  const loadHorarios = async () => {
    try {
      const userId = await storage.getItem("user_id");
      if (!userId) {
        router.replace("/auth/login");
        return;
      }
      // Usamos o endpoint de dashboard que já retorna as aulas de hoje filtradas
      const resp = await apiGet(`/aluno/dashboard/${userId}`);
      setAulas(resp.aulas_hoje || []);
    } catch (err) {
      console.error("Erro ao carregar horários aluno:", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadHorarios();
    }, [])
  );

  const getTodayDateFormatted = () => {
    const options: any = { weekday: 'long', day: 'numeric', month: 'long' };
    const date = new Date().toLocaleDateString('pt-BR', options);
    return date.charAt(0).toUpperCase() + date.slice(1);
  };

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
        <Text style={styles.headerTitle}>Horários de Aula</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.todayCard}>
          <View>
            <Text style={styles.todayTitle}>Agenda de Hoje</Text>
            <Text style={styles.todayDate}>{getTodayDateFormatted()}</Text>
          </View>
          <Ionicons name="calendar" size={32} color={Colors.brand.primary} />
        </View>

        <View style={styles.timeline}>
          {aulas.length > 0 ? (
            <>
              {aulas.map((aula, index) => {
                const aoVivo = isAulaAoVivo(aula.horario);
                const [inicio, fim] = aula.horario.split(' - ');
                const nextAula = aulas[index + 1];
                const hasGap = nextAula != null && fim !== nextAula.horario.split(' - ')[0];
                return (
                  <React.Fragment key={aula.id}>
                    <View style={styles.timelineItem}>
                      <View style={styles.timeColumn}>
                        <Text style={[styles.timeText, aoVivo && styles.timeTextLive]}>{inicio}</Text>
                        <View style={[styles.timelineLine, aoVivo && styles.timelineLineLive]} />
                      </View>

                      <View style={[styles.classCard, aoVivo && styles.classCardLive]}>
                        <View style={styles.cardHeader}>
                          <Text style={styles.className}>{aula.nome}</Text>
                          {aoVivo && (
                            <View style={styles.liveBadge}>
                              <PulsingDot />
                              <Text style={styles.liveBadgeText}>AO VIVO</Text>
                            </View>
                          )}
                        </View>

                        <View style={styles.cardFooter}>
                          <View style={styles.infoRow}>
                            <Ionicons name="location-outline" size={14} color={aoVivo ? '#4ade80' : Colors.brand.textSecondary} />
                            <Text style={[styles.infoText, aoVivo && styles.infoTextLive]}>{aula.sala}</Text>
                          </View>
                        </View>
                      </View>
                    </View>

                    {hasGap && (
                      <View style={styles.gapSection}>
                        <View style={styles.timeColumn}>
                          <Text style={styles.timeText}>{fim}</Text>
                          <View style={styles.gapDottedLine} />
                        </View>
                        <View style={styles.gapLabelContainer}>
                          <Text style={styles.gapLabelText}>intervalo</Text>
                        </View>
                      </View>
                    )}
                  </React.Fragment>
                );
              })}
              <View style={styles.timelineEnd}>
                <Text style={styles.timeText}>
                  {aulas[aulas.length - 1].horario.split(' - ')[1]}
                </Text>
              </View>
            </>
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="cafe-outline" size={50} color={Colors.brand.textSecondary} />
              <Text style={styles.emptyText}>Nenhuma aula agendada para hoje.</Text>
            </View>
          )}
        </View>

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
  todayCard: {
    backgroundColor: Colors.brand.card, borderRadius: 24, padding: 24, marginBottom: 32,
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  todayTitle: { color: "#fff", fontSize: 20, fontWeight: "800" },
  todayDate: { color: Colors.brand.textSecondary, fontSize: 14, marginTop: 4 },
  timeline: { paddingLeft: 4 },
  timelineItem: { flexDirection: "row", alignItems: "stretch", marginBottom: 8 },
  timeColumn: { alignItems: "center", width: 50, marginRight: 16 },
  timeText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  timelineLine: { width: 2, flex: 1, backgroundColor: "rgba(255,255,255,0.1)", marginVertical: 6 },
  timelineLineLive: { backgroundColor: "rgba(74,222,128,0.4)" },
  timelineEnd: { width: 50, alignItems: "center" },
  gapSection: { flexDirection: "row", alignItems: "center" },
  gapDottedLine: {
    width: 2, height: 28,
    borderLeftWidth: 2, borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.2)",
    marginVertical: 4,
  },
  gapLabelContainer: { flex: 1, marginLeft: 16, justifyContent: "center" },
  gapLabelText: { color: "rgba(255,255,255,0.25)", fontSize: 11, fontStyle: "italic" },
  classCard: {
    flex: 1, backgroundColor: Colors.brand.card, borderRadius: 20, padding: 16,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  className: { color: "#fff", fontSize: 15, fontWeight: "700", flex: 1, marginRight: 8 },
  cardFooter: { flexDirection: "row", gap: 16 },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  infoText: { color: Colors.brand.textSecondary, fontSize: 12 },
  emptyContainer: {
    alignItems: "center", paddingVertical: 48,
    backgroundColor: Colors.brand.card, borderRadius: 24,
    borderStyle: "dashed", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  emptyText: { color: Colors.brand.textSecondary, fontSize: 14, marginTop: 12, textAlign: 'center', paddingHorizontal: 24 },
  classCardLive: {
    borderColor: "#4ade80",
    borderWidth: 1.5,
  },
  timeTextLive: { color: "#4ade80" },
  liveBadge: {
    flexDirection: "row", alignItems: "center", gap: 4,
    backgroundColor: "rgba(74,222,128,0.15)", borderRadius: 20,
    paddingHorizontal: 8, paddingVertical: 3,
  },
  liveBadgeText: { color: "#4ade80", fontSize: 10, fontWeight: "800", letterSpacing: 0.8 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#4ade80" },
  infoTextLive: { color: "#4ade80" },
});
