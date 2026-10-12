/** Administrare (adm.*) și tab-ul Utilizatori (ut.*): rolurile date în aplicație, nu în AD (09.10.2026). */
export const utilizatori = {
  "pagini.administrare.nume_meniu": ["Administrare", "Administration"],
  "pagini.administrare.titlu": ["Administrare", "Administration"],
  "pagini.administrare.descriere": ["Setările aplicației, doar pentru administratori. Deocamdată: cine are acces și cu ce rol.", "The application settings, for administrators only. For now: who has access and with which role."],
  "adm.tab.utilizatori": ["Utilizatori", "Users"],

  "ut.intro": ["Parola o verifică Active Directory; rolul îl dai aici. Un cont apare aici automat după prima logare reușită cu contul de rețea, fără rol: până îi dai unul, nu poate intra. <b>Analistul</b> vede toate datele; <b>administratorul</b> vede în plus joburile, rulările manuale și această pagină. Schimbarea se aplică imediat, fără ca utilizatorul să se delogheze.", "Active Directory checks the password; you give the role here. An account appears here automatically after its first successful sign-in with the network account, without a role: until you give it one, it cannot get in. The <b>analyst</b> sees all the data; the <b>administrator</b> also sees the jobs, the manual runs and this page. The change applies immediately, without the user signing out."],
  "ut.filtru.toti": ["Toți ({n})", "All ({n})"],
  "ut.filtru.asteapta": ["Așteaptă un rol ({n})", "Waiting for a role ({n})"],
  "ut.gol_asteapta": ["Niciun cont nu așteaptă un rol.", "No account is waiting for a role."],
  "ut.nedisponibil": ["Baza nu are încă tabela <code>utilizatori</code>. Se creează cu <code>db/migration_040_utilizatori.sql</code>.", "The database does not have the <code>utilizatori</code> table yet. It is created by <code>db/migration_040_utilizatori.sql</code>."],

  "ut.col.utilizator": ["Utilizator", "Username"],
  "ut.col.nume": ["Nume", "Name"],
  "ut.col.rol": ["Rol", "Role"],
  "ut.col.activ": ["Activ", "Active"],
  "ut.col.ultima_logare": ["Ultima logare", "Last sign-in"],
  "ut.col.ultima_logare_t": ["Ultima verificare reușită a parolei în Active Directory, chiar dacă apoi contul n-a avut rol.", "The last successful password check in Active Directory, even if the account then had no role."],
  "ut.col.modificat": ["Ultima schimbare", "Last change"],
  "ut.col.creat": ["Prima logare", "First sign-in"],

  "ut.fara_rol": ["— fără rol (blocat) —", "— no role (blocked) —"],
  "ut.tu": ["tu", "you"],
  "ut.propriul_cont_t": ["Nu îți poți schimba singur rolul sau starea: cere altui administrator.", "You cannot change your own role or status: ask another administrator."],
  "ut.stare.asteapta": ["așteaptă rol", "waiting for role"],
  "ut.stare.dezactivat": ["dezactivat", "deactivated"],
  "ut.de": ["de {cine}", "by {cine}"],
  "ut.salvat": ["Salvat: {u}", "Saved: {u}"],

  "ut.eroare.propriul_cont": ["Nu îți poți retrage singur drepturile de administrator.", "You cannot remove your own administrator rights."],
  "ut.eroare.ultimul_admin": ["E ultimul administrator activ. Dă întâi altcuiva rolul de administrator.", "This is the last active administrator. Give someone else the administrator role first."],
  "ut.eroare.inexistent": ["Contul nu mai există. Reîncarcă pagina.", "The account no longer exists. Reload the page."],
  "ut.eroare.interzis": ["Doar un administrator poate schimba rolurile.", "Only an administrator can change roles."],
  "ut.eroare.generic": ["Schimbarea nu s-a salvat ({cod}).", "The change was not saved ({cod})."],
} as const
