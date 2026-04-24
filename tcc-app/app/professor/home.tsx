import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Animated,
  TouchableOpacity,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter, useFocusEffect } from "expo-router";

import { storage } from "../../services/storage";
import { apiGet } from "../../services/api";
import { Colors } from "../../constants/theme";
import { DashboardHeader } from "../../components/layout/dashboard-header";
import { FloatingMenu } from "../../components/layout/floating-menu";

export default function HomeProfessor() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const loadDashboard = async () => {
    try {
      const userId = await storage.getItem("user_id");
      if (!userId) {
        router.replace("/auth/login");
        return;
      }
      const resp = await apiGet(`/professor/dashboard/${userId}`);
      setData(resp);
    } catch (err) {
      console.error("Erro ao carregar dashboard professor:", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadDashboard();
    }, [])
  );

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.2, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const handleLogout = async () => {
    await storage.clear();
    router.replace('/auth/login');
  };

  const menuItems: any[] = [
    { icon: 'home-outline', activeIcon: 'home', route: '/professor/home', label: 'Início' },
    { icon: 'clipboard-outline', activeIcon: 'clipboard', route: '/professor/turmas', label: 'Turmas' },
    { icon: 'document-text-outline', activeIcon: 'document-text', route: '/professor/relatorios', label: 'Relatórios' },
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
      
      <DashboardHeader 
        greeting="Bem-vindo, Prof." 
        userName={data?.nome?.split(' ')[0] || 'Professor'} 
        onLogout={handleLogout} 
      />

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <TouchableOpacity 
          activeOpacity={0.9}
          onPress={() => router.push("/professor/iniciar-chamada")}
        >
          <LinearGradient
            colors={[Colors.brand.primary, Colors.brand.secondary]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.mainActionCard}
          >
            <View style={styles.actionCardContent}>
              <View style={{ flex: 1 }}>
                <Text style={styles.actionCardTitle}>Iniciar Chamada</Text>
                <Text style={styles.actionCardSubtitle}>
                  Abra a frequência facial para seus alunos agora
                </Text>
              </View>
              <View style={styles.actionIconContainer}>
                <MaterialCommunityIcons name="face-recognition" size={32} color="#fff" />
              </View>
            </View>
          </LinearGradient>
        </TouchableOpacity>

        <View style={styles.sectionContainer}>
          <Text style={[styles.sectionTitle, { marginBottom: 16 }]}>Resumo da Última Chamada</Text>
          <View style={styles.statsRow}>
             <View style={styles.statItem}>
                <Text style={styles.statValue}>{data?.estatisticas?.total || 0}</Text>
                <Text style={styles.statLabel}>Alunos</Text>
             </View>
             <View style={[styles.statItem, { borderColor: 'rgba(29, 185, 84, 0.3)' }]}>
                <Text style={[styles.statValue, { color: '#1DB954' }]}>{data?.estatisticas?.presentes || 0}</Text>
                <Text style={styles.statLabel}>Presentes</Text>
             </View>
             <View style={[styles.statItem, { borderColor: 'rgba(255, 75, 75, 0.3)' }]}>
                <Text style={[styles.statValue, { color: '#FF4B4B' }]}>{data?.estatisticas?.ausentes || 0}</Text>
                <Text style={styles.statLabel}>Ausentes</Text>
             </View>
          </View>
        </View>

        <View style={styles.sectionContainer}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Aulas de Hoje</Text>
            <TouchableOpacity onPress={() => router.push("/professor/horarios-turmas")} activeOpacity={0.7} accessibilityRole="button" accessibilityLabel="Ver todas as aulas">
              <Text style={styles.seeAllText}>Ver todas</Text>
            </TouchableOpacity>
          </View>

          {data?.aulas_hoje && data.aulas_hoje.length > 0 ? (
            data.aulas_hoje.map((aula: any, index: number) => (
              <TouchableOpacity
                key={index}
                style={styles.classCard}
                activeOpacity={0.7}
                accessibilityRole="button"
                accessibilityLabel={`Ver turma ${aula.nome}`}
                onPress={() => router.push("/professor/turmas")}
              >
                <View style={styles.classInfo}>
                  <Text style={styles.className}>{aula.nome}</Text>
                  <View style={styles.classMetaRow}>
                    <Ionicons name="time-outline" size={14} color={Colors.brand.textSecondary} />
                    <Text style={styles.classMetaText}>{aula.horario}</Text>
                    <Ionicons name="location-outline" size={14} color={Colors.brand.textSecondary} style={{ marginLeft: 8 }} />
                    <Text style={styles.classMetaText}>{aula.sala}</Text>
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={20} color={Colors.brand.textSecondary} />
              </TouchableOpacity>
            ))
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="calendar-outline" size={40} color={Colors.brand.textSecondary} />
              <Text style={styles.emptyText}>Sem aulas agendadas para hoje.</Text>
            </View>
          )}
        </View>

        <TouchableOpacity
          style={styles.secondaryCard}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Minhas turmas"
          onPress={() => router.push("/professor/turmas")}
        >
          <View style={[styles.iconCircle, { backgroundColor: 'rgba(75, 57, 239, 0.1)' }]}>
            <Ionicons name="people" size={24} color={Colors.brand.primary} />
          </View>
          <View style={{ flex: 1, marginLeft: 16 }}>
            <Text style={styles.secondaryCardTitle}>Minhas Turmas</Text>
            <Text style={styles.secondaryCardSubtitle}>Gerenciar listas e presenças</Text>
          </View>
          <Ionicons name="arrow-forward" size={20} color={Colors.brand.textSecondary} />
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.secondaryCard, { marginTop: 12 }]}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Relatórios de chamadas"
          onPress={() => router.push("/professor/relatorios")}
        >
          <View style={[styles.iconCircle, { backgroundColor: 'rgba(34, 197, 94, 0.1)' }]}>
            <Ionicons name="document-text" size={24} color="#22C55E" />
          </View>
          <View style={{ flex: 1, marginLeft: 16 }}>
            <Text style={styles.secondaryCardTitle}>Relatórios</Text>
            <Text style={styles.secondaryCardSubtitle}>Histórico de chamadas realizadas</Text>
          </View>
          <Ionicons name="arrow-forward" size={20} color={Colors.brand.textSecondary} />
        </TouchableOpacity>

        <View style={{ height: 120 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  center: { justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 24, paddingTop: 10 },
  mainActionCard: {
    borderRadius: 24, padding: 24, marginBottom: 32,
    elevation: 8, shadowColor: Colors.brand.primary,
    shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8,
  },
  actionCardContent: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  actionCardTitle: { color: "#fff", fontSize: 22, fontWeight: "800" },
  actionCardSubtitle: { color: "rgba(255,255,255,0.8)", fontSize: 14, marginTop: 6, paddingRight: 20 },
  actionIconContainer: { width: 56, height: 56, borderRadius: 28, backgroundColor: "rgba(255,255,255,0.2)", justifyContent: "center", alignItems: "center" },
  sectionContainer: { marginBottom: 32 },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  sectionTitle: { color: Colors.brand.text, fontSize: 18, fontWeight: "700" },
  seeAllText: { color: Colors.brand.primary, fontSize: 14, fontWeight: "600" },
  statsRow: { flexDirection: "row", gap: 12 },
  statItem: { flex: 1, backgroundColor: Colors.brand.card, borderRadius: 20, padding: 16, alignItems: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.05)" },
  statValue: { color: Colors.brand.text, fontSize: 22, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 4 },
  classCard: {
    backgroundColor: Colors.brand.card, borderRadius: 20, padding: 18,
    flexDirection: "row", alignItems: "center", marginBottom: 12,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  classInfo: { flex: 1 },
  className: { color: Colors.brand.text, fontSize: 16, fontWeight: "700" },
  classMetaRow: { flexDirection: "row", alignItems: "center", marginTop: 6, gap: 4 },
  classMetaText: { color: Colors.brand.textSecondary, fontSize: 12 },
  secondaryCard: {
    backgroundColor: Colors.brand.card, borderRadius: 24, padding: 20,
    flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  iconCircle: { width: 50, height: 50, borderRadius: 25, justifyContent: "center", alignItems: "center" },
  secondaryCardTitle: { color: Colors.brand.text, fontSize: 16, fontWeight: "700" },
  secondaryCardSubtitle: { color: Colors.brand.textSecondary, fontSize: 13, marginTop: 2 },
  emptyContainer: {
    alignItems: "center", paddingVertical: 30, backgroundColor: Colors.brand.card,
    borderRadius: 24, borderStyle: "dashed", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  emptyText: { color: Colors.brand.textSecondary, marginTop: 12, fontSize: 14 },
});
