/** Texte adăugate la mutarea paginii în React (în afara extragerii din 02.10.2026). */
export const extra_context_istoric = {
  // `context.card.schimbare` are clasa în parametru (class="{cls}"), dar <T> pune parametrii doar în text, nu în
  // atribute: săgeata ar fi ieșit fără culoare. Aici schimbarea colorată vine întreagă, ca parametru.
  "context.card.fata_de": ["{schimbare} față de {zi}", "{schimbare} since {zi}"],
  // singularele: Exim are o singură schimbare la dobânzi și o singură scumpire la comisioane (05.10.2026);
  // vechiul text spunea „1 schimbări”, „↑ 1 scumpiri”
  "istoric.titlu_numar_1": ["{n} schimbare de preț în filtrul curent", "{n} price change in the current filter"],
  "istoric.tile_scumpiri_1": ["↑ {n} scumpire", "↑ {n} increase"],
  "istoric.tile_ieftiniri_1": ["↓ {n} ieftinire", "↓ {n} decrease"],
  "istoric.grup_schimbari_1": ["{n} schimbare", "{n} change"],
} as const
