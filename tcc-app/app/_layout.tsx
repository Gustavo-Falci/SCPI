import { ThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { storage } from '../services/storage';
import { useEffect, useState } from 'react';
import { useColorScheme } from '@/hooks/use-color-scheme';

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();
  const segments = useSegments();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = await storage.getItem('access_token');
        const role = await storage.getItem('user_role');
        const inAuthGroup = segments[0] === 'auth';
        const isIndex = segments.length === 0 || segments[0] === '';

        if (!token) {
          // Se não tem token e não está na tela de auth, vai pro login
          if (!inAuthGroup) {
            router.replace('/auth/login');
          }
        } else {
          // Se tem token e está na index, vai pra home
          // Removi o redirecionamento automático de quem já está em /auth/login
          if (isIndex) {
            if (role === 'Professor') {
              router.replace('/professor/home');
            } else {
              router.replace('/aluno/home');
            }
          }
        }
      } catch (e) {
        console.error('Erro no RootLayout:', e);
      } finally {
        setIsReady(true);
      }
    };

    checkAuth();
  }, [segments]);

  if (!isReady) return null;

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="auth/login" options={{ headerShown: false }} />
        <Stack.Screen name="auth/register" options={{ headerShown: false }} />
        <Stack.Screen name="aluno/home" options={{ headerShown: false }} />
        <Stack.Screen name="aluno/cadastro-facial" options={{ headerShown: false }} />
        <Stack.Screen name="professor/home" options={{ headerShown: false }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
