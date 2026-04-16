import React from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function Horarios() {
  const router = useRouter();

  const aulas = [
    { id: 1, nome: "Engenharia de Software I", horario: "08:00 - 09:30", sala: "Sala 02", status: "agora" },
    { id: 2, nome: "Cálculo II", horario: "10:00 - 11:30", sala: "Sala 05", status: "proxima" },
    { id: 3, nome: "Estrutura de Dados", horario: "13:00 - 14:30", sala: "Lab 03", status: "proxima" },
    { id: 4, nome: "Inglês Instrumental", horario: "15:00 - 16:30", sala: "Sala 09", status: "proxima" },
    { id: 5, nome: "Programação Linear", horario: "17:00 - 18:30", sala: "Lab 07", status: "proxima" },
  ];

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/aluno/home' },
    { icon: 'stats-chart-outline', activeIcon: 'stats-chart', route: '/aluno/frequencia' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/aluno/horarios' },
    { icon: 'person-outline', activeIcon: 'person', route: '/aluno/perfil' },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
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
            <Text style={styles.todayDate}>Segunda, 15 de Abril</Text>
          </View>
          <Ionicons name="calendar" size={32} color={Colors.brand.primary} />
        </View>

        <View style={styles.timeline}>
          {aulas.map((aula, index) => (
            <View key={aula.id} style={styles.timelineItem}>
              <View style={styles.timeColumn}>
                <Text style={styles.timeText}>{aula.horario.split(' - ')[0]}</Text>
                <View style={[styles.timelineLine, index === aulas.length - 1 && { backgroundColor: 'transparent' }]} />
              </View>

              <View style={[styles.classCard, aula.status === 'agora' && styles.activeCard]}>
                <View style={styles.cardHeader}>
                  <Text style={styles.className}>{aula.nome}</Text>
                  {aula.status === 'agora' && (
                    <View style={styles.liveBadge}>
                      <Text style={styles.liveText}>AGORA</Text>
                    </View>
                  )}
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
          ))}
        </View>

        <View style={{ height: 120 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
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
  activeCard: { borderColor: Colors.brand.primary, borderWidth: 1.5 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  className: { color: "#fff", fontSize: 15, fontWeight: "700", flex: 1, marginRight: 8 },
  liveBadge: { backgroundColor: Colors.brand.primary, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  liveText: { color: "#fff", fontSize: 10, fontWeight: "800" },
  cardFooter: { flexDirection: "row", gap: 16 },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  infoText: { color: Colors.brand.textSecondary, fontSize: 12 },
});
