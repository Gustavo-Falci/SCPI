import { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Alert,
  ScrollView,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { CameraView, useCameraPermissions } from "expo-camera";

import { apiPost, apiPostFormData } from "../../services/api";
import { storage } from "../../services/storage";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Colors } from "../../constants/theme";

const { height } = Dimensions.get("window");

export default function PrimeiroAcesso() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [step, setStep] = useState<"senha" | "face">("senha");
  const [isLoading, setIsLoading] = useState(false);

  // Step 1 — senha
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [showSenhaAtual, setShowSenhaAtual] = useState(false);
  const [showNovaSenha, setShowNovaSenha] = useState(false);
  const [confirmarSenhaError, setConfirmarSenhaError] = useState("");

  // Step 2 — face
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [consentimento, setConsentimento] = useState(false);
  const [userData, setUserData] = useState<any>(null);

  useEffect(() => {
    const loadUser = async () => {
      const nome = await storage.getItem("user_name");
      const email = await storage.getItem("user_email");
      const ra = await storage.getItem("user_ra");
      const id = await storage.getItem("user_id");
      setUserData({ nome, email, ra, id });
    };
    loadUser();
  }, []);

  const passwordRules = {
    minLength: novaSenha.length >= 8,
    hasNumber: /\d/.test(novaSenha),
    hasUppercase: /[A-Z]/.test(novaSenha),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(novaSenha),
  };
  const allRulesOk = Object.values(passwordRules).every(Boolean);
  const senhasConferem = novaSenha === confirmarSenha && novaSenha.length > 0;
  const formValido = allRulesOk && senhasConferem && senhaAtual.length > 0;

  const handleAlterarSenha = async () => {
    if (!senhaAtual) {
      Alert.alert("Erro", "Informe sua senha temporária.");
      return;
    }
    if (!allRulesOk) {
      Alert.alert("Senha fraca", "A senha não atende a todos os requisitos de segurança.");
      return;
    }
    if (!senhasConferem) {
      Alert.alert("Erro", "As senhas não coincidem.");
      return;
    }

    setIsLoading(true);
    try {
      await apiPost("/auth/alterar-senha", {
        senha_atual: senhaAtual,
        nova_senha: novaSenha,
      });

      await storage.setItem("primeiro_acesso", "false");

      const role = await storage.getItem("user_role");
      const faceCadastrada = await storage.getItem("face_cadastrada");

      if (role === "Aluno" && faceCadastrada !== "true") {
        setStep("face");
      } else if (role === "Professor") {
        router.replace("/professor/home");
      } else {
        router.replace("/aluno/home");
      }
    } catch (error: any) {
      Alert.alert("Erro", error.message || "Não foi possível alterar a senha.");
    } finally {
      setIsLoading(false);
    }
  };

  const tirarFotoECadastrar = async () => {
    if (!cameraRef.current || isLoading) return;
    if (!userData?.email || !userData?.ra) {
      Alert.alert("Erro de Dados", "Seus dados (Email/RA) não foram localizados. Faça logout e entre novamente.");
      return;
    }

    setIsLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.7,
        base64: false,
        shutterSound: false,
      });

      const formData = new FormData();
      formData.append("user_id", userData?.id || "");
      formData.append("nome", userData?.nome || "Aluno");
      formData.append("email", userData?.email || "");
      formData.append("ra", userData?.ra || "");

      const localUri = photo.uri;
      const filename = localUri.split("/").pop() || "face.jpg";
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : `image/jpeg`;

      formData.append("foto", {
        uri: localUri,
        name: filename,
        type,
      } as any);
      formData.append("consentimento_biometrico", "true");

      console.log("[face] uri:", localUri, "type:", type, "userData:", JSON.stringify(userData));
      await apiPostFormData("/alunos/cadastrar-face", formData);

      await storage.setItem("face_cadastrada", "true");
      Alert.alert("Tudo pronto!", "Sua biometria facial foi cadastrada com sucesso!");
      router.replace("/aluno/home");
    } catch (error: any) {
      Alert.alert("Erro", error.message || "Não foi possível processar sua face. Tente novamente.");
      setCameraOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  // ---------- STEP 2 — FACE ----------
  if (step === "face") {
    if (!permission) return <View style={styles.container} />;

    if (!permission.granted) {
      return (
        <SafeAreaView style={styles.container}>
          <View style={styles.center}>
            <Ionicons name="camera-outline" size={80} color={Colors.brand.textSecondary} />
            <Text style={styles.permissionText}>
              Precisamos de acesso à sua câmera para concluir o cadastro facial.
            </Text>
            <TouchableOpacity
              style={styles.primaryButton}
              onPress={requestPermission}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel="Permitir acesso à câmera"
            >
              <Text style={styles.buttonText}>Permitir Câmera</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      );
    }

    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />

        {cameraOpen ? (
          <View style={styles.cameraWrapper}>
            <TouchableOpacity
              style={[styles.closeBtnTop, { top: insets.top + 20 }]}
              onPress={() => setCameraOpen(false)}
              disabled={isLoading}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel="Fechar câmera"
            >
              <Ionicons name="close" size={30} color="#fff" />
            </TouchableOpacity>

            <View style={styles.scannerContainer}>
              <Text style={styles.cameraHint}>Posicione seu rosto dentro da moldura</Text>

              <View style={styles.faceFrameContainer}>
                <View style={styles.ovalMask}>
                  <CameraView style={styles.cameraPreview} facing="front" ref={cameraRef} />
                </View>
                <View style={styles.faceFrameBorder} />
              </View>
            </View>

            <View style={styles.cameraControls}>
              <TouchableOpacity
                style={styles.captureBtn}
                onPress={tirarFotoECadastrar}
                disabled={isLoading}
                activeOpacity={0.7}
                accessibilityRole="button"
                accessibilityLabel="Tirar foto e cadastrar face"
              >
                <View style={styles.captureBtnInner} />
              </TouchableOpacity>
            </View>

            {isLoading && (
              <View style={styles.loadingOverlay}>
                <ActivityIndicator size="large" color={Colors.brand.primary} />
                <Text style={styles.loadingText}>Processando Biometria...</Text>
              </View>
            )}
          </View>
        ) : (
          <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.faceHeader}>
              <View style={{ width: 44 }} />
              <Text style={styles.headerTitle}>Passo 2 de 2</Text>
              <View style={{ width: 44 }} />
            </View>

            <ScrollView
              style={{ flex: 1 }}
              contentContainerStyle={styles.scrollContent}
              showsVerticalScrollIndicator={false}
            >
              <View style={styles.heroSection}>
                <View style={styles.heroIconBadge}>
                  <MaterialCommunityIcons name="face-recognition" size={52} color={Colors.brand.primary} />
                </View>
                <Text style={styles.heroTitle}>Complete seu Cadastro</Text>
                <Text style={styles.heroSubtitle}>
                  Cadastre seu rosto para registrar presença nas aulas automaticamente.
                </Text>
              </View>

              <Text style={styles.faceSectionLabel}>Antes de começar</Text>
              <View style={styles.instructionsContainer}>
                <View style={styles.instructionItem}>
                  <View style={styles.iconCircle}>
                    <Ionicons name="sunny-outline" size={18} color={Colors.brand.primary} />
                  </View>
                  <Text style={styles.instructionText}>Procure um ambiente bem iluminado</Text>
                </View>

                <View style={styles.instructionItem}>
                  <View style={styles.iconCircle}>
                    <Ionicons name="glasses-outline" size={18} color={Colors.brand.primary} />
                  </View>
                  <Text style={styles.instructionText}>Remova óculos escuros e máscara</Text>
                </View>

                <View style={styles.instructionItem}>
                  <View style={styles.iconCircle}>
                    <Ionicons name="person-outline" size={18} color={Colors.brand.primary} />
                  </View>
                  <Text style={styles.instructionText}>Mantenha uma expressão neutra</Text>
                </View>
              </View>

              <Text style={styles.faceSectionLabel}>Privacidade</Text>
              <View style={[styles.consentCard, consentimento && styles.consentCardActive]}>
                <View style={styles.consentHeader}>
                  <Ionicons name="shield-checkmark-outline" size={22} color={Colors.brand.primary} />
                  <Text style={styles.consentTitle}>Consentimento LGPD</Text>
                </View>
                <Text style={styles.consentBody}>
                  Autorizo o SCPI a coletar e processar minha imagem facial para{" "}
                  <Text style={styles.consentBodyStrong}>controle de presença nas aulas</Text>. Os dados são
                  armazenados de forma segura (AWS Rekognition + S3) e posso revogar este consentimento a
                  qualquer momento pelo meu perfil. (LGPD art. 11)
                </Text>
                <TouchableOpacity
                  style={styles.consentRow}
                  onPress={() => setConsentimento((v) => !v)}
                  activeOpacity={0.8}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <View style={[styles.checkbox, consentimento && styles.checkboxActive]}>
                    {consentimento && <Ionicons name="checkmark" size={16} color="#fff" />}
                  </View>
                  <Text style={styles.consentCheckLabel}>
                    Li e concordo com o tratamento dos meus dados biométricos.
                  </Text>
                </TouchableOpacity>
              </View>

              <TouchableOpacity
                style={[styles.mainButton, !consentimento && styles.mainButtonDisabled]}
                onPress={() => consentimento && setCameraOpen(true)}
                disabled={!consentimento}
                activeOpacity={0.85}
              >
                <Ionicons name="camera" size={22} color="#fff" />
                <Text style={styles.mainButtonText}>Cadastrar Face</Text>
              </TouchableOpacity>
              {!consentimento && (
                <Text style={styles.hintText}>Marque o consentimento acima para continuar</Text>
              )}
            </ScrollView>
          </SafeAreaView>
        )}
      </View>
    );
  }

  // ---------- STEP 1 — SENHA ----------
  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1 }}>
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ flexGrow: 1 }}>
          <View style={styles.topArea}>
            <View style={styles.stepBadge}>
              <Text style={styles.stepBadgeText}>Passo 1 de 2</Text>
            </View>
          </View>

          <View style={styles.card}>
            <View style={styles.heroInline}>
              <View style={styles.heroIconSmall}>
                <Ionicons name="lock-closed" size={28} color={Colors.brand.primary} />
              </View>
              <Text style={styles.title}>Altere sua Senha</Text>
              <Text style={styles.subtitle}>
                Por segurança, defina uma nova senha para sua conta.
              </Text>
            </View>

            <View style={styles.divider} />

            <Input
              label="Senha Temporária"
              placeholder="Senha atual"
              value={senhaAtual}
              onChangeText={setSenhaAtual}
              secureTextEntry={!showSenhaAtual}
              icon="key-outline"
              rightIcon={showSenhaAtual ? "eye-off-outline" : "eye-outline"}
              onRightIconPress={() => setShowSenhaAtual((v) => !v)}
            />

            <Input
              label="Nova Senha"
              placeholder="••••••"
              value={novaSenha}
              onChangeText={setNovaSenha}
              secureTextEntry={!showNovaSenha}
              icon="lock-closed-outline"
              rightIcon={showNovaSenha ? "eye-off-outline" : "eye-outline"}
              onRightIconPress={() => setShowNovaSenha((v) => !v)}
              containerStyle={{ marginBottom: novaSenha.length > 0 ? 0 : 16 }}
            />
            {novaSenha.length > 0 && (
              <View style={styles.passwordReqs}>
                {(
                  [
                    { key: "minLength" as const, label: "Mínimo 8 caracteres" },
                    { key: "hasNumber" as const, label: "Pelo menos 1 número" },
                    { key: "hasUppercase" as const, label: "Pelo menos 1 maiúscula" },
                    { key: "hasSpecial" as const, label: "Pelo menos 1 caractere especial" },
                  ]
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
              secureTextEntry={!showNovaSenha}
              icon="checkmark-circle-outline"
              error={confirmarSenhaError}
            />

            <Button
              title="SALVAR E CONTINUAR"
              onPress={handleAlterarSenha}
              loading={isLoading}
              disabled={!formValido}
              style={{ marginTop: 10, opacity: formValido ? 1 : 0.4 }}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.brand.background },
  topArea: {
    height: height * 0.18,
    backgroundColor: Colors.brand.background,
    alignItems: "center",
    justifyContent: "center",
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
    minHeight: height * 0.82,
  },
  heroInline: {
    alignItems: "center",
    marginBottom: 8,
  },
  heroIconSmall: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "rgba(75, 57, 239, 0.12)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(75, 57, 239, 0.25)",
  },
  title: {
    color: Colors.brand.text,
    fontSize: 26,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 16,
    lineHeight: 20,
  },
  divider: {
    height: 1,
    backgroundColor: "rgba(255,255,255,0.1)",
    marginVertical: 24,
  },
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
  reqItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    width: "47%",
  },
  reqText: {
    color: "#BFBFBF",
    fontSize: 12,
  },
  reqTextOk: {
    color: "#22C55E",
  },

  // Face step
  center: { flex: 1, justifyContent: "center", alignItems: "center", paddingHorizontal: 40 },
  faceHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    height: 60,
  },
  headerTitle: { fontSize: 14, fontWeight: "800", color: "#fff", letterSpacing: 1.2, textTransform: "uppercase" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 40 },
  heroSection: { alignItems: "center", marginBottom: 28, marginTop: 8 },
  heroIconBadge: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: "rgba(75, 57, 239, 0.12)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "rgba(75, 57, 239, 0.25)",
  },
  heroTitle: { color: "#fff", fontSize: 24, fontWeight: "800", textAlign: "center" },
  heroSubtitle: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 6,
    paddingHorizontal: 16,
    lineHeight: 20,
  },
  faceSectionLabel: {
    color: Colors.brand.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1.2,
    textTransform: "uppercase",
    marginBottom: 12,
    marginLeft: 4,
  },
  instructionsContainer: { gap: 10, marginBottom: 24 },
  instructionItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    backgroundColor: "rgba(255,255,255,0.03)",
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 14,
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(75, 57, 239, 0.12)",
    justifyContent: "center",
    alignItems: "center",
  },
  instructionText: { flex: 1, color: Colors.brand.text, fontSize: 14, fontWeight: "500" },
  mainButton: {
    backgroundColor: Colors.brand.primary,
    height: 56,
    borderRadius: 16,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
    marginTop: 8,
    shadowColor: Colors.brand.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
  mainButtonDisabled: { opacity: 0.35, shadowOpacity: 0 },
  mainButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  hintText: {
    color: Colors.brand.textSecondary,
    fontSize: 12,
    textAlign: "center",
    marginTop: 12,
    fontStyle: "italic",
  },
  consentCard: {
    backgroundColor: Colors.brand.card,
    borderRadius: 18,
    padding: 18,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  consentCardActive: { borderColor: Colors.brand.primary, backgroundColor: "rgba(75, 57, 239, 0.06)" },
  consentHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  consentTitle: { color: "#fff", fontSize: 15, fontWeight: "700" },
  consentBody: { color: Colors.brand.textSecondary, fontSize: 13, lineHeight: 20, marginBottom: 16 },
  consentBodyStrong: { color: Colors.brand.text, fontWeight: "700" },
  consentRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.06)",
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: Colors.brand.textSecondary,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 1,
  },
  checkboxActive: { backgroundColor: Colors.brand.primary, borderColor: Colors.brand.primary },
  consentCheckLabel: { flex: 1, color: Colors.brand.text, fontSize: 13, fontWeight: "500", lineHeight: 18 },
  cameraWrapper: { flex: 1, backgroundColor: "#000" },
  scannerContainer: { flex: 1, justifyContent: "center", alignItems: "center" },
  faceFrameContainer: { width: 280, height: 420, justifyContent: "center", alignItems: "center" },
  ovalMask: { width: 280, height: 420, borderRadius: 140, overflow: "hidden", backgroundColor: "#000" },
  cameraPreview: { flex: 1, width: "100%" },
  faceFrameBorder: {
    position: "absolute",
    width: 280,
    height: 420,
    borderRadius: 140,
    borderWidth: 3,
    borderColor: Colors.brand.primary,
  },
  cameraControls: {
    position: "absolute",
    bottom: 50,
    width: "100%",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  captureBtn: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "rgba(255,255,255,0.3)",
    justifyContent: "center",
    alignItems: "center",
  },
  captureBtnInner: { width: 64, height: 64, borderRadius: 32, backgroundColor: "#fff" },
  closeBtnTop: {
    position: "absolute",
    left: 25,
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: "rgba(255,255,255,0.1)",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 20,
  },
  cameraHint: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
    textAlign: "center",
    paddingHorizontal: 40,
    marginBottom: 30,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.8)",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 30,
  },
  loadingText: { color: "#fff", marginTop: 20, fontSize: 16, fontWeight: "700" },
  permissionText: { color: Colors.brand.textSecondary, textAlign: "center", marginVertical: 20, fontSize: 16 },
  primaryButton: { backgroundColor: Colors.brand.primary, paddingHorizontal: 30, paddingVertical: 15, borderRadius: 12 },
  buttonText: { color: "#fff", fontWeight: "700" },
});
