import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

export default function AulasDoDia() {
  const router = useRouter();

  const aulas = [
    {
      id: 1,
      nome: "ADS 2°",
      horario: "09:00 - 10:30",
      sala: "Lab 03",
      status: "agora",
    },
    {
      id: 2,
      nome: "COMEX 1°",
      horario: "10:30 - 11:25",
      sala: "Lab 07",
      status: "proxima",
    },
    {
      id: 3,
      nome: "GPI 1°",
      horario: "11:25 - 12:30",
      sala: "Sala 9",
      status: "proxima",
    },
    {
      id: 4,
      nome: "ADS 4°",
      horario: "12:30 - 13:10",
      sala: "Lab 05",
      status: "proxima",
    },
    {
      id: 5,
      nome: "COMEX 2°",
      horario: "16:00 - 17:30",
      sala: "Sala 15",
      status: "proxima",
    },
    
  ];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.headerTitle}>Aulas de hoje</Text>

        <View style={{ width: 22 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {aulas.map((aula) => (
          <View style={styles.card} key={aula.id}>
            {aula.status === "agora" && (
              <View style={styles.liveContainer}>
                <View style={styles.liveDot} />
                <Text style={styles.liveText}>Em andamento</Text>
              </View>
            )}

            <Text style={styles.className}>{aula.nome}</Text>

            <Text style={styles.info}>
              {aula.horario} • {aula.sala}
            </Text>

            <TouchableOpacity
              style={styles.button}
              onPress={() =>
                router.push({
                  pathname: "/professor/lista-presencas",
                  params: { turma: aula.nome },
                })
              }
            >
              <Text style={styles.buttonText}>Abrir chamada</Text>
            </TouchableOpacity>
          </View>
        ))}

        <View style={{ height: 120 }} />
      </ScrollView>
      
      <View style={styles.bottomMenu}>
        <TouchableOpacity onPress={() => router.replace("/professor/home")}>
          <Ionicons name="home-outline" size={22} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/professor/turmas")}>
          <Ionicons name="clipboard-outline" size={22} color="#aaa" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/professor/horarios-turmas")}>
          <Ionicons name="calendar-outline" size={22} color="#7C4DFF" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push("/professor/perfil")}>
          <Ionicons name="person-outline" size={22} color="#aaa" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#E9EAEC" },

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

  headerTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },

  card: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginTop: 18,
    borderRadius: 16,
    padding: 16,
  },

  className: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "700",
  },

  info: {
    color: "#9CA3AF",
    marginTop: 6,
    marginBottom: 12,
  },

  button: {
    backgroundColor: "#5B3EFF",
    paddingVertical: 8,
    borderRadius: 20,
    alignItems: "center",
  },

  buttonText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "600",
  },

  liveContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },

  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#22C55E",
    marginRight: 6,
  },

  liveText: {
    color: "#22C55E",
    fontSize: 12,
    fontWeight: "600",
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