from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)


def _meraki():
    # Import tardif : meraki_dns lit la clé API à l'import, l'erreur est ainsi affichée dans la page.
    import meraki_dns
    return meraki_dns


def form(*names):
    return [request.form.get(n, "").strip() for n in names]


def run_json(action, ok_message):
    """Exécute une action Meraki depuis une modal (fetch) : JSON, la page se recharge si ok."""
    try:
        action()
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f"Erreur Meraki : {e}"), 502
    flash(ok_message, "ok")
    return jsonify(ok=True)


def run_redirect(action, ok_message, endpoint):
    try:
        action()
    except Exception as e:
        flash(f"Échec : {e}", "error")
    else:
        flash(ok_message, "ok")
    return redirect(url_for(endpoint))


def load(*loaders):
    """Appelle les fonctions de lecture Meraki ; en cas d'erreur renvoie des listes vides + le message."""
    try:
        m = _meraki()
        return [getattr(m, name)() for name in loaders], None
    except Exception as e:
        return [[] for _ in loaders], f"Impossible de lire Meraki : {e}"


# --- Enregistrements ---

@app.get("/")
def index():
    (records, profiles), error = load("get_records", "get_profiles")
    names = {p["profileId"]: p["name"] for p in profiles}
    for r in records:
        r["profile_id"] = r.get("profile", {}).get("id")
        r["profile_name"] = names.get(r["profile_id"], r["profile_id"])
    records.sort(key=lambda r: (r["profile_name"] or "").lower() + r["hostname"].lower())
    return render_template("index.html", records=records, profiles=profiles, error=error)


@app.post("/records")
def record_create():
    profile_id, hostname, address = form("profile_id", "hostname", "address")
    return run_json(lambda: _meraki().create_record(profile_id, hostname, address), f"{hostname} créé.")


@app.post("/records/<record_id>")
def record_update(record_id):
    hostname, address = form("hostname", "address")
    return run_json(lambda: _meraki().update_record(record_id, hostname, address), f"{hostname} modifié.")


@app.post("/records/<record_id>/delete")
def record_delete(record_id):
    return run_redirect(lambda: _meraki().delete_record(record_id), "Enregistrement supprimé.", "index")


# --- Profils ---

@app.get("/profiles")
def profiles():
    (rows,), error = load("list_profile_summaries")
    return render_template("profiles.html", profiles=rows, error=error)


@app.post("/profiles")
def profile_create():
    (name,) = form("name")
    return run_json(lambda: _meraki().create_profile(name), f"Profil {name} créé.")


@app.post("/profiles/<profile_id>")
def profile_update(profile_id):
    (name,) = form("name")
    return run_json(lambda: _meraki().update_profile(profile_id, name), f"Profil renommé en {name}.")


@app.post("/profiles/<profile_id>/delete")
def profile_delete(profile_id):
    return run_redirect(lambda: _meraki().delete_profile(profile_id), "Profil supprimé.", "profiles")


# --- Réseaux ---

@app.get("/networks")
def networks():
    (rows, profile_list), error = load("list_network_profiles", "get_profiles")
    return render_template("networks.html", networks=rows, profiles=profile_list, error=error)


@app.post("/networks/<network_id>/assign")
def network_assign(network_id):
    (profile_id,) = form("profile_id")
    return run_redirect(lambda: _meraki().assign_profile(network_id, profile_id),
                        "Profil associé au réseau.", "networks")


@app.post("/networks/<network_id>/unassign")
def network_unassign(network_id):
    return run_redirect(lambda: _meraki().unassign_profile(network_id),
                        "Profil dissocié du réseau.", "networks")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
