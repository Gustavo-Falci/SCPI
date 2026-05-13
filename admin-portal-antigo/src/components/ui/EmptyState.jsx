import React from 'react';

export function EmptyState({ icon: Icon, message }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-white/[0.01] rounded-3xl border-2 border-dashed border-white/5">
      {Icon && <Icon className="text-gray-800 mb-4" size={48} />}
      <p className="text-gray-500 text-base font-black">{message}</p>
    </div>
  );
}
