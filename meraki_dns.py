from dotenv import load_dotenv
from pathlib import Path
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


# Liste les réseaux
def list_networks():
    networks = dashboard.organizations.getOrganizationNetworks(ORG_ID)
    for network in networks:
        print(network["id"], "|", network["name"], "|", network.get("productTypes"))


# Liste les enregistrements DNS
def list_records():
    records = dashboard.appliance.getOrganizationApplianceDnsLocalRecords(ORG_ID)
    for record in records:
        print(record[0], "|", record[1], "|", record[2], "|", record[3])


if __name__ == '__main__':
    list_networks()
