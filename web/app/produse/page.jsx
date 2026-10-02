import { Suspense } from "react";
import Antet from "@/components/Antet";
import ProduseLibra from "@/components/produse/ProduseLibra";

export const metadata = { title: "Produse & prețuri · Marketing Command Center" };

export default function Pagina() {
  return (
    <>
      <Antet id="produse" />
      {/* useSearchParams cere o graniță Suspense la prerandare */}
      <Suspense fallback={<section><p className="note">se încarcă…</p></section>}>
        <ProduseLibra />
      </Suspense>
    </>
  );
}
