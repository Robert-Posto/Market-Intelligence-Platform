import { redirect } from "next/navigation";

// Overview nu e portat încă: prima pagină a aplicației Next.js e Produse & prețuri.
export default function Acasa() {
  redirect("/produse");
}
