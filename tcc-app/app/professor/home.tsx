import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Feather, Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";

export default function HomeProfessor() {
  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#5B3EFF", "#4B2FD6"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>Portal do Professor</Text>
        <View style={styles.bellContainer}>
          <Feather name="bell" size={18} color="#fff" />
        </View>
      </LinearGradient>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <LinearGradient
          colors={["#5B3EFF", "#4B2FD6"]}
          style={styles.bigCard}
        >
          <MaterialCommunityIcons name="face-recognition" size={26} color="#fff" />
          <Text style={styles.bigCardTitle}>Registrar presença</Text>
          <Text style={styles.bigCardSubtitle}>
            Inicie a captura facial da turma.
          </Text>
        </LinearGradient>

        <View style={styles.row}>
          <View style={styles.smallCard}>
            <Ionicons name="people" size={24} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Minhas Turmas</Text>
            <Text style={styles.smallCardText}>
              Veja suas turmas cadastradas.
            </Text>
          </View>

          <View style={styles.smallCard}>
            <Ionicons name="calendar" size={24} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Horários</Text>
            <Text style={styles.smallCardText}>
              Veja seus horários de aula.
            </Text>
          </View>
        </View>

        <View style={styles.divider} />

        <View style={styles.todayCard}>
          <View style={styles.todayHeader}>
            <Text style={styles.todayTitle}>Aulas de hoje</Text>
            <Text style={styles.seeAll}>Ver tudo</Text>
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
              12:40 PM - 13:35 PM - Sala 305
            </Text>
          </View>
        </View>
      </ScrollView>
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
    paddingBottom: 40,
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
});