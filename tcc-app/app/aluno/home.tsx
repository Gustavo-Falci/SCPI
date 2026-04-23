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

function isAulaAgora(horario: string): boolean {
  if (!horario) return false;
  const parts = horario.split(' - ');
  if (parts.length !== 2) return false;

  const toMinutes = (hhmm: string): number => {
    const [h, m] = hhmm.trim().split(':').map(Number);
    if (isNaN(h) || isNaN(m)) return -1;
    return h * 60 + m;
  };

  const inicio = toMinutes(parts[0]);
  const fim = toMinutes(parts[1]);
  if (inicio === -1 || fim === -1) return false;

  const now = new Date();
  const agora = now.getHours() * 60 + now.getMinutes();

  return agora >= inicio && agora <= fim;
}

export default function HomeAluno() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const loadDashboard = async () => {
    try {
      const userId = await storage.getItem("user_id");
      if (!userId) {
        router.replace("/auth/login");
        return;
      }
      const resp = await apiGet(`/aluno/dashboard/${userId}`);
      setData(resp);
    } catch (err) {
      console.error("Erro ao carregar dashboard aluno:", err);
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
    await storage.clear(); // Limpa tudo por segurança
    router.replace('/auth/login');
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
      
      <DashboardHeader 
        greeting="Olá," 
        userName={data?.nome?.split(' ')[0] || 'Aluno'} 
        onLogout={handleLogout} 
      />

      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <TouchableOpacity 
          activeOpacity={0.9}
          onPress={() => router.push("/aluno/cadastro-facial")}
        >
          <LinearGradient
            colors={[Colors.brand.primary, Colors.brand.secondary]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.faceCard}
          >
            <View style={styles.faceCardContent}>
              <View>
                <Text style={styles.faceCardTitle}>Biometria Facial</Text>
                <Text style={styles.faceCardStatus}>
                  {data?.face_registrada ? "Atualize sua face quando quiser" : "Cadastre sua face agora"}
                </Text>
              </View>
              <MaterialCommunityIcons name="face-recognition" size={40} color="#fff" />
            </View>
          </LinearGradient>
        </TouchableOpacity>

        <View style={styles.statsRow}>
          <TouchableOpacity style={styles.statCard} activeOpacity={0.7} accessibilityRole="button" accessibilityLabel="Ver minha frequência" onPress={() => router.push("/aluno/frequencia")}>
            <View style={[styles.iconCircle, { backgroundColor: 'rgba(75, 57, 239, 0.1)' }]}>
              <Ionicons name="stats-chart" size={20} color={Colors.brand.primary} />
            </View>
            <Text style={styles.statValue}>{data?.frequencia_geral || 0}%</Text>
            <Text style={styles.statLabel}>Frequência</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.statCard} activeOpacity={0.7} accessibilityRole="button" accessibilityLabel="Ver meus horários" onPress={() => router.push("/aluno/horarios")}>
            <View style={[styles.iconCircle, { backgroundColor: 'rgba(29, 185, 84, 0.1)' }]}>
              <Ionicons name="calendar" size={20} color="#1DB954" />
            </View>
            <Text style={styles.statValue}>{data?.aulas_hoje?.length || 0}</Text>
            <Text style={styles.statLabel}>Aulas hoje</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.sectionContainer}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Aulas de Hoje</Text>
            <TouchableOpacity onPress={() => router.push("/aluno/horarios")} activeOpacity={0.7} accessibilityRole="button" accessibilityLabel="Ver todas as aulas">
              <Text style={styles.seeAllText}>Ver todas</Text>
            </TouchableOpacity>
          </View>

          {data?.aulas_hoje && data.aulas_hoje.length > 0 ? (
            data.aulas_hoje.map((aula: any, index: number) => (
              <View key={index} style={styles.classCard}>
                <View style={styles.classTimeContainer}>
                  <Text style={styles.classTimeText}>{aula.horario?.split(' - ')[0]}</Text>
                  <View style={styles.timeDivider} />
                  <Text style={styles.classTimeTextEnd}>{aula.horario?.split(' - ')[1]}</Text>
                </View>
                <View style={styles.classInfo}>
                  <Text style={styles.className}>{aula.nome}</Text>
                  <View style={styles.classRoomRow}>
                    <Ionicons name="location-outline" size={14} color={Colors.brand.textSecondary} />
                    <Text style={styles.classRoomText}>{aula.sala}</Text>
                  </View>
                </View>
                {isAulaAgora(aula.horario) && (
                   <View style={styles.liveBadge}>
                      <Animated.View style={[styles.liveDot, { transform: [{ scale: pulseAnim }] }]} />
                      <Text style={styles.liveText}>Agora</Text>
                   </View>
                )}
              </View>
            ))
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="cafe-outline" size={40} color={Colors.brand.textSecondary} />
              <Text style={styles.emptyText}>Nenhuma aula para hoje!</Text>
            </View>
          )}
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

      <FloatingMenu items={menuItems} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  center: { justifyContent: 'center', alignItems: 'center' },
  scrollContent: { paddingHorizontal: 24, paddingTop: 10 },
  faceCard: {
    borderRadius: 24, padding: 24, marginBottom: 24,
    elevation: 8, shadowColor: Colors.brand.primary,
    shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8,
  },
  faceCardContent: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  faceCardTitle: { color: "#fff", fontSize: 20, fontWeight: "800" },
  faceCardStatus: { color: "rgba(255,255,255,0.8)", fontSize: 14, marginTop: 4 },
  statsRow: { flexDirection: "row", gap: 16, marginBottom: 32 },
  statCard: {
    flex: 1, backgroundColor: Colors.brand.card, borderRadius: 20,
    padding: 16, alignItems: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  iconCircle: { width: 40, height: 40, borderRadius: 20, justifyContent: "center", alignItems: "center", marginBottom: 12 },
  statValue: { color: Colors.brand.text, fontSize: 20, fontWeight: "800" },
  statLabel: { color: Colors.brand.textSecondary, fontSize: 12, marginTop: 2 },
  sectionContainer: { marginBottom: 24 },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  sectionTitle: { color: Colors.brand.text, fontSize: 18, fontWeight: "700" },
  seeAllText: { color: Colors.brand.primary, fontSize: 14, fontWeight: "600" },
  classCard: {
    backgroundColor: Colors.brand.card, borderRadius: 20, padding: 16,
    flexDirection: "row", alignItems: "center", marginBottom: 12,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.05)",
  },
  classTimeContainer: { alignItems: "center", width: 60, borderRightWidth: 1, borderRightColor: "rgba(255,255,255,0.1)", paddingRight: 12 },
  classTimeText: { color: Colors.brand.text, fontSize: 13, fontWeight: "700" },
  classTimeTextEnd: { color: Colors.brand.textSecondary, fontSize: 11 },
  timeDivider: { height: 10, width: 1, backgroundColor: "rgba(255,255,255,0.1)", marginVertical: 2 },
  classInfo: { flex: 1, paddingLeft: 16 },
  className: { color: Colors.brand.text, fontSize: 15, fontWeight: "700" },
  classRoomRow: { flexDirection: "row", alignItems: "center", marginTop: 4, gap: 4 },
  classRoomText: { color: Colors.brand.textSecondary, fontSize: 12 },
  liveBadge: { flexDirection: "row", alignItems: "center", backgroundColor: "rgba(29, 185, 84, 0.15)", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, gap: 4 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#1DB954" },
  liveText: { color: "#1DB954", fontSize: 10, fontWeight: "800", textTransform: "uppercase" },
  emptyContainer: {
    alignItems: "center", paddingVertical: 40, backgroundColor: Colors.brand.card,
    borderRadius: 24, borderStyle: "dashed", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  emptyText: { color: Colors.brand.textSecondary, marginTop: 12, fontSize: 14 },
});
