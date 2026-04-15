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
import { TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

import { storage } from "../../services/storage";
import { apiGet } from "../../services/api";
import { useState, useCallback } from "react";
import { useFocusEffect } from "expo-router";

export default function HomeAluno() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

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

  const handleLogout = async () => {
    try {
      await storage.removeItem('access_token');
      await storage.removeItem('user_role');
      await storage.removeItem('user_id');
      await storage.removeItem('user_name');
    } catch (e) {
      console.error("Erro logout aluno:", e);
    }
    router.replace('/auth/login');
  };

  const pulseAnim = useRef(new Animated.Value(1)).current;

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
        <Text style={styles.headerTitle}>Olá, {data?.nome?.split(' ')[0] || 'Aluno'}</Text>

        <TouchableOpacity
          style={styles.bellContainer}
          onPress={handleLogout}
        >
          <Feather name="log-out" size={18} color="#fff" />
        </TouchableOpacity>
      </LinearGradient>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* CADASTRAR FACE */}
        <TouchableOpacity onPress={() => router.push("/aluno/cadastro-facial")}>
        <LinearGradient
          colors={["#5B3EFF", "#4B2FD6"]}
          style={styles.bigCard}
        >
          <MaterialCommunityIcons
            name="face-recognition"
            size={26}
            color="#fff"
          />
          <Text style={styles.bigCardTitle}>Cadastrar face</Text>
          <Text style={styles.bigCardSubtitle}>
            Cadastre a face do aluno aqui!
          </Text>
        </LinearGradient>
        </TouchableOpacity>

        {/* DOIS CARDS */}
        <View style={styles.row}>
          <View style={styles.smallCard}>
            <Ionicons name="book-outline" size={24} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Frequências</Text>
            <Text style={styles.smallCardText}>
              Veja suas frequências nas aulas!
            </Text>
          </View>

          <View style={styles.smallCard}>
            <Ionicons name="calendar-outline" size={24} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Horários</Text>
            <Text style={styles.smallCardText}>
              Veja os horários de suas aulas!
            </Text>
          </View>
        </View>

        <View style={styles.divider} />

        {/* AULAS DE HOJE */}
        <View style={styles.todayCard}>
          <View style={styles.todayHeader}>
            <Text style={styles.todayTitle}>Aulas de hoje</Text>
            <TouchableOpacity onPress={() => router.push("/aluno/horarios")}>
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
             <Text style={{color: '#aaa'}}>Nenhuma aula hoje.</Text>
          )}
        </View>

        {/* 🔥 AULA EM ANDAMENTO AGORA EMBAIXO */}
        <View style={styles.currentClassCard}>
          <View style={styles.liveIndicator}>
            <Animated.View
              style={[
                styles.liveDot,
                { transform: [{ scale: pulseAnim }] },
              ]}
            />
            <Text style={styles.liveText}>Frequência Geral</Text>
          </View>

          <Text style={styles.currentSubject}>
            Média de presença em todas as disciplinas
          </Text>

          <Text style={styles.frequencyValue}>
            {data?.frequencia_geral || 0}%
          </Text>

          <View style={styles.frequencyBar}>
            <View
              style={[
                styles.frequencyFill,
                { width: `${data?.frequencia_geral || 0}%` },
              ]}
            />
          </View>
        </View>

        {/* Espaço extra para não ficar atrás do menu */}
        <View style={{ height: 90 }} />
      </ScrollView>

      {/* MENU RÁPIDO INFERIOR */}
      <View style={styles.bottomMenu}>
        <Ionicons name="home" size={24} color="#5B3EFF" />
        <Ionicons name="stats-chart-outline" size={24} color="#aaa" />
        <Ionicons name="calendar-outline" size={24} color="#aaa" />
        <Ionicons name="person-outline" size={24} color="#aaa" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F2F2F2",
  },
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
  headerTitle: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "700",
  },
  bellContainer: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "rgba(255,255,255,0.25)",
    justifyContent: "center",
    alignItems: "center",
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 20,
  },
  bigCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 22,
  },
  bigCardTitle: {
    color: "#fff",
    fontSize: 17,
    fontWeight: "700",
    marginTop: 10,
  },
  bigCardSubtitle: {
    color: "#E0E0E0",
    fontSize: 12,
    marginTop: 4,
  },
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
  smallCardText: {
    color: "#aaa",
    fontSize: 11,
    marginTop: 4,
  },
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
  todayTitle: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  seeAll: {
    color: "#5B3EFF",
    fontSize: 12,
    fontWeight: "500",
  },
  classItem: {
    marginBottom: 12,
  },
  classTitle: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  classTime: {
    color: "#aaa",
    fontSize: 11,
    marginTop: 2,
  },
  currentClassCard: {
    backgroundColor: "#111",
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
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
  frequencyLabel: {
    color: "#aaa",
    fontSize: 12,
  },
  frequencyValue: {
    color: "#1DB954",
    fontSize: 22,
    fontWeight: "700",
    marginTop: 4,
  },
  frequencyBar: {
    height: 6,
    backgroundColor: "#333",
    borderRadius: 4,
    marginTop: 8,
  },
  frequencyFill: {
    height: 6,
    backgroundColor: "#1DB954",
    borderRadius: 4,
  },
  bottomMenu: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    height: 70,
    backgroundColor: "#111",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: "#222",
  },
});