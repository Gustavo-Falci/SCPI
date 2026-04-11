import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
} from "react-native";

export default function Horarios() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      
      {/* HEADER */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={22} color="#fff" />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>Horarios de aula</Text>
        </View>

        <Ionicons name="calendar-outline" size={22} color="#fff" />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>

        {/* TOP CARD */}
        <View style={styles.todayCard}>
          <Text style={styles.todayTitle}>Aulas de hoje</Text>
          <Text style={styles.todayDate}>Segunda, 15 de abril</Text>
        </View>

        {/* CARD 1 */}
        <View style={styles.classCard}>
          <View style={styles.timeBox}>
            <Text style={styles.timeText}>8:00</Text>
            <Text style={styles.timeText}>AM</Text>
          </View>

          <View style={styles.classInfo}>
            <Text style={styles.className}>Engenharia de software 1</Text>
            <Text style={styles.room}>Sala 02</Text>

            <View style={styles.statusRow}>
              <View style={styles.timeTag}>
                <Text style={styles.timeTagText}>8:00–9:30</Text>
              </View>

              <View style={styles.activeTag}>
                <Text style={styles.activeText}>Em andamento</Text>
              </View>
            </View>
          </View>
        </View>

        {/* CARD 2 */}
        <View style={styles.classCard}>
          <View style={styles.timeBox}>
            <Text style={styles.timeText}>10:00</Text>
            <Text style={styles.timeText}>AM</Text>
          </View>

          <View style={styles.classInfo}>
            <Text style={styles.className}>Calculo 2</Text>
            <Text style={styles.room}>Sala 05</Text>

            <View style={styles.statusRow}>
              <View style={styles.timeTag}>
                <Text style={styles.timeTagText}>10:00–11:30</Text>
              </View>

              <View style={styles.waitTag}>
                <Text style={styles.waitText}>Aguardando inicio</Text>
              </View>
            </View>
          </View>
        </View>

        {/* CARD 3 */}
        <View style={styles.classCard}>
          <View style={styles.timeBox}>
            <Text style={styles.timeText}>1:00</Text>
            <Text style={styles.timeText}>PM</Text>
          </View>

          <View style={styles.classInfo}>
            <Text style={styles.className}>Estrutura de dados</Text>
            <Text style={styles.room}>Lab 03</Text>

            <View style={styles.statusRow}>
              <View style={styles.timeTag}>
                <Text style={styles.timeTagText}>1:00–2:30</Text>
              </View>

              <View style={styles.waitTag}>
                <Text style={styles.waitText}>Aguardando inicio</Text>
              </View>
            </View>
          </View>
        </View>

        {/* CARD 4 */}
        <View style={styles.classCard}>
          <View style={styles.timeBox}>
            <Text style={styles.timeText}>3:00</Text>
            <Text style={styles.timeText}>PM</Text>
          </View>

          <View style={styles.classInfo}>
            <Text style={styles.className}>Ingles</Text>
            <Text style={styles.room}>Sala 09</Text>

            <View style={styles.statusRow}>
              <View style={styles.timeTag}>
                <Text style={styles.timeTagText}>3:00–4:30</Text>
              </View>

              <View style={styles.waitTag}>
                <Text style={styles.waitText}>Aguardando inicio</Text>
              </View>
            </View>
          </View>
        </View>

        {/* CARD 5 */}
        <View style={styles.classCard}>
          <View style={styles.timeBox}>
            <Text style={styles.timeText}>5:00</Text>
            <Text style={styles.timeText}>PM</Text>
          </View>

          <View style={styles.classInfo}>
            <Text style={styles.className}>Programação Linear</Text>
            <Text style={styles.room}>Lab 07</Text>

            <View style={styles.statusRow}>
              <View style={styles.timeTag}>
                <Text style={styles.timeTagText}>5:00–6:30</Text>
              </View>

              <View style={styles.waitTag}>
                <Text style={styles.waitText}>Aguardando inicio</Text>
              </View>
            </View>
          </View>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>

      {/* MENU INFERIOR */}
      <View style={styles.bottomMenu}>
        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="home-outline" size={24} color="#9CA3AF" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="clipboard-outline" size={24} color="#9CA3AF" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="people-outline" size={24} color="#9CA3AF" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem}>
          <Ionicons name="person-outline" size={24} color="#9CA3AF" />
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

  todayCard: {
    backgroundColor: "#111",
    margin: 20,
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    justifyContent: "space-between",
  },

  todayTitle: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },

  todayDate: {
    color: "#9CA3AF",
  },

  classCard: {
    backgroundColor: "#111",
    marginHorizontal: 20,
    marginBottom: 14,
    borderRadius: 16,
    padding: 16,
    flexDirection: "row",
  },

  timeBox: {
    backgroundColor: "#2C1E7A",
    borderRadius: 10,
    padding: 10,
    width: 65,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 14,
  },

  timeText: {
    color: "#8B7CFF",
    fontWeight: "700",
  },

  classInfo: {
    flex: 1,
  },

  className: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },

  room: {
    color: "#9CA3AF",
    marginTop: 2,
  },

  statusRow: {
    flexDirection: "row",
    marginTop: 8,
    gap: 8,
  },

  timeTag: {
    backgroundColor: "#3B1F15",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },

  timeTagText: {
    color: "#F59E0B",
    fontSize: 12,
  },

  activeTag: {
    backgroundColor: "#134E4A",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },

  activeText: {
    color: "#34D399",
    fontSize: 12,
  },

  waitTag: {
    backgroundColor: "#3F3F46",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },

  waitText: {
    color: "#D4D4D8",
    fontSize: 12,
  },

  bottomMenu: {
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    backgroundColor: "#0B0B0B",
    height: 75,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
  },

  menuItem: {
    alignItems: "center",
    justifyContent: "center",
  },

});