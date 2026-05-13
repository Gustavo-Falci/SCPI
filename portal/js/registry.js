// Shared registry para FAB mobile — evita import circular entre main.js e tabs
let _createFn = null;
export const setCreate = fn => { _createFn = fn; };
export const clearCreate = () => { _createFn = null; };
export const runCreate = () => _createFn?.();
export const hasCreate = () => !!_createFn;
