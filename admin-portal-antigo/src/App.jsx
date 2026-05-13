import React, { useState, useEffect, useRef } from 'react';
import { LoginScreen } from './screens/LoginScreen';
import { AdminDashboard } from './screens/AdminDashboard';
import {
  installAuthInterceptor,
  clearAdminSession,
  readAdminSession,
} from './services/apiClient';
import { logout } from './services/authService';

export default function AdminPortal() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [adminUser, setAdminUser] = useState(null);

  const onSessionExpiredRef = useRef(() => {
    clearAdminSession();
    setIsLoggedIn(false);
    setAdminUser(null);
  });
  onSessionExpiredRef.current = () => {
    clearAdminSession();
    setIsLoggedIn(false);
    setAdminUser(null);
  };

  useEffect(() => {
    const session = readAdminSession();
    if (session.ok) {
      setAdminUser(session.user);
      setIsLoggedIn(true);
    } else if (session.partial) {
      clearAdminSession();
    }
  }, []);

  useEffect(() => {
    return installAuthInterceptor(() => onSessionExpiredRef.current?.());
  }, []);

  const handleLogin = (data) => {
    setAdminUser(data);
    setIsLoggedIn(true);
  };

  const handleLogout = async () => {
    await logout();
    setIsLoggedIn(false);
    setAdminUser(null);
  };

  if (!isLoggedIn) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return <AdminDashboard admin={adminUser} onLogout={handleLogout} />;
}
