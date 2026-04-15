import { View, ActivityIndicator } from "react-native";

export default function Index() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <ActivityIndicator size="large" color="#5B3EFF" />
    </View>
  );
}