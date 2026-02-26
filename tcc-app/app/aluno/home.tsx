import React from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Feather, Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";

export default function HomeAluno() {
  return (
    <View style={styles.container}>
      {/* HEADER */}
      <LinearGradient
        colors={["#5B3EFF", "#4B2FD6"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>Portal do Aluno</Text>

        <View style={styles.bellContainer}>
          <Feather name="bell" size={20} color="#fff" />
        </View>
      </LinearGradient>

      <ScrollView contentContainerStyle={styles.content}>
        {/* CARD GRANDE */}
        <LinearGradient
          colors={["#5B3EFF", "#4B2FD6"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.bigCard}
        >
          <MaterialCommunityIcons
            name="face-recognition"
            size={32}
            color="#fff"
          />
          <Text style={styles.bigCardTitle}>Cadastrar face</Text>
          <Text style={styles.bigCardSubtitle}>
            Cadastre a face do aluno aqui!
          </Text>
        </LinearGradient>

        {/* DOIS CARDS */}
        <View style={styles.row}>
          <View style={styles.smallCard}>
            <Ionicons name="book-outline" size={28} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Frequencias</Text>
            <Text style={styles.smallCardText}>
              Veja suas frequencias nas aulas!
            </Text>
          </View>

          <View style={styles.smallCard}>
            <Ionicons name="calendar-outline" size={28} color="#5B3EFF" />
            <Text style={styles.smallCardTitle}>Horarios de aulas</Text>
            <Text style={styles.smallCardText}>
              Veja os horarios de suas aulas!
            </Text>
          </View>
        </View>

        {/* DIVISOR */}
        <View style={styles.divider} />

        {/* AULAS DE HOJE */}
        <View style={styles.todayCard}>
          <View style={styles.todayHeader}>
            <Text style={styles.todayTitle}>Aulas de hoje</Text>
            <Text style={styles.seeAll}>Ver tudo</Text>
          </View>

          <View style={styles.classItem}>
            <Text style={styles.classTitle}>Matematica 1</Text>
            <Text style={styles.classTime}>
              09:00 AM - 10:30 AM - Sala 305
            </Text>
          </View>

          <View style={styles.classItem}>
            <Text style={styles.classTitle}>
              Engenharia de Software 2
            </Text>
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
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#E6E6E6",
  },

  header: {
    paddingTop: 60,
    paddingBottom: 25,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  headerTitle: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "600",
  },

  bellContainer: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
  },

  content: {
    padding: 20,
  },

  bigCard: {
    borderRadius: 15,
    padding: 20,
    marginBottom: 20,
  },

  bigCardTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
    marginTop: 10,
  },

  bigCardSubtitle: {
    color: "#E0E0E0",
    fontSize: 13,
    marginTop: 4,
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 20,
  },

  smallCard: {
    width: "48%",
    backgroundColor: "#111",
    borderRadius: 15,
    padding: 15,
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
    backgroundColor: "#bbb",
    marginVertical: 10,
  },

  todayCard: {
    backgroundColor: "#111",
    borderRadius: 15,
    padding: 15,
  },

  todayHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 15,
  },

  todayTitle: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },

  seeAll: {
    color: "#5B3EFF",
    fontSize: 13,
  },

  classItem: {
    marginBottom: 12,
  },

  classTitle: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "500",
  },

  classTime: {
    color: "#aaa",
    fontSize: 11,
    marginTop: 2,
  },
});