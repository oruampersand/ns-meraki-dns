# ns-meraki-dns

Web app Flask pour gérer le Local DNS des MX Meraki (enregistrements de type A uniquement : l'API Meraki ne gère pas les CNAME).

## Lancer

```
.venv/bin/pip install -r requirements.txt
cp .env.example .env && cp config.yml.example config.yml   # puis renseigner API_KEY, ORG_ID, profile
.venv/bin/python app.py                                    # http://127.0.0.1:5050
```

Le port 5050 est volontaire : 5000 est pris par AirPlay sur macOS (réponse 403 `AirTunes`).

## Architecture

- `config.yml` (**ignoré par git**, modèle : `config.yml.example`) est la source de vérité : `profile` + liste `records` (`hostname`, `type`, `address`).
- `app.py` : routes Flask. Ajout/modification/suppression ne modifient que `config.yml`. `/push` (GET) renvoie le fragment HTML du plan, `/push` (POST) l'applique.
- `meraki_dns.py` : accès à l'API Meraki (SDK `meraki`) et logique de synchro : `load_desired` -> `diff_records` -> `plan_config` -> `execute_plan`. Lit `API_KEY` et `ORG_ID` dans `.env` à l'import.
- `templates/` : `index.html` (liste + modals `<dialog>` création/modification/suppression/push, JS inline), `push_plan.html` (fragment du plan), `base.html`.

## Règles importantes

- La synchro est **destructive** : un enregistrement présent sur Meraki dans le profil du YAML mais absent du YAML est supprimé. Les autres profils ne sont jamais touchés.
- Toute écriture vers Meraki passe par le plan + une modal de confirmation. Ne jamais appliquer sans confirmation.
- `meraki_dns` est importé tardivement (`_meraki()` dans `app.py`) pour que la liste fonctionne sans clé API.
- Ne pas se connecter à l'org Meraki réelle pour tester, même en lecture. Tester avec un faux module `meraki_dns` et une copie de `config.yml` (client de test Flask).
- Les hostnames sont comparés sans tenir compte de la casse.
- Dans les templates Jinja, utiliser `plan["update"]` et non `plan.update` (collision avec `dict.update`).
- L'app n'a ni authentification ni CSRF : elle écoute sur 127.0.0.1 uniquement, ne pas l'exposer.
- Ne jamais committer `.env` ni `config.yml`.
