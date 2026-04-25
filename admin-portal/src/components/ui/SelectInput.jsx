import React from 'react';
import { ChevronDown } from 'lucide-react';

export function SelectInput({ children, className = '', ...props }) {
  return (
    <div className="relative">
      <select
        style={{ colorScheme: 'dark' }}
        className={`w-full bg-[#1A1C1E] border border-white/10 rounded-xl px-4 py-3 pr-10 text-sm text-white outline-none focus:border-[#4B39EF] focus:ring-2 focus:ring-[#4B39EF]/20 transition-all appearance-none cursor-pointer ${className}`}
        {...props}
      >
        {children}
      </select>
      <ChevronDown size={18} className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
    </div>
  );
}
