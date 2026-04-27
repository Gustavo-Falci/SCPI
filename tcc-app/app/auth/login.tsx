import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { storage } from "../../services/storage";
import { loginRequest } from "../../services/api";
import { registerForPushNotificationsAsync } from "../../services/notifications";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Colors } from "../../constants/theme";

const { height } = Dimensions.get("window");

export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async () => {
    if (!email || !senha) {
      Alert.alert("Erro", "Por favor, preencha todos os campos.");
      return;
    }

    setIsLoading(true);
    try {
      const resp = await loginRequest(email, senha);

      await storage.setItem("access_token", resp.access_token);
      await storage.setItem("refresh_token", resp.refresh_token);
      await storage.setItem("user_role", resp.user_role);
      await storage.setItem("user_id", resp.user_id);
      await storage.setItem("user_name", resp.user_name);
      await storage.setItem("user_email", resp.user_email);
      if (resp.user_ra) await storage.setItem("user_ra", resp.user_ra);
      await storage.setItem("primeiro_acesso", resp.primeiro_acesso ? "true" : "false");
      await storage.setItem("face_cadastrada", resp.face_cadastrada ? "true" : "false");

      // Registra push token em background (sem bloquear navegação)
      registerForPushNotificationsAsync();

      if (resp.primeiro_acesso) {
        router.replace("/auth/primeiro-acesso");
      } else if (resp.user_role === "Professor") {
        router.replace("/professor/home");
      } else {
        router.replace("/aluno/home");
      }
    } catch (error: any) {
      Alert.alert(
        "Falha no Login",
        error.message || "E-mail ou senha incorretos.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        <ScrollView 
          contentContainerStyle={{ flexGrow: 1 }}
          bounces={false}
          showsVerticalScrollIndicator={false}
        >
          {/* Parte superior (Espaçamento para o design) */}
          <View style={styles.topArea} />

          {/* Card de Login */}
          <View style={styles.card}>
            <Text style={styles.title}>Bem-vindo!</Text>
            
            <View style={styles.divider} />

            <Input
              label="Email"
              placeholder="seu@email.com"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              icon="mail-outline"
            />

            <Input
              label="Senha"
              placeholder="Sua senha"
              value={senha}
              onChangeText={setSenha}
              secureTextEntry={!showPassword}
              icon="lock-closed-outline"
              rightIcon={showPassword ? "eye-off-outline" : "eye-outline"}
              onRightIconPress={() => setShowPassword(!showPassword)}
            />

            <Button
              title="Entrar"
              onPress={handleLogin}
              loading={isLoading}
              style={{ marginTop: 10 }}
            />

            <TouchableOpacity
              style={styles.forgotBtn}
              onPress={() => router.push("/auth/esqueci-senha")}
              accessibilityRole="button"
            >
              <Text style={styles.forgotText}>Esqueceu sua senha?</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.brand.background,
  },
  topArea: {
    height: height * 0.20, // Reduzi um pouco para caber melhor em telas menores
    backgroundColor: Colors.brand.background,
  },
  card: {
    flex: 1,
    backgroundColor: Colors.brand.card,
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 20,
    minHeight: height * 0.75, // Garante que o card ocupe o resto da tela
  },
  title: {
    color: Colors.brand.text,
    fontSize: 32,
    fontWeight: "800",
    textAlign: "center",
  },
  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.15)",
    marginVertical: 24,
  },
  forgotBtn: {
    marginTop: 20,
    alignItems: "center",
  },
  forgotText: {
    color: Colors.brand.primary,
    fontSize: 14,
    fontWeight: "600",
  },
});
