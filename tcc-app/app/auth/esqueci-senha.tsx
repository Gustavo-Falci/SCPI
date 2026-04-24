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
import { Ionicons } from "@expo/vector-icons";
import { apiPost } from "../../services/api";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Colors } from "../../constants/theme";

const { height } = Dimensions.get("window");

type Step = "email" | "codigo" | "senha";

export default function EsqueciSenha() {
  const router = useRouter();

  const [step, setStep] = useState<Step>("email");
  const [isLoading, setIsLoading] = useState(false);

  const [email, setEmail] = useState("");
  const [codigo, setCodigo] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [confirmarSenhaError, setConfirmarSenhaError] = useState("");

  const passwordRules = {
    minLength: novaSenha.length >= 8,
    hasNumber: /\d/.test(novaSenha),
    hasUppercase: /[A-Z]/.test(novaSenha),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(novaSenha),
  };
  const allRulesOk = Object.values(passwordRules).every(Boolean);
  const senhasConferem = novaSenha === confirmarSenha && novaSenha.length > 0;

  const STEPS: Record<Step, { title: string; subtitle: string; badge: string; icon: string }> = {
    email:  { title: "Esqueci minha senha", subtitle: "Informe seu e-mail para receber o código de verificação.", badge: "Passo 1 de 3", icon: "mail-outline" },
    codigo: { title: "Verifique seu e-mail", subtitle: `Enviamos um código de 6 dígitos para\n${email}`, badge: "Passo 2 de 3", icon: "shield-checkmark-outline" },
    senha:  { title: "Nova senha", subtitle: "Defina uma nova senha segura para sua conta.", badge: "Passo 3 de 3", icon: "lock-closed-outline" },
  };

  const handleEnviarEmail = async () => {
    if (!email.trim()) { Alert.alert("Erro", "Informe seu e-mail."); return; }
    setIsLoading(true);
    try {
      await apiPost("/auth/esqueci-senha", { email: email.trim() });
      setStep("codigo");
    } catch (error: any) {
      Alert.alert("Atenção", error.message || "Não foi possível enviar o código.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerificarCodigo = async () => {
    if (codigo.length !== 6) { Alert.alert("Erro", "O código deve ter 6 dígitos."); return; }
    setIsLoading(true);
    try {
      const resp = await apiPost("/auth/verificar-codigo", { email: email.trim(), codigo });
      setResetToken(resp.reset_token);
      setStep("senha");
    } catch (error: any) {
      Alert.alert("Erro", error.message || "Código inválido ou expirado.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRedefinirSenha = async () => {
    if (!allRulesOk) { Alert.alert("Senha fraca", "A senha não atende todos os requisitos."); return; }
    if (!senhasConferem) { Alert.alert("Erro", "As senhas não coincidem."); return; }
    setIsLoading(true);
    try {
      await apiPost("/auth/redefinir-senha", { reset_token: resetToken, nova_senha: novaSenha });
      Alert.alert("Sucesso!", "Sua senha foi redefinida. Faça login com a nova senha.", [
        { text: "OK", onPress: () => router.replace("/auth/login") },
      ]);
    } catch (error: any) {
      Alert.alert("Erro", error.message || "Não foi possível redefinir a senha.");
    } finally {
      setIsLoading(false);
    }
  };

  const meta = STEPS[step];

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ flexGrow: 1 }} showsVerticalScrollIndicator={false} bounces={false}>

          <View style={styles.topArea}>
            <TouchableOpacity style={styles.backBtn} onPress={() => step === "email" ? router.back() : setStep(step === "codigo" ? "email" : "codigo")} accessibilityRole="button">
              <Ionicons name="arrow-back" size={22} color={Colors.brand.text} />
            </TouchableOpacity>
            <View style={styles.stepBadge}>
              <Text style={styles.stepBadgeText}>{meta.badge}</Text>
            </View>
          </View>

          <View style={styles.card}>
            <View style={styles.heroSection}>
              <View style={styles.heroIconBadge}>
                <Ionicons name={meta.icon as any} size={30} color={Colors.brand.primary} />
              </View>
              <Text style={styles.title}>{meta.title}</Text>
              <Text style={styles.subtitle}>{meta.subtitle}</Text>
            </View>

            <View style={styles.divider} />

            {step === "email" && (
              <>
                <Input
                  label="E-mail"
                  placeholder="seu@email.com"
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  icon="mail-outline"
                />
                <Button title="ENVIAR CÓDIGO" onPress={handleEnviarEmail} loading={isLoading} style={{ marginTop: 10 }} />
              </>
            )}

            {step === "codigo" && (
              <>
                <Input
                  label="Código de verificação"
                  placeholder="000000"
                  value={codigo}
                  onChangeText={(v) => setCodigo(v.replace(/\D/g, "").slice(0, 6))}
                  keyboardType="number-pad"
                  icon="keypad-outline"
                  containerStyle={{ marginBottom: 8 }}
                />
                <Text style={styles.reenviarHint}>
                  Não recebeu?{" "}
                  <Text style={styles.reenviarLink} onPress={handleEnviarEmail}>Reenviar código</Text>
                </Text>
                <Button
                  title="VERIFICAR CÓDIGO"
                  onPress={handleVerificarCodigo}
                  loading={isLoading}
                  disabled={codigo.length !== 6}
                  style={{ marginTop: 16, opacity: codigo.length === 6 ? 1 : 0.4 }}
                />
              </>
            )}

            {step === "senha" && (
              <>
                <Input
                  label="Nova Senha"
                  placeholder="••••••"
                  value={novaSenha}
                  onChangeText={setNovaSenha}
                  secureTextEntry={!showSenha}
                  icon="lock-closed-outline"
                  rightIcon={showSenha ? "eye-off-outline" : "eye-outline"}
                  onRightIconPress={() => setShowSenha((v) => !v)}
                  containerStyle={{ marginBottom: novaSenha.length > 0 ? 0 : 16 }}
                />
                {novaSenha.length > 0 && (
                  <View style={styles.passwordReqs}>
                    {(
                      [
                        { key: "minLength" as const, label: "Mínimo 8 caracteres" },
                        { key: "hasNumber" as const, label: "Pelo menos 1 número" },
                        { key: "hasUppercase" as const, label: "Pelo menos 1 maiúscula" },
                        { key: "hasSpecial" as const, label: "Pelo menos 1 especial" },
                      ] as const
                    ).map(({ key, label }) => (
                      <View key={key} style={styles.reqItem}>
                        <Ionicons
                          name={passwordRules[key] ? "checkmark-circle" : "ellipse-outline"}
                          size={14}
                          color={passwordRules[key] ? "#22C55E" : "#BFBFBF"}
                        />
                        <Text style={[styles.reqText, passwordRules[key] && styles.reqTextOk]}>{label}</Text>
                      </View>
                    ))}
                  </View>
                )}
                <Input
                  label="Confirmar Nova Senha"
                  placeholder="••••••"
                  value={confirmarSenha}
                  onChangeText={(v) => {
                    setConfirmarSenha(v);
                    setConfirmarSenhaError(v.length > 0 && novaSenha !== v ? "As senhas não coincidem." : "");
                  }}
                  secureTextEntry={!showSenha}
                  icon="checkmark-circle-outline"
                  error={confirmarSenhaError}
                />
                <Button
                  title="SALVAR NOVA SENHA"
                  onPress={handleRedefinirSenha}
                  loading={isLoading}
                  disabled={!allRulesOk || !senhasConferem}
                  style={{ marginTop: 10, opacity: allRulesOk && senhasConferem ? 1 : 0.4 }}
                />
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  topArea: {
    height: height * 0.15,
    backgroundColor: Colors.brand.background,
    alignItems: "center",
    justifyContent: "flex-end",
    paddingBottom: 12,
    paddingHorizontal: 20,
  },
  backBtn: {
    position: "absolute",
    left: 20,
    bottom: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.07)",
    justifyContent: "center",
    alignItems: "center",
  },
  stepBadge: {
    backgroundColor: "rgba(75, 57, 239, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(75, 57, 239, 0.4)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  stepBadgeText: {
    color: Colors.brand.primary,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    textTransform: "uppercase",
  },
  card: {
    flex: 1,
    backgroundColor: Colors.brand.card,
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    paddingHorizontal: 24,
    paddingTop: 32,
    paddingBottom: 24,
    minHeight: height * 0.85,
  },
  heroSection: { alignItems: "center", marginBottom: 8 },
  heroIconBadge: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "rgba(75, 57, 239, 0.12)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "rgba(75, 57, 239, 0.25)",
  },
  title: { color: Colors.brand.text, fontSize: 26, fontWeight: "800", textAlign: "center" },
  subtitle: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 12,
    lineHeight: 20,
  },
  divider: { height: 1, backgroundColor: "rgba(255,255,255,0.1)", marginVertical: 24 },
  reenviarHint: { color: Colors.brand.textSecondary, fontSize: 13, textAlign: "center" },
  reenviarLink: { color: Colors.brand.primary, fontWeight: "700" },
  passwordReqs: {
    backgroundColor: "rgba(255,255,255,0.03)",
    borderRadius: 12,
    padding: 12,
    marginTop: 6,
    marginBottom: 16,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  reqItem: { flexDirection: "row", alignItems: "center", gap: 5, width: "47%" },
  reqText: { color: "#BFBFBF", fontSize: 12 },
  reqTextOk: { color: "#22C55E" },
});
