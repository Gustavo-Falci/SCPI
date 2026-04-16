import { Feather, Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useRef, useState, useEffect } from "react";
import { 
  StyleSheet, 
  Text, 
  TouchableOpacity, 
  View, 
  Alert, 
  ActivityIndicator, 
  StatusBar,
  Dimensions 
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { storage } from "../../services/storage";
import { apiPostFormData } from "../../services/api";
import { Colors } from "../../constants/theme";

const { width, height } = Dimensions.get("window");

export default function CadastroFacial() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraOpen, setCameraOpen] = useState(false);
  const cameraRef = useRef<CameraView | null>(null);
  const [loading, setLoading] = useState(false);
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

  const tirarFoto = async () => {
    if (!cameraRef.current || loading) return;

    setLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.7,
        base64: false,
      });
      
      const formData = new FormData();
      formData.append("user_id", userData?.id || "");
      formData.append("nome", userData?.nome || "Aluno");
      formData.append("email", userData?.email || "");
      formData.append("ra", userData?.ra || "");

      const localUri = photo.uri;
      const filename = localUri.split('/').pop() || 'face.jpg';
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : `image/jpeg`;

      formData.append("foto", {
        uri: localUri,
        name: filename,
        type: type,
      } as any);

      await apiPostFormData("/alunos/cadastrar-face", formData);
      
      Alert.alert("Sucesso!", "Sua biometria facial foi cadastrada com sucesso!");
      router.back();
    } catch (error: any) {
      console.error("Erro no cadastro facial:", error);
      Alert.alert("Erro", error.message || "Não foi possível processar sua face. Tente novamente em um local mais iluminado.");
    } finally {
      setLoading(false);
    }
  };

  if (!permission) return <View style={styles.container} />;
  
  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Ionicons name="camera-outline" size={80} color={Colors.brand.textSecondary} />
          <Text style={styles.permissionText}>Precisamos de acesso à sua câmera para realizar o cadastro facial.</Text>
          <TouchableOpacity style={styles.primaryButton} onPress={requestPermission}>
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
          
          {/* BOTÃO FECHAR (TOPO ESQUERDO) */}
          <TouchableOpacity 
            style={[styles.closeBtnTop, { top: insets.top + 20 }]} 
            onPress={() => setCameraOpen(false)}
            disabled={loading}
          >
            <Ionicons name="close" size={30} color="#fff" />
          </TouchableOpacity>

          <View style={styles.scannerContainer}>
            <Text style={styles.cameraHint}>
               Posicione seu rosto dentro da moldura
            </Text>

            {/* MOLDURA OVAL COM A CÂMERA DENTRO */}
            <View style={styles.faceFrameContainer}>
              <View style={styles.ovalMask}>
                <CameraView
                  style={styles.cameraPreview}
                  facing="front"
                  ref={cameraRef}
                />
              </View>
              {/* Borda decorativa azul */}
              <View style={styles.faceFrameBorder} />
            </View>
          </View>

          {/* BOTÕES DE CAPTURA (BASE) */}
          <View style={styles.cameraControls}>
            <TouchableOpacity 
              style={styles.captureBtn} 
              onPress={tirarFoto}
              disabled={loading}
            >
              <View style={styles.captureBtnInner} />
            </TouchableOpacity>
          </View>

          {loading && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color={Colors.brand.primary} />
              <Text style={styles.loadingText}>Processando Biometria...</Text>
            </View>
          )}
        </View>
      ) : (
        <SafeAreaView style={{ flex: 1 }}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Cadastro Biométrico</Text>
            <View style={{ width: 44 }} />
          </View>

          <View style={styles.content}>
            <View style={styles.previewCard}>
              <MaterialCommunityIcons name="face-recognition" size={100} color={Colors.brand.primary} />
              <Text style={styles.previewTitle}>Pronto para o Scanner?</Text>
              <Text style={styles.previewSubtitle}>Siga as instruções abaixo para garantir a melhor precisão.</Text>
            </View>

            <View style={styles.instructionsContainer}>
              <View style={styles.instructionItem}>
                <View style={styles.iconCircle}>
                  <Ionicons name="sunny-outline" size={20} color={Colors.brand.primary} />
                </View>
                <Text style={styles.instructionText}>Procure um ambiente bem iluminado</Text>
              </View>

              <View style={styles.instructionItem}>
                <View style={styles.iconCircle}>
                  <Ionicons name=" eyeglasses-outline" size={20} color={Colors.brand.primary} />
                </View>
                <Text style={styles.instructionText}>Remova óculos escuros e máscara</Text>
              </View>

              <View style={styles.instructionItem}>
                <View style={styles.iconCircle}>
                  <Ionicons name="person-outline" size={20} color={Colors.brand.primary} />
                </View>
                <Text style={styles.instructionText}>Mantenha uma expressão neutra</Text>
              </View>
            </View>

            <TouchableOpacity 
              style={styles.mainButton} 
              onPress={() => setCameraOpen(true)}
            >
              <Ionicons name="camera" size={22} color="#fff" />
              <Text style={styles.mainButtonText}>Abrir Câmera</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.brand.background,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    height: 60,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#fff",
  },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.brand.card,
    justifyContent: "center",
    alignItems: "center",
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
  },
  previewCard: {
    backgroundColor: Colors.brand.card,
    borderRadius: 32,
    padding: 40,
    alignItems: "center",
    marginBottom: 40,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  previewTitle: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "800",
    marginTop: 20,
  },
  previewSubtitle: {
    color: Colors.brand.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 8,
  },
  instructionsContainer: {
    gap: 16,
    marginBottom: 40,
  },
  instructionItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(75, 57, 239, 0.1)",
    justifyContent: "center",
    alignItems: "center",
  },
  instructionText: {
    color: Colors.brand.textSecondary,
    fontSize: 15,
    fontWeight: "500",
  },
  mainButton: {
    backgroundColor: Colors.brand.primary,
    height: 60,
    borderRadius: 18,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
  },
  mainButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  cameraWrapper: {
    flex: 1,
    backgroundColor: "#000",
  },
  scannerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  faceFrameContainer: {
    width: 280,
    height: 420,
    justifyContent: "center",
    alignItems: "center",
  },
  ovalMask: {
    width: 280,
    height: 420,
    borderRadius: 140,
    overflow: "hidden", // Isso faz a mágica de cortar a câmera
    backgroundColor: "#000",
  },
  cameraPreview: {
    flex: 1,
    width: "100%",
  },
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
  captureBtnInner: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#fff",
  },
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
  loadingText: {
    color: "#fff",
    marginTop: 20,
    fontSize: 16,
    fontWeight: "700",
  },
  permissionText: {
    color: Colors.brand.textSecondary,
    textAlign: "center",
    marginVertical: 20,
    fontSize: 16,
  },
  primaryButton: {
    backgroundColor: Colors.brand.primary,
    paddingHorizontal: 30,
    paddingVertical: 15,
    borderRadius: 12,
  },
  buttonText: {
    color: "#fff",
    fontWeight: "700",
  }
});
