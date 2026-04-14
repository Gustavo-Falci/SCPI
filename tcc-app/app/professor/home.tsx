import React, { useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Animated,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Feather, Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useState, useCallback } from "react";
import { useRouter, useFocusEffect } from "expo-router";
import { Alert, TouchableOpacity } from "react-native";

import { storage } from "../../services/storage";
import { apiGet } from "../../services/api";

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
      console.error("Erro ao carregar dashboard:", err);
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
        Animated.timing(pulseAnim, {
          toValue: 1.4,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <LinearGradient
        colors={["#5B3EFF", "#4B2FD6"]}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>Olá, {data?.nome?.split(' ')[0] || 'Professor'}</Text>

        <TouchableOpacity
          style={styles.bellContainer}
          onPress={async () => {
            await storage.removeItem('access_token');
            await storage.removeItem('user_role');
            router.replace('/auth/login');
          }}
        >
          <Feather name="log-out" size={18} color="#fff" />
        </TouchableOpacity>
      </LinearGradient>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* CARD PRINCIPAL */}
        <TouchableOpacity onPress={() => router.push("/professor/turmas")}>
          <LinearGradient
            colors={["#5B3EFF", "#4B2FD6"]}
            style={styles.bigCard}
          >
            <MaterialCommunityIcons
              name="clipboard-check-outline"
              size={26}
              color="#fff"
            />
            <Text style={styles.bigCardTitle}>Abrir chamada</Text>
            <Text style={styles.bigCardSubtitle}>
              Inicie a chamada com reconhecimento facial
            </Text>
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.push("/professor/turmas")}>
          <LinearGradient
            colors={["#000000", "#000000"]}
            style={styles.bigCard}
          >
            <Ionicons name="people-outline" size={26} color="#7C4DFF" />
            <Text style={styles.bigCardTitle}>Minhas Turmas</Text>
            <Text style={styles.bigCardSubtitle}>
              Gerencie suas turmas.
            </Text>
          </LinearGradient>
        </TouchableOpacity>

        <View style={styles.divider} />

        {/* AULAS DE HOJE */}
        <View style={styles.todayCard}>
          <View style={styles.todayHeader}>
            <Text style={styles.todayTitle}>Aulas de hoje</Text>
            <TouchableOpacity onPress={() => router.push("/professor/horarios-turmas")}>
              <Text style={styles.seeAll}>Ver tudo</Text>
            </TouchableOpacity>
          </View>

          {data?.aulas_hoje?.map((aula: any) => (
            <View style={styles.classItem} key={aula.id}>
              <Text style={styles.classTitle}>{aula.nome}</Text>
              <Text style={styles.classTime}>
                {aula.horario} • {aula.sala}
              </Text>
            </View>
          ))}
          {(!data?.aulas_hoje || data.aulas_hoje.length === 0) && (
             <Text style={{color: '#aaa'}}>Nenhuma aula agendada.</Text>
          )}
        </View>

        {/* 🔴 AULA EM ANDAMENTO / ÚLTIMA CHAMADA */}
        <View style={styles.currentClassCard}>
          <View style={styles.liveIndicator}>
            <Animated.View
              style={[
                styles.liveDot,
                { transform: [{ scale: pulseAnim }] },
              ]}
            />
            <Text style={styles.liveText}>Estatísticas da Chamada</Text>
          </View>

          <Text style={styles.currentSubject}>
            {data?.estatisticas?.disciplina || 'Sem dados'}
          </Text>

          <View style={styles.presenceContainer}>
            <Text style={styles.presenceText}>
              👥 {data?.estatisticas?.total || 0} alunos
            </Text>
            <Text style={styles.presentText}>
              ✅ {data?.estatisticas?.presentes || 0} presentes
            </Text>
            <Text style={styles.absentText}>
              ❌ {data?.estatisticas?.ausentes || 0} ausentes
            </Text>
          </View>
        </View>

        <View style={{ height: 90 }} />
      </ScrollView>

      <View style={styles.bottomMenu}>
          <Ionicons name="home-outline" size={22} color="#7C4DFF" />
          <Ionicons name="clipboard-outline" size={22} color="#aaa" />
          <Ionicons name="calendar-outline" size={22} color="#aaa" />
          <Ionicons name="person-outline" size={22} color="#aaa" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F2F2F2" },

  header: {
    paddingTop: 60,
    paddingBottom: 28,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  headerTitle: { color: "#fff", fontSize: 20, fontWeight: "700" },

  bellContainer: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "rgba(255,255,255,0.25)",
    justifyContent: "center",
    alignItems: "center",
  },

  content: { paddingHorizontal: 20, paddingTop: 20 },

  bigCard: { borderRadius: 16, padding: 20, marginBottom: 22 },

  bigCardTitle: {
    color: "#fff",
    fontSize: 17,
    fontWeight: "700",
    marginTop: 10,
  },

  bigCardSubtitle: { color: "#E0E0E0", fontSize: 12, marginTop: 4 },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 22,
  },

  smallCard: {
    width: "48%",
    backgroundColor: "#111",
    borderRadius: 16,
    padding: 16,
  },

  smallCardTitle: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
    marginTop: 10,
  },

  smallCardText: { color: "#aaa", fontSize: 11, marginTop: 4 },

  divider: {
    height: 1,
    backgroundColor: "#D9D9D9",
    marginBottom: 22,
  },

  todayCard: {
    backgroundColor: "#111",
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
  },

  todayHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
  },

  todayTitle: { color: "#fff", fontSize: 16, fontWeight: "700" },

  seeAll: { color: "#5B3EFF", fontSize: 12 },

  classItem: { marginBottom: 12 },

  classTitle: { color: "#fff", fontSize: 14, fontWeight: "600" },

  classTime: { color: "#aaa", fontSize: 11, marginTop: 2 },

  currentClassCard: {
    backgroundColor: "#111",
    borderRadius: 16,
    padding: 16,
  },

  liveIndicator: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },

  liveDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#1DB954",
    marginRight: 8,
  },

  liveText: {
    color: "#1DB954",
    fontSize: 14,
    fontWeight: "700",
  },

  currentSubject: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },

  currentTime: {
    color: "#aaa",
    fontSize: 12,
    marginTop: 4,
    marginBottom: 12,
  },

  presenceContainer: {
    gap: 6,
  },

  presenceText: { color: "#fff", fontSize: 13 },

  presentText: { color: "#1DB954", fontSize: 13 },

  absentText: { color: "#FF3B30", fontSize: 13 },

  bottomMenu: {
    position: "absolute",
    bottom: 15,
    left: 15,
    right: 15,
    height: 65,
    backgroundColor: "#111",
    borderRadius: 20,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
  },
});