import React from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  StyleSheet 
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { Colors } from '../../constants/theme';

interface DashboardHeaderProps {
  greeting: string;
  userName: string;
  onLogout: () => void;
}

export const DashboardHeader = ({ greeting, userName, onLogout }: DashboardHeaderProps) => {
  return (
    <View style={styles.header}>
      <View>
        <Text style={styles.greetingText}>{greeting}</Text>
        <Text style={styles.userName}>{userName}</Text>
      </View>
      <TouchableOpacity style={styles.logoutBtn} onPress={onLogout}>
        <Feather name="log-out" size={20} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingVertical: 20,
  },
  greetingText: {
    color: Colors.brand.textSecondary,
    fontSize: 16,
  },
  userName: {
    color: Colors.brand.text,
    fontSize: 24,
    fontWeight: "800",
  },
  logoutBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.brand.card,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
});
