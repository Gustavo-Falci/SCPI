import { View, ActivityIndicator, StyleSheet, StatusBar } from "react-native";
import { Colors } from "../constants/theme";

export default function Index() {
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ActivityIndicator size="large" color={Colors.brand.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.brand.background,
    justifyContent: 'center',
    alignItems: 'center'
  }
});
