import React, { useState, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
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
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{aulas.length}</Text>
          </View>
        </View>

        <View style={styles.timeline}>
          {aulas.length > 0 ? (
            aulas.map((aula, index) => {
              const parts = aula.horario.split(' - ');
              const timeStart = parts[0] ?? '';
              const timeEnd = parts[1] ?? '';

              const isNow = (() => {
                if (parts.length < 2) return false;
                const [hI, mI] = timeStart.split(':').map(Number);
                const [hF, mF] = timeEnd.split(':').map(Number);
                const cur = new Date().getHours() * 60 + new Date().getMinutes();
                return cur >= hI * 60 + mI && cur < hF * 60 + mF;
              })();

              const isPast = (() => {
                if (parts.length < 2) return false;
                const [hF, mF] = timeEnd.split(':').map(Number);
                const cur = new Date().getHours() * 60 + new Date().getMinutes();
                return cur >= hF * 60 + mF;
              })();

              return (
                <View key={aula.id} style={styles.timelineItem}>
                  {/* Coluna de horário */}
                  <View style={styles.timeColumn}>
                    <Text style={[styles.timeStart, isPast && !isNow && styles.timePast]}>
                      {timeStart}
                    </Text>
                    <Text style={styles.timeEnd}>{timeEnd}</Text>
                  </View>

                  {/* Dot + linha conectora */}
                  <View style={styles.connector}>
                    <View style={[
                      styles.dot,
                      isNow && styles.dotActive,
                      isPast && styles.dotPast,
                    ]} />
                    {index < aulas.length - 1 && (
                      <View style={styles.connectorLine} />
                    )}
                  </View>

                  {/* Card da aula */}
                  <TouchableOpacity
                    style={[
                      styles.classCard,
                      isNow && styles.activeCard,
                      isPast && styles.pastCard,
                    ]}
                    activeOpacity={0.7}
                    accessibilityRole="button"
                    accessibilityLabel={`Aula de ${aula.nome}${isNow ? ', ao vivo' : ''}`}
                    onPress={() => router.push("/professor/iniciar-chamada")}
                  >
                    <View style={styles.cardHeader}>
                      <Text style={[styles.className, isPast && styles.textPast]} numberOfLines={2}>
                        {aula.nome}
                      </Text>
                      {isNow && (
                        <View style={styles.liveBadge}>
                          <View style={styles.liveDot} />
                          <Text style={styles.liveText}>AO VIVO</Text>
                        </View>
                      )}
                      {isPast && (
                        <View style={styles.pastBadge}>
                          <Text style={styles.pastBadgeText}>Encerrada</Text>
                        </View>
                      )}
                    </View>

                    <View style={styles.infoRow}>
                      <Ionicons name="location-outline" size={13} color={Colors.brand.textSecondary} />
                      <Text style={styles.infoText}>{aula.sala}</Text>
                    </View>

                    {isNow && (
                      <View style={styles.callButton}>
                        <Text style={styles.callButtonText}>Ir para Chamada</Text>
                        <Ionicons name="arrow-forward" size={16} color="#fff" />
                      </View>
                    )}
                  </TouchableOpacity>
                </View>
              );
            })
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
  countBadge: { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.brand.primary, justifyContent: "center", alignItems: "center" },
  countText: { color: "#fff", fontWeight: "800", fontSize: 18 },
  timeline: { paddingLeft: 4 },
  timelineItem: { flexDirection: "row", marginBottom: 16, alignItems: "flex-start" },

  timeColumn: { width: 56, alignItems: "flex-end", paddingRight: 4, paddingTop: 1 },
  timeStart: { color: "#fff", fontSize: 14, fontWeight: "700", lineHeight: 18 },
  timeEnd: { color: Colors.brand.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 2 },
  timePast: { color: Colors.brand.textSecondary },

  connector: { width: 24, alignItems: "center", paddingTop: 3 },
  dot: {
    width: 12, height: 12, borderRadius: 6,
    backgroundColor: Colors.brand.card,
    borderWidth: 2, borderColor: "rgba(255,255,255,0.25)",
  },
  dotActive: { backgroundColor: "#22C55E", borderColor: "#22C55E" },
  dotPast: { backgroundColor: "transparent", borderColor: "rgba(255,255,255,0.1)" },
  connectorLine: {
    width: 2, flex: 1, minHeight: 24,
    backgroundColor: "rgba(255,255,255,0.08)",
    marginTop: 4,
  },

  classCard: {
    flex: 1, backgroundColor: Colors.brand.card, borderRadius: 16, padding: 14,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)", marginLeft: 10,
  },
  activeCard: { borderColor: "#22C55E", borderWidth: 1.5 },
  pastCard: { opacity: 0.5 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 },
  className: { color: "#fff", fontSize: 15, fontWeight: "700", flex: 1, marginRight: 8 },
  textPast: { color: Colors.brand.textSecondary },
  liveBadge: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: "rgba(34, 197, 94, 0.15)", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#22C55E" },
  liveText: { color: "#22C55E", fontSize: 10, fontWeight: "800" },
  pastBadge: { backgroundColor: "rgba(255,255,255,0.06)", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  pastBadgeText: { color: Colors.brand.textSecondary, fontSize: 10, fontWeight: "700" },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  infoText: { color: Colors.brand.textSecondary, fontSize: 12 },
  callButton: {
    marginTop: 12, backgroundColor: Colors.brand.primary, paddingVertical: 10,
    borderRadius: 12, flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 8,
  },
  callButtonText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  emptyContainer: {
    alignItems: "center", paddingVertical: 48,
    backgroundColor: Colors.brand.card, borderRadius: 24,
    borderStyle: "dashed", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  emptyText: { color: Colors.brand.textSecondary, fontSize: 14, marginTop: 12, textAlign: 'center', paddingHorizontal: 24 },
});
