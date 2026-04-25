import React from 'react';
import { ChevronDown } from 'lucide-react';

export function Pagination({ page, totalPages, onPageChange, totalItems, itemLabel }) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between flex-shrink-0 pt-3">
      <p className="text-xs font-black text-gray-500">
        {totalItems} {itemLabel} • página {page} de {totalPages}
      </p>
      <div className="flex gap-1.5">
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1}
          className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronDown size={14} className="rotate-90" />
        </button>
        {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`w-8 h-8 rounded-xl text-xs font-black transition-all border ${
              page === p
                ? 'bg-[#4B39EF] text-white border-[#4B39EF] shadow-lg'
                : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'
            }`}
          >
            {p}
          </button>
        ))}
        <button
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronDown size={14} className="-rotate-90" />
        </button>
      </div>
    </div>
  );
}
