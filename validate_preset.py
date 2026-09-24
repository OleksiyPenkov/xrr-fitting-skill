#!/usr/bin/env python3
"""Validate an XRR fitting preset and its substrate library.

Three layers of checking:

  1. JSON Schema  - shape, types, required keys, no stray keys, for both the
                    preset and the substrate library it points at.
  2. Semantics    - what a schema cannot express: ordering of bounds, start
                    values inside their own bounds, the substrate id resolving,
                    and the acceptance block agreeing with the chi2 block.
  3. Materials    - optionally, which material names the engine's Henke table
                    currently knows. That table is per-installation and
                    extensible, so a missing name is never an error here: it
                    means the operator supplies the entry. Entries that declare
                    `requires_table_entry` are expected to be missing.

Exit status is 0 only when there are no errors. Warnings do not fail the run.

    python validate_preset.py presets/csmic-empyrean.json
    python validate_preset.py presets/csmic-empyrean.json --check-materials
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PRESET_SCHEMA = os.path.join(HERE, "preset.schema.json")
SUBSTRATE_SCHEMA = os.path.join(HERE, "substrates.schema.json")
# the X-Ray Calc 3 tool server, used only by --check-materials; set XRC_MCP to its path
XRC = os.environ.get("XRC_MCP", "XRC_MCP.exe")

errors = []
warnings = []
notes = []


def err(m):
    errors.append(m)


def warn(m):
    warnings.append(m)


def note(m):
    notes.append(m)


def validate_against(doc, schema_path, label):
    try:
        import jsonschema
    except ImportError:
        warn("jsonschema not installed; %s shape not checked" % label)
        return
    schema = json.load(open(schema_path, encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    for e in sorted(v.iter_errors(doc), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in e.path) or "(root)"
        err("%s schema: %s: %s" % (label, where, e.message))


def load_library(preset, preset_path):
    ref = preset.get("substrate", {})
    rel = ref.get("library")
    if not rel:
        return None, None
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(preset_path)), rel))
    if not os.path.exists(path):
        err("substrate.library %r does not resolve to a file (looked at %s)" % (rel, path))
        return None, None
    try:
        raw = open(path, "rb").read()
        lib = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        err("substrate library %s is not valid JSON: %s" % (os.path.basename(path), e))
        return None, None
    validate_against(lib, SUBSTRATE_SCHEMA, "substrate-library")
    return lib, path


def check_semantics(preset, lib):
    # --- resolution ordering -------------------------------------------------
    r = preset.get("instrument", {}).get("resolution_deg", {})
    if r:
        lo, hi, st = r.get("min"), r.get("max"), r.get("start")
        if None not in (lo, hi) and lo > hi:
            err("instrument.resolution_deg: min %g exceeds max %g" % (lo, hi))
        if None not in (lo, hi, st) and not (lo <= st <= hi):
            err("instrument.resolution_deg: start %g outside [%g, %g]" % (st, lo, hi))

    # --- substrate reference resolves ----------------------------------------
    want = preset.get("substrate", {}).get("default")
    if lib is not None and want:
        subs = lib.get("substrates", {})
        if want not in subs:
            err("substrate.default %r is not in the library (have: %s)"
                % (want, ", ".join(sorted(subs)) or "none"))
        else:
            s = subs[want]
            if s.get("material", "").upper() in ("SIO2", "QUARTS") and s.get("density", 0) > 2.60:
                note("default substrate %r uses %s at %g g/cm3, the crystalline-quartz "
                     "value. Glass substrates are nearer 2.2-2.5."
                     % (want, s["material"], s["density"]))

    # --- substrates without provenance ---------------------------------------
    if lib:
        for sid, s in lib.get("substrates", {}).items():
            p = (s.get("provenance") or "").strip()
            if p.upper().startswith("NOT MEASURED"):
                note("substrate %r density is declared not measured" % sid)
            if s.get("requires_table_entry") and not s.get("table_entry_hint"):
                warn("substrate %r requires a Henke table entry but gives no "
                     "table_entry_hint, so an operator cannot generate it" % sid)

    # --- default density rule ------------------------------------------------
    d = preset.get("materials", {}).get("default_rule", {})
    if d:
        lo, hi = d.get("min_fraction_of_bulk"), d.get("max_fraction_of_bulk")
        st = d.get("start_fraction_of_bulk")
        if None not in (lo, hi) and lo >= hi:
            err("materials.default_rule: min_fraction %g >= max_fraction %g" % (lo, hi))
        if None not in (lo, hi, st) and not (lo <= st <= hi):
            err("materials.default_rule: start_fraction %g outside [%g, %g]" % (st, lo, hi))

    # --- named materials -----------------------------------------------------
    for name, m in preset.get("materials", {}).get("named", {}).items():
        lo, hi, st = m.get("density_min"), m.get("density_max"), m.get("density_start")
        if None in (lo, hi, st):
            continue
        if lo >= hi:
            err("materials.named.%s: density_min %g >= density_max %g" % (name, lo, hi))
        if not (lo <= st <= hi):
            err("materials.named.%s: density_start %g outside [%g, %g]" % (name, st, lo, hi))

    # --- layer roughness: ordered bounds, start range inside them -------------
    sg = preset.get("materials", {}).get("sigma_A", {})
    if sg.get("bounds") and sg.get("start"):
        (lo, hi), (s0, s1) = sg["bounds"], sg["start"]
        if lo < 0 or lo >= hi:
            err("materials.sigma_A.bounds: need 0 <= min < max, got [%g, %g]" % (lo, hi))
        elif s0 > s1 or not (lo <= s0 and s1 <= hi):
            err("materials.sigma_A.start [%g, %g] not an ordered range inside bounds "
                "[%g, %g]" % (s0, s1, lo, hi))

    # --- contamination layer against its OWN bounds --------------------------
    # Deliberately not checked against materials.named: a hydrocarbon overlayer is
    # lighter than the sputtered form of the same element, and v4 conflating the two
    # gave the surface layer a start density outside its own stated range.
    surf = preset.get("surface", {}).get("contamination_layer", {})
    if surf:
        b = surf.get("bounds", {})
        for key, field in (("thickness_A", "thickness_A"),
                           ("sigma_A", "sigma_A"),
                           ("density", "density")):
            rng, val = b.get(key), surf.get(field)
            if not rng or val is None:
                continue
            lo, hi = rng
            if lo >= hi:
                err("surface.contamination_layer.bounds.%s: %g >= %g" % (key, lo, hi))
            elif not (lo <= val <= hi):
                err("surface.contamination_layer: %s start %g outside its own bounds "
                    "[%g, %g]" % (field, val, lo, hi))
        var = surf.get("sensitivity_variant")
        if var and var.get("thickness_A") == surf.get("thickness_A") \
                and var.get("density") == surf.get("density"):
            err("surface.contamination_layer.sensitivity_variant is identical to the "
                "starting layer, so the section 3 variant probes nothing")

    # --- acceptance ----------------------------------------------------------
    acc = preset.get("acceptance", {})
    cal = acc.get("calibrated_under", {})
    chi_ml = preset.get("chi2", {}).get("multilayer")
    if cal.get("chi2") and chi_ml and cal["chi2"] != chi_ml:
        warn("acceptance.calibrated_under.chi2 differs from chi2.multilayer: chi2_max "
             "means a different unweighted chi-squared than it did at calibration")
    res_now = preset.get("instrument", {}).get("resolution_deg", {}).get("start")
    res_cal = cal.get("resolution_deg")
    if None not in (res_now, res_cal) and abs(res_now - res_cal) > 1e-12:
        warn("acceptance thresholds were calibrated at resolution %g but the preset "
             "starts at %g" % (res_cal, res_now))
    sc = preset.get("scale", {})
    if sc and sc.get("solve") and cal.get("scale_solve") is False             and acc.get("thresholds", {}).get("chi2_max") is not None:
        warn("acceptance.thresholds.chi2_max was calibrated with the scale anchored "
             "(calibrated_under.scale_solve false) but scale.solve is true: a solved "
             "chi-squared is never higher than the anchored one, so the threshold is not "
             "calibrated for this preset's default and the verdict must say so (section 10 rule 5)")
    if sc and sc.get("solve") and "scale_solve" not in cal             and acc.get("thresholds", {}).get("chi2_max") is not None:
        warn("scale.solve is true but calibrated_under does not say whether chi2_max was "
             "fixed with the scale solved or anchored")
    if acc.get("thresholds", {}).get("chi2_max") is not None and not cal.get("curves"):
        err("acceptance: a chi2_max is declared but calibrated_under.curves is empty; "
            "a shipped threshold must name the curves it was fixed on")


def engine_materials():
    if not os.path.exists(XRC):
        warn("--check-materials: server not found at %s" % XRC)
        return None
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "validate", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "list_materials", "arguments": {}}},
    ]
    payload = "\n".join(json.dumps(m) for m in msgs) + "\n"
    try:
        with tempfile.TemporaryDirectory(prefix="xrc-validate-") as tmp:
            p = subprocess.run([XRC, "--workdir", tmp], input=payload,
                               capture_output=True, text=True, timeout=90)
    except Exception as e:  # noqa: BLE001
        warn("--check-materials: could not run the server (%s)" % e)
        return None
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("id") == 2:
            try:
                tab = json.loads(m["result"]["content"][0]["text"])["materials"]
                return {x["name"].upper(): x for x in tab}
            except Exception:  # noqa: BLE001
                pass
    warn("--check-materials: no material list came back from the server")
    return None


def check_materials(preset, lib, known):
    """Advisory only. The Henke table is per-installation and extensible."""
    note("materials checked against this installation's table (%d entries)" % len(known))

    for name, m in preset.get("materials", {}).get("named", {}).items():
        k = known.get(name.upper())
        if not k:
            warn("material %r is not in this installation's Henke table; the operator "
                 "must supply that entry" % name)
            continue
        if m.get("density_max", 0) > k["bulk_density"] and not m.get("reason"):
            warn("materials.named.%s: density_max %g exceeds this table's bulk density "
                 "%g and no reason is given" % (name, m["density_max"], k["bulk_density"]))

    surf = preset.get("surface", {}).get("contamination_layer", {}).get("material")
    if surf and surf.upper() not in known:
        warn("surface.contamination_layer material %r is not in this installation's "
             "Henke table" % surf)

    if lib:
        for sid, s in lib.get("substrates", {}).items():
            present = s.get("material", "").upper() in known
            declared = bool(s.get("requires_table_entry"))
            if not present and not declared:
                warn("substrate %r uses material %r which is not in this installation's "
                     "table and does not set requires_table_entry"
                     % (sid, s.get("material")))
            elif present and declared:
                note("substrate %r declares requires_table_entry but %r is already in "
                     "this table" % (sid, s.get("material")))
            elif not present and declared:
                note("substrate %r needs a table entry for %r, as declared"
                     % (sid, s.get("material")))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset")
    ap.add_argument("--check-materials", action="store_true",
                    help="also report which names this installation's Henke table knows")
    args = ap.parse_args()

    raw = open(args.preset, "rb").read()
    try:
        preset = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        print("FAIL  %s is not valid JSON: %s" % (args.preset, e))
        return 1

    validate_against(preset, PRESET_SCHEMA, "preset")
    lib, lib_path = load_library(preset, args.preset)
    check_semantics(preset, lib)
    if args.check_materials:
        known = engine_materials()
        if known:
            check_materials(preset, lib, known)

    print("preset   : %s" % preset.get("preset_id", "(no id)"))
    print("file     : %s  sha256 %s"
          % (os.path.basename(args.preset), hashlib.sha256(raw).hexdigest()[:16]))
    if lib_path:
        lraw = open(lib_path, "rb").read()
        print("substrate: %s  sha256 %s  (%d entries, default %r)"
              % (os.path.basename(lib_path), hashlib.sha256(lraw).hexdigest()[:16],
                 len(lib.get("substrates", {})), preset.get("substrate", {}).get("default")))
    if not preset.get("provenance"):
        warn("no provenance recorded on the preset")
    for m in notes:
        print("note     : %s" % m)
    for m in warnings:
        print("WARN     : %s" % m)
    for m in errors:
        print("ERROR    : %s" % m)
    print("result   : %s (%d error%s, %d warning%s)"
          % ("PASS" if not errors else "FAIL",
             len(errors), "" if len(errors) == 1 else "s",
             len(warnings), "" if len(warnings) == 1 else "s"))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
