import React, { useState } from 'react';
import { Lock, X } from 'lucide-react';
import { login } from '../services/authService';
import { extractErrorMessage } from '../services/apiClient';

export function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoading(true);
    try {
      const data = await login(email, password);
      onLogin(data);
    } catch (err) {
      setLoginError(`Falha no login: ${extractErrorMessage(err, 'Erro de conexão')}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0C0C12] p-6">
      <div className="w-full max-w-lg bg-[#151718] rounded-[50px] p-12 border border-white/5 shadow-2xl">
        <div className="text-center mb-12">
          <div className="w-24 h-24 bg-[#4B39EF]/10 rounded-[30px] flex items-center justify-center mx-auto mb-8">
            <Lock className="text-[#4B39EF]" size={48} />
          </div>
          <h1 className="text-4xl font-black text-white tracking-tight">Portal SCPI</h1>
          <p className="text-gray-500 text-lg mt-3 font-medium">Gestão Administrativa</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-8">
          <div className="space-y-3">
            <label className="text-xs font-black text-gray-400 uppercase tracking-[0.2em] ml-1">E-mail de Acesso</label>
            <input
              type="email" required
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg text-white focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 outline-none transition-all placeholder:text-gray-700"
              placeholder="admin@scpi.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-3">
            <label className="text-xs font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Senha Secreta</label>
            <input
              type="password" required
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg text-white focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 outline-none transition-all placeholder:text-gray-700"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button
            disabled={loading}
            className="w-full bg-[#4B39EF] hover:bg-[#5E47FF] text-white font-black py-6 rounded-2xl shadow-2xl shadow-[#4B39EF]/40 transition-all uppercase tracking-widest text-sm active:scale-[0.98]"
          >
            {loading ? 'Processando...' : 'Entrar no Sistema'}
          </button>
          {loginError && (
            <div className="flex items-center gap-3 mt-6 px-5 py-4 rounded-2xl border border-red-500/40 bg-red-500/5">
              <X size={16} className="text-red-400 shrink-0" />
              <p className="text-sm font-bold text-red-400">{loginError}</p>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
