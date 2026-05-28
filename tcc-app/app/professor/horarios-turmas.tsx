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

type Periodo = 'manha' | 'tarde' | 'noite';

function getPeriodo(horario: string): Periodo {
  const inicio = horario.split(' - ')[0] ?? '00:00';
  const hora = Number(inicio.split(':')[0]);
  if (hora <= 13) return 'manha';
  if (hora < 18) return 'tarde';
  return 'noite';
}

const PERIODO_LABEL: Record<Periodo, string> = {
  manha: 'Manhã',
  tarde: 'Tarde',
  noite: 'Noite',
};

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

export default function AulasDoDia() {
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
      const resp = await apiGet(`/professor/dashboard/${userId}`);
      setAulas(resp.aulas_hoje || []);
    } catch (err) {
      console.error("Erro ao carregar horários professor:", err);
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
    { icon: 'home-outline', activeIcon: 'home', route: '/professor/home', label: 'Início' },
    { icon: 'clipboard-outline', activeIcon: 'clipboard', route: '/professor/turmas', label: 'Turmas' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/professor/horarios-turmas', label: 'Agenda' },
    { icon: 'person-outline', activeIcon: 'person', route: '/professor/perfil', label: 'Perfil' },
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
        <Text style={styles.headerTitle}>Minha Agenda</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.todayCard}>
          <View>
            <Text style={styles.todayTitle}>Aulas de Hoje</Text>
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
                const prevAula = aulas[index - 1];
                const nextAula = aulas[index + 1];
                const periodo = getPeriodo(aula.horario);
                const samePeriodAsNext = nextAula != null && getPeriodo(nextAula.horario) === periodo;
                const samePeriodAsPrev = prevAula != null && getPeriodo(prevAula.horario) === periodo;
                const hasGap = samePeriodAsNext && fim !== nextAula.horario.split(' - ')[0];
                const isLast = index === aulas.length - 1;
                const isLastOfPeriod = !samePeriodAsNext;
                const isFirstOfPeriod = !samePeriodAsPrev;
                const prevConnects = samePeriodAsPrev && prevAula.horario.split(' - ')[1] === inicio;
                const nextConnects = samePeriodAsNext && fim === nextAula.horario.split(' - ')[0];

                return (
                  <React.Fragment key={aula.id}>
                    {isFirstOfPeriod && (
                      <View style={styles.periodHeader}>
                        <Text style={styles.periodLabel}>{PERIODO_LABEL[periodo]}</Text>
                        <View style={styles.periodDivider} />
                      </View>
                    )}
                    {isFirstOfPeriod && periodo === 'manha' && inicio !== '07:40' && (
                      <View style={styles.gapSection}>
                        <View style={styles.timeColumn}>
                          <Text style={styles.boundText}>07:40</Text>
                          <View style={styles.gapDottedLine} />
                        </View>
                        <View style={styles.gapLabelContainer}>
                          <Text style={styles.boundLabel}>início do turno</Text>
                        </View>
                      </View>
                    )}
                    <View style={styles.timelineItem}>
                      <View style={styles.timeColumn}>
                        {!prevConnects && (
                          <Text style={[styles.timeText, aoVivo && styles.timeTextLive]}>{inicio}</Text>
                        )}
                        <View style={[styles.timelineLine, aoVivo && styles.timelineLineLive]} />
                        {(isLast || isLastOfPeriod) && (
                          <Text style={[styles.timeText, aoVivo && styles.timeTextLive]}>{fim}</Text>
                        )}
                      </View>

                      <TouchableOpacity
                        style={[styles.classCard, aoVivo && styles.classCardLive]}
                        activeOpacity={0.7}
                        accessibilityRole="button"
                        accessibilityLabel={`Aula de ${aula.nome}${aoVivo ? ', ao vivo' : ''}`}
                        onPress={() => router.push("/professor/iniciar-chamada")}
                      >
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
                      </TouchableOpacity>
                    </View>

                    {nextConnects && (
                      <View style={styles.bridgeSection}>
                        <View style={styles.timeColumn}>
                          <Text style={styles.timeText}>{fim}</Text>
                        </View>
                        <View style={styles.bridgeLine} />
                      </View>
                    )}

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
                    {isLast && periodo === 'noite' && fim !== '23:05' && (
                      <View style={styles.gapSection}>
                        <View style={styles.timeColumn}>
                          <View style={styles.gapDottedLine} />
                          <Text style={styles.boundText}>23:05</Text>
                        </View>
                        <View style={styles.gapLabelContainer}>
                          <Text style={styles.boundLabel}>fim do turno</Text>
                        </View>
                      </View>
                    )}
                  </React.Fragment>
                );
              })}
            </>
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="calendar-outline" size={50} color={Colors.brand.textSecondary} />
              <Text style={styles.emptyText}>Sem aulas agendadas para hoje.</Text>
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
  periodHeader: {
    flexDirection: "row", alignItems: "center", gap: 12,
    marginTop: 8, marginBottom: 12,
  },
  periodLabel: {
    color: "#fff", fontSize: 12, fontWeight: "800",
    letterSpacing: 1.2, textTransform: "uppercase",
  },
  periodDivider: {
    flex: 1, height: 1, backgroundColor: "rgba(255,255,255,0.08)",
  },
  timelineItem: { flexDirection: "row", alignItems: "stretch", marginBottom: 4 },
  timeColumn: { alignItems: "center", width: 50, marginRight: 16 },
  timeText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  timelineLine: {
    width: 2,
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.1)",
    marginVertical: 6,
  },
  timelineLineLive: { backgroundColor: "rgba(74,222,128,0.4)" },
  gapSection: { flexDirection: "row", alignItems: "center" },
  bridgeSection: { flexDirection: "row", alignItems: "center", marginVertical: 4 },
  bridgeLine: {
    flex: 1,
    height: 1,
    backgroundColor: "rgba(255,255,255,0.06)",
    marginLeft: 16,
  },
  gapDottedLine: {
    width: 2, height: 28,
    borderLeftWidth: 2, borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.2)",
    marginVertical: 4,
  },
  gapLabelContainer: { flex: 1, marginLeft: 16, justifyContent: "center" },
  gapLabelText: { color: "rgba(255,255,255,0.25)", fontSize: 11, fontStyle: "italic" },
  boundText: { color: "rgba(255,255,255,0.55)", fontSize: 12, fontWeight: "700" },
  boundLabel: { color: "rgba(255,255,255,0.4)", fontSize: 11, fontStyle: "italic", letterSpacing: 0.4 },
  classCard: {
    flex: 1,
    minHeight: 88,
    justifyContent: "center",
    backgroundColor: Colors.brand.card,
    borderRadius: 18,
    paddingHorizontal: 15,
    paddingVertical: 13,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 },
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
