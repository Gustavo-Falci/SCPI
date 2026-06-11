import React, { useEffect, useRef } from "react";
import {
  Animated,
  Dimensions,
  Easing,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

export type ToastType = "error" | "success" | "warning" | "info";

export interface ToastData {
  id: number;
  type: ToastType;
  message: string;
  title?: string;
  duration?: number;
}

interface Props {
  toast: ToastData | null;
  onDismiss: (id: number) => void;
}

const COLORS: Record<ToastType, { bg: string; border: string; icon: keyof typeof Ionicons.glyphMap; text: string }> = {
  error: { bg: "#1F1416", border: "#EF4444", icon: "alert-circle", text: "#FECACA" },
  success: { bg: "#0F1A14", border: "#22C55E", icon: "checkmark-circle", text: "#BBF7D0" },
  warning: { bg: "#1F1A0F", border: "#F59E0B", icon: "warning", text: "#FDE68A" },
  info: { bg: "#0F141F", border: "#3B82F6", icon: "information-circle", text: "#BFDBFE" },
};

const DEFAULT_DURATIONS: Record<ToastType, number> = {
  error: 5000,
  success: 3000,
  warning: 4000,
  info: 3500,
};

const TITLES: Record<ToastType, string> = {
  error: "Erro",
  success: "Sucesso",
  warning: "Atenção",
  info: "Informação",
};

const { width } = Dimensions.get("window");

/**
 * Toast animado mobile — slide-down do topo, abaixo da status bar.
 * Tap para dispensar; auto-dismiss conforme tipo.
 */
export function ErrorToast({ toast, onDismiss }: Props) {
  const translateY = useRef(new Animated.Value(-200)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const dismissedRef = useRef(false);

  useEffect(() => {
    if (!toast) return;
    dismissedRef.current = false;

    const duration = toast.duration ?? DEFAULT_DURATIONS[toast.type];

    Animated.parallel([
      Animated.timing(translateY, {
        toValue: 0,
        duration: 280,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 1,
        duration: 220,
        useNativeDriver: true,
      }),
    ]).start();

    const timer = setTimeout(() => dismiss(), duration);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast?.id]);

  const dismiss = () => {
    if (!toast || dismissedRef.current) return;
    dismissedRef.current = true;

    Animated.parallel([
      Animated.timing(translateY, {
        toValue: -200,
        duration: 220,
        easing: Easing.in(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 0,
        duration: 180,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onDismiss(toast.id);
    });
  };

  if (!toast) return null;

  const cfg = COLORS[toast.type];

  return (
    <View pointerEvents="box-none" style={styles.wrapper}>
      <SafeAreaView edges={["top"]} pointerEvents="box-none">
        <Animated.View
          style={[
            styles.container,
            {
              transform: [{ translateY }],
              opacity,
              backgroundColor: cfg.bg,
              borderColor: cfg.border,
            },
          ]}
        >
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={dismiss}
            accessibilityRole="alert"
            accessibilityLabel={`${TITLES[toast.type]}: ${toast.message}. Toque para dispensar.`}
            style={styles.touchable}
          >
            <View style={[styles.iconWrap, { backgroundColor: cfg.border + "22" }]}>
              <Ionicons name={cfg.icon} size={22} color={cfg.border} />
            </View>
            <View style={styles.textWrap}>
              <Text style={[styles.title, { color: cfg.text }]} numberOfLines={1}>
                {toast.title ?? TITLES[toast.type]}
              </Text>
              <Text style={styles.message} numberOfLines={3}>
                {toast.message}
              </Text>
            </View>
            <Ionicons name="close" size={18} color="rgba(255,255,255,0.5)" />
          </TouchableOpacity>
        </Animated.View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    elevation: 50,
  },
  container: {
    marginHorizontal: 16,
    marginTop: 8,
    borderRadius: 16,
    borderWidth: 1.5,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 12,
    maxWidth: width - 32,
  },
  touchable: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 14,
    gap: 12,
  },
  iconWrap: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
  },
  textWrap: {
    flex: 1,
  },
  title: {
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.8,
    textTransform: "uppercase",
    marginBottom: 2,
  },
  message: {
    fontSize: 14,
    color: "#fff",
    lineHeight: 19,
    fontWeight: "500",
  },
});
