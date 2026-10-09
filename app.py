import ipaddress
import os
from pathlib import Path

import yaml
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.yml"

app = Flask(__name__)
app.secret_key = os.urandom(24)


def load_config():
    """Renvoie (nom du profil, liste de {hostname, type, address}) depuis config.yml."""
    with open(CONFIG_FILE, "r", encoding="utf8") as f:
        cfg = yaml.safe_load(f) or {}
    records = [
        {"hostname": str(r["hostname"]), "type": "A", "address": str(r["address"])}
        for r in cfg.get("records") or []
        if r.get("hostname") and r.get("address")  # ignore les entrées vides du modèle
    ]
    return cfg.get("profile"), records


def save_config(profile, records):
    tmp = CONFIG_FILE.with_suffix(".yml.tmp")
    with open(tmp, "w", encoding="utf8") as f:
        yaml.safe_dump({"profile": profile, "records": records}, f, sort_keys=False)
    tmp.replace(CONFIG_FILE)


def find(records, hostname):
    return next((r for r in records if r["hostname"].lower() == hostname.lower()), None)


def validate(hostname, address, records, current=None):
    """Renvoie un message d'erreur, ou None si valide."""
    if not hostname or not address:
        return "Hostname et adresse sont obligatoires."
    try:
        ipaddress.IPv4Address(address)
    except ValueError:
        return f"Adresse IPv4 invalide : {address}"
    other = find(records, hostname)
    if other and other is not current:
        return f"{hostname} existe déjà."
    return None


@app.get("/")
def index():
    profile, records = load_config()
    return render_template("index.html", profile=profile, records=records)


def record_from_form():
    return {k: request.form.get(k, "").strip() for k in ("hostname", "address")}


@app.post("/record")
def create_record():
    profile, records = load_config()
    form = record_from_form()
    error = validate(form["hostname"], form["address"], records)
    if error:
        return jsonify(error=error), 400
    records.append({"hostname": form["hostname"], "type": "A", "address": form["address"]})
    save_config(profile, records)
    flash(f"{form['hostname']} ajouté (pas encore poussé vers Meraki).", "ok")
    return jsonify(ok=True)


@app.post("/record/<hostname>")
def edit_record(hostname):
    profile, records = load_config()
    record = find(records, hostname)
    if not record:
        return jsonify(error=f"{hostname} introuvable."), 404
    form = record_from_form()
    error = validate(form["hostname"], form["address"], records, current=record)
    if error:
        return jsonify(error=error), 400
    record.update(form)
    save_config(profile, records)
    flash(f"{form['hostname']} modifié (pas encore poussé vers Meraki).", "ok")
    return jsonify(ok=True)


@app.post("/record/<hostname>/delete")
def delete_record(hostname):
    profile, records = load_config()
    record = find(records, hostname)
    if record:
        records.remove(record)
        save_config(profile, records)
        flash(f"{hostname} supprimé (pas encore poussé vers Meraki).", "ok")
    return redirect(url_for("index"))


def _meraki():
    # Import tardif : meraki_dns lit la clé API à l'import, la liste fonctionne donc sans.
    import meraki_dns
    return meraki_dns


@app.get("/push")
def push_preview():
    """Fragment HTML du plan de synchro (lecture seule côté Meraki), affiché dans la modal."""
    try:
        m = _meraki()
        plan = m.plan_config(CONFIG_FILE)
    except Exception as e:
        return render_template("push_plan.html", error=str(e))
    return render_template("push_plan.html", plan=plan, empty=m.plan_is_empty(plan))


@app.post("/push")
def push_apply():
    try:
        m = _meraki()
        plan = m.plan_config(CONFIG_FILE)  # recalculé : on n'applique que l'état actuel
        m.execute_plan(plan)
    except Exception as e:
        flash(f"Échec de la synchronisation : {e}", "error")
    else:
        flash("Synchronisation vers Meraki terminée.", "ok")
    return redirect(url_for("index"))


@app.get("/networks")
def networks():
    """Réseaux et profils associés, lus en direct sur Meraki."""
    try:
        m = _meraki()
        rows, profiles = m.list_network_profiles(), m.get_profiles()
    except Exception as e:
        flash(f"Impossible de lire les réseaux : {e}", "error")
        return redirect(url_for("index"))
    return render_template("networks.html", networks=rows, profiles=profiles)


@app.post("/networks/<network_id>/assign")
def network_assign(network_id):
    try:
        _meraki().assign_profile(network_id, request.form.get("profile_id", ""))
    except Exception as e:
        flash(f"Échec de l'association : {e}", "error")
    else:
        flash("Profil associé au réseau.", "ok")
    return redirect(url_for("networks"))


@app.post("/networks/<network_id>/unassign")
def network_unassign(network_id):
    try:
        _meraki().unassign_profile(network_id)
    except Exception as e:
        flash(f"Échec de la dissociation : {e}", "error")
    else:
        flash("Profil dissocié du réseau.", "ok")
    return redirect(url_for("networks"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
