# ns-meraki-dns

Web app pour gérer le Local DNS des MX Meraki : enregistrements, profils et association profil <-> réseau.

Meraki est la source de vérité. Chaque page lit directement sur Meraki et chaque action s'applique immédiatement, après confirmation dans une modal.

## Prérequis

- Python 3.10 ou plus (le code est testé avec 3.14)
- Une clé API Meraki avec les droits d'écriture sur l'organisation
- Des MX en firmware 19.1 ou plus (requis pour le Local DNS)

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Renseigner ensuite `.env` :

```
API_KEY = "votre clé API Meraki"
ORG_ID = "l'ID de l'organisation"
```

`.env` est ignoré par git : ne jamais le committer.

## Lancement

```bash
.venv/bin/python app.py
```

Ouvrir http://127.0.0.1:5050 et arrêter le serveur avec `Ctrl+C`.

Le port 5050 est volontaire : sur macOS, le port 5000 est pris par le récepteur AirPlay et répond 403.

L'app n'a ni authentification ni protection CSRF. Elle écoute uniquement sur 127.0.0.1 : ne pas l'exposer sur le réseau.

## Utilisation

- **Enregistrements** (`/`) : liste des enregistrements de tous les profils, avec un filtre par profil. Un clic sur une ligne permet de modifier ou supprimer. « + Ajouter » crée un enregistrement dans le profil choisi.
- **Profils** (`/profiles`) : créer, renommer et supprimer un profil. La suppression est refusée tant que le profil contient des enregistrements ou qu'un réseau y est associé.
- **Réseaux** (`/networks`) : liste des réseaux ayant un MX et de leur profil. On peut associer un profil à un réseau, ou le dissocier. Un réseau qui a déjà un profil doit être dissocié avant d'en recevoir un autre.

Seuls les enregistrements de type A (IPv4) sont gérés : l'API Meraki ne permet pas de créer des CNAME.

## Références

- Doc API Meraki : https://developer.cisco.com/meraki/api-v1/
- Création d'un profil Local DNS : https://developer.cisco.com/meraki/api-v1/create-organization-appliance-dns-local-profile/
