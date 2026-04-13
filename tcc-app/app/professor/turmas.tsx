import { Feather, Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

export default function Turmas() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={22} color="#fff" />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>Minhas turmas</Text>
        </View>

        <Ionicons name="notifications-outline" size={22} color="#fff" />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.searchBox}>
          <Ionicons name="search-outline" size={18} color="#9CA3AF" />
          <TextInput
            placeholder="Buscar turmas..."
            placeholderTextColor="#9CA3AF"
            style={styles.input}
          />
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Turmas</Text>
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.className}>ADS 2º</Text>

            <View style={styles.time}>
              <Ionicons name="time-outline" size={14} color="#5B3EFF" />
              <Text style={styles.timeText}>9:00 AM</Text>
            </View>
          </View>

          <Text style={styles.classInfo}>Sala 2 • 28 Estudantes</Text>

          <TouchableOpacity
            style={styles.button}
            onPress={() =>
              router.push({
                pathname: "/professor/lista-presencas",
                params: { turma: "ADS 2º" },
              })
            }
          >
            <Feather name="user-check" size={16} color="#5B3EFF" />
            <Text style={styles.buttonText}>Lista de presença</Text>
          </TouchableOpacity>
        </View>

        {/* CARD 2 */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.className}>COMEX 1º</Text>

            <View style={styles.time}>
              <Ionicons name="time-outline" size={14} color="#5B3EFF" />
              <Text style={styles.timeText}>11:30 AM</Text>
            </View>
          </View>

          <Text style={styles.classInfo}>Sala 3 • 24 Estudantes</Text>

          <TouchableOpacity
            style={styles.button}
            onPress={() =>
              router.push({
                pathname: "/professor/lista-presencas",
                params: { turma: "COMEX 1°" },
              })
            }
          >
            <Feather name="user-check" size={16} color="#5B3EFF" />
            <Text style={styles.buttonText}>Lista de presença</Text>
          </TouchableOpacity>
        </View>

        {/* CARD 3 */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.className}>ADS 4º</Text>

            <View style={styles.time}>
              <Ionicons name="time-outline" size={14} color="#5B3EFF" />
              <Text style={styles.timeText}>2:15 PM</Text>
            </View>
          </View>

          <Text style={styles.classInfo}>Lab 1 • 35 Estudantes</Text>

          <TouchableOpacity
            style={styles.button}
            onPress={() =>
              router.push({
                pathname: "/professor/lista-presencas",
                params: { turma: "ADS 4º" },
              })
            }
          >
            <Feather name="user-check" size={16} color="#5B3EFF" />
            <Text style={styles.buttonText}>Lista de presença</Text>
          </TouchableOpacity>
        </View>

        {/* CARD 4 */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.className}>GPI 1º</Text>

            <View style={styles.time}>
              <Ionicons name="time-outline" size={14} color="#5B3EFF" />
              <Text style={styles.timeText}>3:15 PM</Text>
            </View>
          </View>

          <Text style={styles.classInfo}>Lab 4 • 30 Estudantes</Text>

          <TouchableOpacity
            style={styles.button}
            onPress={() =>
              router.push({
                pathname: "/professor/lista-presencas",
                params: { turma: "GPI 1º" },
              })
            }
          >
            <Feather name="user-check" size={16} color="#5B3EFF" />
            <Text style={styles.buttonText}>Lista de presença</Text>
          </TouchableOpacity>
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

            <View style={styles.bottomMenu}>
              <Ionicons name="home-outline" size={22} color="#aaa" />
              <Ionicons name="clipboard-outline" size={22} color="#7C4DFF" />
              <Ionicons name="calendar-outline" size={22} color="#aaa" />
              <Ionicons name="person-outline" size={22} color="#aaa" />
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
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
  },

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  headerTitle: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "700",
  },

  searchBox: {
    marginTop: 20,
    marginHorizontal: 20,
    backgroundColor: "#F3F4F6",
    borderRadius: 12,
    height: 44,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
  },

  input: {
    marginLeft: 8,
    flex: 1,
    fontSize: 14,
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginHorizontal: 20,
    marginTop: 30,
    marginBottom: 20,
  },

  sectionTitle: {
    fontSize: 28,
    fontWeight: "600",
  },

  day: {
    color: "#6B7280",
    fontSize: 13,
  },

  card: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginTop: 14,
    borderRadius: 16,
    padding: 16,
  },

  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  className: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },

  classInfo: {
    color: "#9CA3AF",
    marginTop: 4,
    marginBottom: 12,
  },

  time: {
    backgroundColor: "#EEF2FF",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },

  timeText: {
    marginLeft: 4,
    fontSize: 12,
    color: "#5B3EFF",
    fontWeight: "600",
  },

  button: {
    backgroundColor: "#F3F4F6",
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  buttonText: {
    marginLeft: 6,
    color: "#5B3EFF",
    fontSize: 13,
    fontWeight: "500",
  },

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