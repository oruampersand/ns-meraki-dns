# ns-meraki-dns

Web app Flask pour gérer le Local DNS des MX Meraki : enregistrements, profils, association profil <-> réseau. Enregistrements de type A uniquement (l'API Meraki ne gère pas les CNAME).

## Lancer

```
.venv/bin/pip install -r requirements.txt
cp .env.example .env                                       # puis renseigner API_KEY et ORG_ID
.venv/bin/python app.py                                    # http://127.0.0.1:5050
```

Le port 5050 est volontaire : 5000 est pris par AirPlay sur macOS (réponse 403 `AirTunes`).

## Architecture

- **Meraki est la source de vérité** : plus de fichier YAML. Chaque page lit en direct sur Meraki et chaque action écrit immédiatement, après confirmation en modal.
- `app.py` : routes Flask. Pages : `/` (enregistrements, filtre par profil), `/profiles` (créer, renommer, supprimer), `/networks` (associer/dissocier). Les modals de création/modification passent par `fetch` (JSON, `run_json`), les suppressions et associations par un POST classique (`run_redirect`).
- `meraki_dns.py` : accès à l'API Meraki (SDK `meraki`) et validations (`ValueError` = erreur affichable à l'utilisateur). Lit `API_KEY` et `ORG_ID` dans `.env` à l'import.
- `templates/` : `base.html` (nav, styles), `index.html`, `profiles.html`, `networks.html` ; `static/app.js` : fermeture des modals et `submitJson`.

## Règles importantes

- Toute écriture vers Meraki passe par une modal de confirmation. Ne jamais écrire sans confirmation.
- `delete_profile` refuse un profil qui a encore des enregistrements ou des réseaux associés ; `assign_profile` refuse d'écraser un profil déjà associé (dissocier d'abord). Ces garde-fous sont volontaires (comportement de l'API non vérifié).
- Hostnames et noms de profil sont comparés sans tenir compte de la casse.
- `meraki_dns` est importé tardivement (`_meraki()` dans `app.py`) : une clé API absente ou invalide s'affiche dans la page au lieu de planter le démarrage.
- Ne pas se connecter à l'org Meraki réelle pour tester, même en lecture. Tester avec un faux `meraki_dns.dashboard` (objet avec les mêmes méthodes, clé API factice) et le client de test Flask.
- L'app n'a ni authentification ni CSRF : elle écoute sur 127.0.0.1 uniquement, ne pas l'exposer.
- Ne jamais committer `.env`.
