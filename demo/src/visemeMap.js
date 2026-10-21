// Mapeo de los 22 visemas de Azure TTS (visemeId 0-21) a las 8 formas de boca de Robin.
export const VISEME_TO_MOUTH = Object.freeze({
  0: 'REST',
  21: 'MBP',
  18: 'FV',
  1: 'A', 2: 'A', 9: 'A', 11: 'A',
  4: 'E', 5: 'E', 6: 'E', 12: 'E', 13: 'E',
  3: 'O', 8: 'O', 10: 'O',
  7: 'U',
  14: 'CONS', 15: 'CONS', 16: 'CONS', 17: 'CONS', 19: 'CONS', 20: 'CONS',
});

/** ms a partir de ticks de 100 ns (formato audioOffset de Azure). */
export const ticksToMs = (ticks) => ticks / 10000;
