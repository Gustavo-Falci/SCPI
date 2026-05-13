import React from 'react';

export function InputGroup({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-black text-gray-400 uppercase tracking-[0.15em] ml-1">{label}</label>
      {children}
    </div>
  );
}
