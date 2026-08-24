from dotenv import load_dotenv
from pathlib import Path
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


# Liste les réseaux
def list_networks():
    networks = dashboard.organizations.getOrganizationNetworks(ORG_ID)
    for network in networks:
        print(network["id"], "|", network["name"], "|", network.get("productTypes"))


# Liste les profils
def list_profiles():
    profiles = dashboard.appliance.getOrganizationApplianceDnsLocalProfiles(ORG_ID)
    for profile in profiles:
        print(profile[0], "|", profile[1])


# Liste les enregistrements DNS
def list_records():
    records = dashboard.appliance.getOrganizationApplianceDnsLocalRecords(ORG_ID)
    for record in records:
        print(record[0], "|", record[1], "|", record[2], "|", record[3])


# Lire et afficher config.yml
def read_config(configfile):
    with open(configfile, "r", encoding="utf8") as f:
        filecontent = yaml.safe_load(f)
    print(filecontent)
    return filecontent


# Appliquer la config
def apply_config(configfile):
    read_config(configfile)


# Ajouter enregistrement
def add_record(configfile, new_data):
    with open(configfile, "+a", encoding="uft8") as f:
        f.seek(0)
        existing_data = yaml.safe_load(f) or []
        existing_data.append(new_data)
        f.seek(0)
        yaml.dump(existing_data, f, default_flow_style=False)


if __name__ == '__main__':
    list_profiles()
