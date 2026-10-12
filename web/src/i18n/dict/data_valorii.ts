/** Data unei valori de referință (dv.*): din citat, a documentului, a extragerii. */
export const data_valorii = {
  "dv.citat": ["din citat: {data}", "from the quote: {data}"],
  "dv.document": ["document: {data}", "document: {data}"],
  "dv.extragere": ["extras la {data}", "extracted on {data}"],
  "dv.titlu": ["Data din citat: {citat} · data documentului: {document} ({sursa}) · extras la: {extragere}", "Date in the quote: {citat} · document date: {document} ({sursa}) · extracted on: {extragere}"],
  "dv.sursa.text": ["din textul documentului", "from the document text"],
  "dv.sursa.pdf_modificat": ["metadatele PDF, ultima modificare", "PDF metadata, last modified"],
  "dv.sursa.pdf_creat": ["metadatele PDF, creare", "PDF metadata, created"],
  "dv.sursa.http": ["data trimisă de serverul băncii", "date sent by the bank's server"],
} as const
