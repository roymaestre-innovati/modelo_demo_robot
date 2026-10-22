import robin from './robin.js';
import ignis from './ignis.js';

export const PROFILES = { robin, ignis };
export const DEFAULT_PROFILE = 'robin';

/** Perfil elegido con ?model=robin|ignis (por defecto robin). */
export function profileFromUrl(search = window.location.search) {
  const id = new URLSearchParams(search).get('model') ?? DEFAULT_PROFILE;
  return PROFILES[id] ?? PROFILES[DEFAULT_PROFILE];
}
