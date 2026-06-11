import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";
import Constants from "expo-constants";
import { apiPost } from "./api";

// Exibe notificações em primeiro plano como alerta
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPushNotificationsAsync() {
  // Push tokens não funcionam em simulador/emulador, apenas em dispositivos físicos
  if (!Device.isDevice) {
    console.log("[Notifications] Push tokens requerem dispositivo físico.");
    return null;
  }

  // Canal Android
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("presencas", {
      name: "Presenças",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#4B39EF",
      sound: "default",
    });
  }

  // Permissão
  const { status: existing } = await Notifications.getPermissionsAsync();
  let finalStatus = existing;

  if (existing !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.log("[Notifications] Permissão de notificação negada.");
    return null;
  }

  // Obtém o Expo Push Token — requer projectId do EAS
  try {
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;

    if (!projectId) {
      console.log(
        "[Notifications] projectId não configurado. " +
        "Execute 'eas init' para habilitar push notifications."
      );
      return null;
    }

    const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
    const expoToken = tokenData.data;
    console.log("[Notifications] Expo push token:", expoToken);

    // Registra no backend (silenciosamente em background)
    apiPost("/notificacoes/registrar-token", { expo_token: expoToken }).catch(
      (e) => console.warn("[Notifications] Falha ao registrar token:", e.message)
    );

    return expoToken;
  } catch (e) {
    console.warn("[Notifications] Erro ao obter push token:", e.message);
    return null;
  }
}
