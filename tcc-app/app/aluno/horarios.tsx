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
            aulas.map((aula, index) => (
              <View key={aula.id} style={styles.timelineItem}>
                <View style={styles.timeColumn}>
                  <Text style={styles.timeText}>{aula.horario.split(' - ')[0]}</Text>
                  <View style={[styles.timelineLine, index === aulas.length - 1 && { backgroundColor: 'transparent' }]} />
                </View>

                <View style={styles.classCard}>
                  <View style={styles.cardHeader}>
                    <Text style={styles.className}>{aula.nome}</Text>
                  </View>
                  
                  <View style={styles.cardFooter}>
                    <View style={styles.infoRow}>
                      <Ionicons name="location-outline" size={14} color={Colors.brand.textSecondary} />
                      <Text style={styles.infoText}>{aula.sala}</Text>
                    </View>
                    <View style={styles.infoRow}>
                      <Ionicons name="time-outline" size={14} color={Colors.brand.textSecondary} />
                      <Text style={styles.infoText}>{aula.horario}</Text>
                    </View>
                  </View>
                </View>
              </View>
            ))
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
  timelineItem: { flexDirection: "row", marginBottom: 12 },
  timeColumn: { alignItems: "center", width: 50, marginRight: 16 },
  timeText: { color: "#fff", fontSize: 14, fontWeight: "700" },
  timelineLine: { width: 2, flex: 1, backgroundColor: "rgba(255,255,255,0.1)", marginVertical: 8 },
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
});
