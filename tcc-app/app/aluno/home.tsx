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

export default function HomeAluno() {
  const router = useRouter();
  const frequencia = 85;

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
      <TouchableOpacity onPress={() => router.push("/aluno/cadastro-facial")}>
        <LinearGradient
        colors={["#5B3EFF", "#4B2FD6"]}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>Portal do Aluno</Text>

        <View style={styles.bellContainer}>
          <Feather name="bell" size={18} color="#fff" />
        </View>
      </LinearGradient>
        </TouchableOpacity>

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
            <Text style={styles.seeAll}>Ver tudo</Text>
          </View>

          <View style={styles.classItem}>
            <Text style={styles.classTitle}>Matemática 1</Text>
            <Text style={styles.classTime}>
              09:00 AM - 10:30 AM - Sala 305
            </Text>
          </View>

          <View style={styles.classItem}>
            <Text style={styles.classTitle}>Engenharia de Software 2</Text>
            <Text style={styles.classTime}>
              11:00 AM - 12:30 PM - Lab 201
            </Text>
          </View>

          <View style={styles.classItem}>
            <Text style={styles.classTitle}>Estrutura de Dados</Text>
            <Text style={styles.classTime}>
              12:40 PM - 13:35 PM - Lab 205
            </Text>
          </View>
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
            <Text style={styles.liveText}>Aula em andamento</Text>
          </View>

          <Text style={styles.currentSubject}>
            Engenharia de Software 2
          </Text>

          <Text style={styles.currentTime}>
            11:00 - 12:30 • Lab 201
          </Text>

          <Text style={styles.frequencyLabel}>
            Frequência nesta aula
          </Text>

          <Text style={styles.frequencyValue}>
            {frequencia}%
          </Text>

          <View style={styles.frequencyBar}>
            <View
              style={[
                styles.frequencyFill,
                { width: `${frequencia}%` },
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