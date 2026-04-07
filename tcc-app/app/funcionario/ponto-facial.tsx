import { Ionicons, MaterialCommunityIcons, Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useRef, useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Alert,
  ActivityIndicator,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { API_URL } from "../../services/api";

export default function PontoFacial() {
  const router = useRouter();
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraOpen, setCameraOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const cameraRef = useRef<CameraView | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const tirarFoto = async () => {
    if (!cameraRef.current) return;

    setIsLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.8,
      });

      // Monta formData para enviar a API
      const formData = new FormData();
      formData.append("foto", {
        uri: photo.uri,
        name: "ponto.jpg",
        type: "image/jpeg",
      } as any);

      const response = await fetch(`${API_URL}/ponto/registrar`, {
        method: "POST",
        body: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const data = await response.json();

      if (response.ok) {
        setLastResult(`Ponto registrado: ${data.tipo} às ${data.hora}`);
        Alert.alert("Sucesso!", `Ponto de ${data.tipo} registrado às ${data.hora}`);
      } else {
        Alert.alert("Erro", data.detail || "Não foi possível reconhecer seu rosto.");
      }
    } catch (error: any) {
      Alert.alert("Erro", "Falha na conexão com o servidor.");
    } finally {
      setIsLoading(false);
      setCameraOpen(false);
    }
  };

  if (!permission) {
    return <View />;
  }

  if (!permission.granted) {
    requestPermission();
  }

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Ponto Facial</Text>
        <View style={{ width: 22 }} />
      </View>

      {!cameraOpen ? (
        <>
          {/* CARD CAMERA */}
          <View style={styles.cameraCard}>
            <MaterialCommunityIcons name="face-recognition" size={70} color="#5B3EFF" />
            <Text style={styles.cameraText}>Posicione seu rosto na câmera</Text>
            <Text style={styles.verifyText}>para registrar o ponto</Text>

            {lastResult && (
              <View style={styles.resultContainer}>
                <Ionicons name="checkmark-circle" size={18} color="#22C55E" />
                <Text style={styles.resultText}>{lastResult}</Text>
              </View>
            )}
          </View>

          {/* INSTRUÇÕES */}
          <View style={styles.instructionsCard}>
            <Text style={styles.instructionsTitle}>Instruções:</Text>
            <View style={styles.instructionItem}>
              <Ionicons name="checkmark-circle" size={18} color="#22C55E" />
              <Text style={styles.instructionText}>Boa iluminação</Text>
            </View>
            <View style={styles.instructionItem}>
              <Ionicons name="checkmark-circle" size={18} color="#22C55E" />
              <Text style={styles.instructionText}>Sem óculos ou boné</Text>
            </View>
            <View style={styles.instructionItem}>
              <Ionicons name="checkmark-circle" size={18} color="#22C55E" />
              <Text style={styles.instructionText}>Olhe diretamente para a câmera</Text>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.button, isLoading && styles.buttonDisabled]}
            onPress={() => setCameraOpen(true)}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Feather name="camera" size={18} color="#fff" />
                <Text style={styles.buttonText}>Registrar Ponto</Text>
              </>
            )}
          </TouchableOpacity>
        </>
      ) : (
        <View style={{ flex: 1 }}>
          <CameraView style={{ flex: 1 }} facing="front" ref={cameraRef} />
          {/* Overlay com instrução */}
          <View style={styles.overlayInstruction}>
            <View style={styles.faceGuide}>
              <Ionicons name="scan" size={80} color="rgba(255,255,255,0.7)" />
            </View>
            <Text style={styles.overlayText}>Centralize seu rosto</Text>
          </View>
          <View style={styles.cameraControls}>
            <TouchableOpacity onPress={() => setCameraOpen(false)}>
              <Ionicons name="close" size={36} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity onPress={tirarFoto} disabled={isLoading}>
              {isLoading ? (
                <ActivityIndicator color="#fff" size="large" />
              ) : (
                <Ionicons name="camera" size={52} color="#5B3EFF" />
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F5",
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 25,
    justifyContent: "space-between",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  headerTitle: { fontSize: 17, fontWeight: "600", color: "#2C2C2C" },
  cameraCard: {
    backgroundColor: "#fff",
    borderRadius: 18,
    padding: 30,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  cameraText: { marginTop: 14, fontSize: 15, color: "#333", textAlign: "center" },
  verifyText: { fontSize: 13, color: "#888", marginTop: 2 },
  resultContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
    padding: 10,
    backgroundColor: "#F0FFF0",
    borderRadius: 10,
  },
  resultText: { marginLeft: 6, fontSize: 13, color: "#22C55E", fontWeight: "500" },
  instructionsCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 18,
    marginTop: 16,
  },
  instructionsTitle: { fontWeight: "600", marginBottom: 12, fontSize: 15, color: "#333" },
  instructionItem: { flexDirection: "row", alignItems: "center", marginBottom: 10 },
  instructionText: { marginLeft: 8, fontSize: 14, color: "#555" },
  button: {
    backgroundColor: "#22C55E",
    height: 52,
    borderRadius: 26,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
    marginTop: 16,
    shadowColor: "#22C55E",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 4,
  },
  buttonDisabled: { backgroundColor: "#aaa" },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  cameraControls: {
    position: "absolute",
    bottom: 50,
    width: "100%",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
  },
  overlayInstruction: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },
  faceGuide: {
    width: 200,
    height: 200,
    borderRadius: 100,
    borderWidth: 3,
    borderColor: "rgba(255,255,255,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },
  overlayText: { color: "#fff", fontSize: 16, marginTop: 16, fontWeight: "600" },
});
