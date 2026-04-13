import { Ionicons, Feather } from "@expo/vector-icons";
import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
} from "react-native";

export default function Frequencia() {
  return (
    <View style={styles.container}>
      {/* HEADER */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Suas frequências</Text>
        <Ionicons name="notifications-outline" size={22} color="#fff" />
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* ALUNO */}
        <View style={styles.studentCard}>
          <Text style={styles.studentName}>Marcos da Silva</Text>
          <Text style={styles.studentRA}>RA: 12345678</Text>
        </View>

        {/* CARDS */}
        {[
          { nome: "Calculo 1", presenca: "85%", falta: "15%", total: "120" },
          { nome: "Ingles", presenca: "71%", falta: "29%", total: "97" },
          { nome: "Estrutura de dados", presenca: "90%", falta: "10%", total: "115" },
          { nome: "Engenharia de Software", presenca: "65%", falta: "35%", total: "120" },
          { nome: "Programação WEB", presenca: "85%", falta: "15%", total: "120"},
        ].map((item, index) => (
          <View style={styles.card} key={index}>
            <Text style={styles.subject}>{item.nome}</Text>

            <View style={styles.row}>
              <View>
                <Text style={styles.label}>Presença</Text>
                <Text style={styles.green}>{item.presenca}</Text>
              </View>

              <View>
                <Text style={styles.label}>Ausencias</Text>
                <Text style={styles.red}>{item.falta}</Text>
              </View>

              <View>
                <Text style={styles.label}>Total de aulas</Text>
                <Text style={styles.white}>{item.total}</Text>
              </View>
            </View>
          </View>
        ))}

        <View style={{ height: 120 }} />
      </ScrollView>

      <View style={styles.bottomMenu}>
        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="home" size={22} color="#7C4DFF" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="stats-chart-outline" size={22} color="#aaa" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="calendar-outline" size={22} color="#aaa" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="person-outline" size={22} color="#aaa" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#E9EAEC",
  },

  header: {
    backgroundColor: "#5B3EFF",
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
    fontSize: 18,
    fontWeight: "700",
  },

  scrollContent: {
    paddingBottom: 20,
  },

  studentCard: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginTop: 20,
    borderRadius: 16,
    paddingVertical: 22,
    paddingHorizontal: 16,
  },

  studentName: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },

  studentRA: {
    color: "#9CA3AF",
    marginTop: 6,
    fontSize: 14,
  },

  card: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginTop: 18,
    borderRadius: 18,
    padding: 18,
  },

  subject: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 12,
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  label: {
    color: "#9CA3AF",
    fontSize: 12,
    marginBottom: 4,
  },

  green: {
    color: "#22C55E",
    fontSize: 16,
    fontWeight: "700",
  },

  red: {
    color: "#EF4444",
    fontSize: 16,
    fontWeight: "700",
  },

  white: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },

  /* MENU */
  bottomMenu: {
    position: "absolute",
    bottom: 15,
    left: 15,
    right: 15,
    height: 65,
    backgroundColor: "#111",
    borderRadius: 20, // 🔥 arredondado
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",

    // sombra
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 10,
  },

  menuItem: {
    alignItems: "center",
    justifyContent: "center",
  },
});