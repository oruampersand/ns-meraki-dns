from dotenv import load_dotenv
from pathlib import Path
import ipaddress
import os
import meraki

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

API_KEY = os.environ["API_KEY"]
ORG_ID = os.environ["ORG_ID"]

dashboard = meraki.DashboardAPI(
    API_KEY,
    suppress_logging=True
)


def _items(resp):
    """Normalise les réponses de liste (liste brute ou {'items': [...]})."""
    if isinstance(resp, dict):
        return resp.get("items", [])
    return resp or []


# --- Profils ---

# Récupère les profils (liste de dicts)
def get_profiles():
    return _items(dashboard.appliance.getOrganizationApplianceDnsLocalProfiles(ORG_ID))


def _check_profile_name(name, profiles, current_id=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("Le nom du profil est obligatoire.")
    if any(p["name"].lower() == name.lower() and p["profileId"] != current_id for p in profiles):
        raise ValueError(f"Un profil nommé « {name} » existe déjà.")
    return name


# Créer un profil
def create_profile(name):
    name = _check_profile_name(name, get_profiles())
    return dashboard.appliance.createOrganizationApplianceDnsLocalProfile(ORG_ID, name)


# Renommer un profil
def update_profile(profile_id, name):
    name = _check_profile_name(name, get_profiles(), current_id=profile_id)
    return dashboard.appliance.updateOrganizationApplianceDnsLocalProfile(ORG_ID, profile_id, name)


# Supprimer un profil (refusé tant qu'il a des enregistrements ou des réseaux associés)
def delete_profile(profile_id):
    if get_records(profile_id):
        raise ValueError("Ce profil contient encore des enregistrements : supprimez-les d'abord.")
    if any(a.get("profile", {}).get("id") == profile_id for a in get_assignments()):
        raise ValueError("Ce profil est associé à un ou plusieurs réseaux : dissociez-le d'abord.")
    dashboard.appliance.deleteOrganizationApplianceDnsLocalProfile(ORG_ID, profile_id)


# Profils avec le nombre d'enregistrements et de réseaux associés
def list_profile_summaries():
    records = get_records()
    assignments = get_assignments()
    rows = []
    for p in get_profiles():
        rows.append({
            "id": p["profileId"],
            "name": p["name"],
            "records": sum(1 for r in records if r.get("profile", {}).get("id") == p["profileId"]),
            "networks": sum(1 for a in assignments if a.get("profile", {}).get("id") == p["profileId"]),
        })
    return sorted(rows, key=lambda r: r["name"].lower())


# --- Enregistrements ---

# Récupère les enregistrements, filtrés par profil si profile_id est fourni
def get_records(profile_id=None):
    records = _items(dashboard.appliance.getOrganizationApplianceDnsLocalRecords(ORG_ID))
    if profile_id:
        records = [r for r in records if r.get("profile", {}).get("id") == profile_id]
    return records


def _check_record(hostname, address, siblings, current_id=None):
    hostname = (hostname or "").strip()
    address = (address or "").strip()
    if not hostname or not address:
        raise ValueError("Hostname et adresse sont obligatoires.")
    try:
        ipaddress.IPv4Address(address)
    except ValueError:
        raise ValueError(f"Adresse IPv4 invalide : {address}") from None
    if any(r["hostname"].lower() == hostname.lower() and r["recordId"] != current_id for r in siblings):
        raise ValueError(f"{hostname} existe déjà dans ce profil.")
    return hostname, address


# Créer un enregistrement (type A uniquement, pas de CNAME via l'API)
def create_record(profile_id, hostname, address):
    if not any(p["profileId"] == profile_id for p in get_profiles()):
        raise ValueError("Profil introuvable.")
    hostname, address = _check_record(hostname, address, get_records(profile_id))
    return dashboard.appliance.createOrganizationApplianceDnsLocalRecord(
        ORG_ID, hostname, address, {"id": profile_id}
    )


# Mettre à jour un enregistrement (hostname et adresse)
def update_record(record_id, hostname, address):
    record = next((r for r in get_records() if r["recordId"] == record_id), None)
    if not record:
        raise ValueError("Enregistrement introuvable.")
    siblings = get_records(record["profile"]["id"])
    hostname, address = _check_record(hostname, address, siblings, current_id=record_id)
    return dashboard.appliance.updateOrganizationApplianceDnsLocalRecord(
        ORG_ID, record_id, hostname=hostname, address=address
    )


# Supprimer un enregistrement
def delete_record(record_id):
    dashboard.appliance.deleteOrganizationApplianceDnsLocalRecord(ORG_ID, record_id)


# --- Réseaux ---

# Réseaux de l'org ayant un MX (seuls ceux-ci supportent le Local DNS)
def get_networks():
    networks = dashboard.organizations.getOrganizationNetworks(ORG_ID, total_pages="all")
    return [n for n in _items(networks) if "appliance" in n.get("productTypes", [])]


# Associations réseau <-> profil existantes
def get_assignments():
    return _items(dashboard.appliance.getOrganizationApplianceDnsLocalProfilesAssignments(ORG_ID))


# Réseaux avec leur profil associé (ou None) : liste de dicts pour l'affichage
def list_network_profiles():
    names = {p["profileId"]: p["name"] for p in get_profiles()}
    by_network = {a.get("network", {}).get("id"): a for a in get_assignments()}
    rows = []
    for n in get_networks():
        a = by_network.get(n["id"])
        profile_id = a.get("profile", {}).get("id") if a else None
        rows.append({
            "id": n["id"],
            "name": n["name"],
            "profile_id": profile_id,
            "profile_name": names.get(profile_id, profile_id),
        })
    return sorted(rows, key=lambda r: r["name"].lower())


# Associe un profil à un réseau (refuse d'écraser une association existante)
def assign_profile(network_id, profile_id):
    if not any(n["id"] == network_id for n in get_networks()):
        raise ValueError("Réseau introuvable (ou sans appliance MX).")
    if not any(p["profileId"] == profile_id for p in get_profiles()):
        raise ValueError("Profil introuvable sur Meraki.")
    if any(a.get("network", {}).get("id") == network_id for a in get_assignments()):
        raise ValueError("Ce réseau a déjà un profil : dissociez-le d'abord.")
    dashboard.appliance.bulkOrganizationApplianceDnsLocalProfilesAssignmentsCreate(
        ORG_ID, [{"network": {"id": network_id}, "profile": {"id": profile_id}}]
    )


# Dissocie le profil d'un réseau
def unassign_profile(network_id):
    current = next((a for a in get_assignments() if a.get("network", {}).get("id") == network_id), None)
    if not current:
        raise ValueError("Ce réseau n'a pas de profil associé.")
    dashboard.appliance.createOrganizationApplianceDnsLocalProfilesAssignmentsBulkDelete(
        ORG_ID, [{"assignmentId": current["assignmentId"]}]
    )
