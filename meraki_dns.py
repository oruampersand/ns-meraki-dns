from dotenv import load_dotenv
from pathlib import Path
import ipaddress
import os
import meraki
import yaml

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


# Récupère les profils (liste de dicts)
def get_profiles():
    return _items(dashboard.appliance.getOrganizationApplianceDnsLocalProfiles(ORG_ID))


# Récupère les enregistrements, filtrés par profil si profile_id est fourni
def get_records(profile_id=None):
    records = _items(dashboard.appliance.getOrganizationApplianceDnsLocalRecords(ORG_ID))
    if profile_id:
        records = [r for r in records if r.get("profile", {}).get("id") == profile_id]
    return records


# Créer un profil
def create_profile(name):
    return dashboard.appliance.createOrganizationApplianceDnsLocalProfile(ORG_ID, name)


# Créer un enregistrement (type A uniquement, pas de CNAME via l'API)
def create_record(profile_id, hostname, address):
    ipaddress.IPv4Address(address)  # valide l'IP, lève ValueError sinon
    return dashboard.appliance.createOrganizationApplianceDnsLocalRecord(
        ORG_ID, hostname, address, {"id": profile_id}
    )


# Mettre à jour un enregistrement (hostname et/ou address)
def update_record(record_id, hostname=None, address=None):
    changes = {}
    if hostname:
        changes["hostname"] = hostname
    if address:
        ipaddress.IPv4Address(address)
        changes["address"] = address
    if not changes:
        return None
    return dashboard.appliance.updateOrganizationApplianceDnsLocalRecord(ORG_ID, record_id, **changes)


# Supprimer un enregistrement
def delete_record(record_id):
    dashboard.appliance.deleteOrganizationApplianceDnsLocalRecord(ORG_ID, record_id)


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
        raise ValueError("Profil introuvable sur Meraki (poussez d'abord les enregistrements pour le créer).")
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


# Lire config.yml
def read_config(configfile):
    with open(configfile, "r", encoding="utf8") as f:
        return yaml.safe_load(f)


# Valide config.yml et renvoie (nom du profil, {hostname_minuscule: (hostname, address)})
def load_desired(configfile):
    cfg = read_config(configfile) or {}
    profile_name = cfg.get("profile")
    if not profile_name:
        raise ValueError("'profile' manquant dans le fichier de config")
    desired = {}
    for rec in cfg.get("records") or []:
        hostname = str(rec.get("hostname") or "").strip()
        address = str(rec.get("address") or "").strip()
        if not hostname or not address:
            raise ValueError(f"Enregistrement incomplet : {rec}")
        if str(rec.get("type") or "A").upper() != "A":
            raise ValueError(f"{hostname} : seul le type A est supporté par l'API")
        ipaddress.IPv4Address(address)
        if hostname.lower() in desired:
            raise ValueError(f"{hostname} : doublon dans le fichier de config")
        desired[hostname.lower()] = (hostname, address)
    return profile_name, desired


# Compare le fichier (desired) à Meraki (existing, liste de dicts) -> (create, update, delete)
def diff_records(desired, existing):
    current = {r["hostname"].lower(): r for r in existing}
    create = [v for k, v in desired.items() if k not in current]
    update = [(current[k], v[1]) for k, v in desired.items()
              if k in current and current[k]["address"] != v[1]]
    delete = [r for k, r in current.items() if k not in desired]
    return create, update, delete


# Calcule le plan de synchro entre config.yml et Meraki (lecture seule côté Meraki)
def plan_config(configfile):
    profile_name, desired = load_desired(configfile)
    profile = next((p for p in get_profiles() if p["name"] == profile_name), None)
    existing = get_records(profile["profileId"]) if profile else []
    create, update, delete = diff_records(desired, existing)
    return {
        "profile_name": profile_name,
        "profile_id": profile["profileId"] if profile else None,
        "create": create,
        "update": update,
        "delete": delete,
        "empty_config": not desired,
    }


def plan_is_empty(plan):
    return bool(plan["profile_id"]) and not (plan["create"] or plan["update"] or plan["delete"])


# Exécute un plan : crée le profil si besoin, puis créations, mises à jour, suppressions
def execute_plan(plan):
    profile_id = plan["profile_id"] or create_profile(plan["profile_name"])["profileId"]
    for hostname, address in plan["create"]:
        create_record(profile_id, hostname, address)
    for rec, address in plan["update"]:
        update_record(rec["recordId"], address=address)
    for rec in plan["delete"]:
        delete_record(rec["recordId"])
