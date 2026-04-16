import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { Colors } from "../../constants/theme";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function Frequencia() {
  const router = useRouter();

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/aluno/home' },
    { icon: 'stats-chart-outline', activeIcon: 'stats-chart', route: '/aluno/frequencia' },
    { icon: 'calendar-outline', activeIcon: 'calendar', route: '/aluno/horarios' },
    { icon: 'person-outline', activeIcon: 'person', route: '/aluno/perfil' },
  ];

  const frequencias = [
    { nome: "Cálculo I", presenca: 85, total: 120 },
    { nome: "Inglês Instrumental", presenca: 71, total: 97 },
    { nome: "Estrutura de Dados", presenca: 90, total: 115 },
    { nome: "Engenharia de Software", presenca: 65, total: 120 },
    { nome: "Programação WEB", presenca: 85, total: 120 },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
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
            <Text style={styles.summaryValue}>79.2%</Text>
          </View>
          <View style={styles.iconCircle}>
            <Ionicons name="trending-up" size={32} color={Colors.brand.primary} />
          </View>
        </View>

        <Text style={styles.sectionTitle}>Disciplinas</Text>

        {frequencias.map((item, index) => {
          const isLow = item.presenca < 75;
          return (
            <View style={styles.card} key={index}>
              <View style={styles.cardHeader}>
                <Text style={styles.subjectName}>{item.nome}</Text>
                <Text style={[styles.percentageText, isLow && { color: Colors.brand.error }]}>
                  {item.presenca}%
                </Text>
              </View>

              <View style={styles.progressBarBg}>
                <View 
                  style={[
                    styles.progressBarFill, 
                    { width: `${item.presenca}%` },
                    isLow && { backgroundColor: Colors.brand.error }
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
                  <Text style={styles.footerValue}>{Math.round((item.total * item.presenca) / 100)}</Text>
                </View>
                <View style={styles.footerItem}>
                  <Text style={styles.footerLabel}>Faltas</Text>
                  <Text style={[styles.footerValue, isLow && { color: Colors.brand.error }]}>
                    {item.total - Math.round((item.total * item.presenca) / 100)}
                  </Text>
                </View>
              </View>
            </View>
          );
        })}

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
  percentageText: { color: "#22C55E", fontSize: 18, fontWeight: "800" },
  progressBarBg: { height: 8, backgroundColor: "rgba(255,255,255,0.05)", borderRadius: 4, overflow: "hidden", marginBottom: 16 },
  progressBarFill: { height: "100%", backgroundColor: "#22C55E", borderRadius: 4 },
  cardFooter: { flexDirection: "row", justifyContent: "space-between", borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.05)", paddingTop: 16 },
  footerItem: { alignItems: "center" },
  footerLabel: { color: Colors.brand.textSecondary, fontSize: 10, fontWeight: "600", textTransform: "uppercase", marginBottom: 4 },
  footerValue: { color: "#fff", fontSize: 14, fontWeight: "700" },
});
