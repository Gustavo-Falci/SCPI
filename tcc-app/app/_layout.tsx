import { ThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';
import { Slot, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { storage } from '../services/storage';
import { useEffect } from 'react';
import { useColorScheme } from '@/hooks/use-color-scheme';

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();

  useEffect(() => {
    const checkAuthAndRedirect = async () => {
      const token = await storage.getItem('access_token');
      // A lógica de redirecionamento principal deve estar na tela de login.
      // O layout raiz apenas garante que, se não houver token, o usuário
      // seja enviado para a tela de login. A tela de login, por sua vez,
      // se já houver um token, deve redirecionar para a home.
      // Esta verificação é um fallback de segurança.
      if (!token) {
        router.replace('/auth/login');
      }
    };

    checkAuthAndRedirect();
  }, []);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      {/* O Slot renderiza a rota filha correspondente. A lógica de redirecionamento
          acontece no useEffect acima e na própria tela de login. */}
      <Slot />
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}

