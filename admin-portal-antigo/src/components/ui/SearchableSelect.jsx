import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Search, X } from 'lucide-react';

export function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = 'Selecione...',
  searchable = true,
  className = '',
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [openUp, setOpenUp] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleOpen = () => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      setOpenUp(spaceBelow < 220);
    }
    setOpen((o) => !o);
    setSearch('');
  };

  const filtered = options.filter((o) =>
    o.label.toLowerCase().includes(search.toLowerCase())
  );
  const selected = options.find((o) => o.value === value);

  const handleSelect = (opt) => {
    onChange(opt.value);
    setSearch('');
    setOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange('');
    setSearch('');
  };

  return (
    <div ref={ref} className={`relative ${className}`}>
      <div
        onClick={handleOpen}
        className="w-full bg-[#1A1C1E] border border-white/10 rounded-xl px-4 py-3 pr-10 text-sm text-white outline-none focus:border-[#4B39EF] transition-all cursor-pointer flex items-center justify-between gap-2 select-none"
        style={{ minHeight: '46px' }}
      >
        <span className={selected ? 'text-white' : 'text-gray-600'}>
          {selected ? selected.label : placeholder}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          {selected && (
            <button
              type="button"
              onClick={handleClear}
              className="w-5 h-5 flex items-center justify-center text-gray-500 hover:text-white transition-colors"
            >
              <X size={12} />
            </button>
          )}
          <ChevronDown size={14} className={`text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {open && (
        <div className={`absolute z-50 w-full bg-[#1A1C1E] border border-white/10 rounded-xl shadow-2xl overflow-hidden ${openUp ? 'bottom-full mb-1.5' : 'top-full mt-1.5'}`}>
          {searchable && (
            <div className="p-2 border-b border-white/5">
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  autoFocus
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Pesquisar..."
                  className="w-full bg-black/30 rounded-lg pl-8 pr-3 py-2 text-sm text-white outline-none placeholder:text-gray-600 border border-white/5 focus:border-[#4B39EF] transition-all"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </div>
          )}
          <div className="max-h-48 overflow-y-auto">
            <div
              onClick={() => handleSelect({ value: '', label: placeholder })}
              className="px-4 py-2.5 text-sm text-gray-500 hover:bg-white/5 cursor-pointer italic transition-colors"
            >
              {placeholder}
            </div>
            {filtered.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-600 text-center">Nenhum resultado</div>
            ) : (
              filtered.map((opt) => (
                <div
                  key={opt.value}
                  onClick={() => handleSelect(opt)}
                  className={`px-4 py-2.5 text-sm cursor-pointer transition-colors ${opt.value === value ? 'bg-[#4B39EF]/20 text-[#7B6EFF] font-black' : 'text-white hover:bg-white/5'}`}
                >
                  {opt.label}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
