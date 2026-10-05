import { Suspense } from "react";
import Antet from "@/components/Antet";
import ProduseConcurenta from "@/components/concurenta/ProduseConcurenta";

export const metadata = { title: "Descoperă concurența · Marketing Command Center" };

export default function Pagina() {
  return (
    <>
      <Antet id="concurenta" />
      <Suspense fallback={<section><p className="note">se încarcă…</p></section>}>
        <ProduseConcurenta />
      </Suspense>
    </>
  );
}
