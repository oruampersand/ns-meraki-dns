// Utilitaires partagés par toutes les pages
const $ = (id) => document.getElementById(id);

// Fermeture des modals : [data-close], clic sur le fond
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-close]")) e.target.closest("dialog").close();
  else if (e.target instanceof HTMLDialogElement) e.target.close();
});

// Envoie un formulaire en fetch ; recharge la page si ok, sinon affiche l'erreur dans errorBox
async function submitJson(form, url, errorBox) {
  errorBox.hidden = true;
  let resp, data;
  try {
    resp = await fetch(url, {method: "POST", body: new FormData(form)});
    data = await resp.json();
  } catch (err) {
    data = {error: "Erreur : " + err};
  }
  if (resp && resp.ok) { location.reload(); return; }
  errorBox.textContent = data.error || "Erreur inconnue.";
  errorBox.hidden = false;
}
