/** Texte adăugate la mutarea paginii în React (în afara extragerii din 02.10.2026). */
export const extra_document = {
  /* `pdf.stare.eroare_incarcare` nu se poate folosi prin <T>: parametrii nu intră
     în atribute (legătura rămânea href="{url}") și target/rel se pierd. Legătura
     spre original se face în cod și intră ca parametru {link}. */
  "pdf.stare.eroare_titlu": ["Documentul nu s-a putut încărca", "The document could not be loaded"],
  "pdf.stare.eroare_manual": ["Poți deschide {link} și căuta manual: <b>{citat}</b>, pagina {pagina}.", "You can open {link} and search by hand: <b>{citat}</b>, page {pagina}."],
  "pdf.stare.eroare_manual_fara_citat": ["Poți deschide {link}, la pagina {pagina}.", "You can open {link}, at page {pagina}."],
  "pdf.stare.eroare_link_original": ["originalul la bancă", "the original on the bank's website"],
  // singularele: un document de o pagină dădea „toate 1 paginile”, „1 pagini.”
  "pdf.nav.singura_pagina": ["singura pagină", "the only page"],
  "pdf.citat.total_pagini_1": ["O pagină.", "1 page."],
  "pdf.citat.negasit_in_document_1": ["<b>{citat}</b> nu s-a regăsit pe singura pagină a documentului.", "<b>{citat}</b> was not found on the document's only page."],
} as const
