#!/usr/bin/env python3
"""Crea l'installer autoinstallante per i client Mac.

Eseguibile da Windows o macOS. Produce:

  dist/securtek-client-mac-vVERSION/
    Installa Securtek.app/          doppio clic
    InstallaSecurtek.command        file unico autoestraente
    LEGGIMI.txt
  dist/Securtek-client-mac-vVERSION.zip
  dist/InstallaSecurtek-vVERSION.command
"""

from __future__ import annotations

import base64
import io
import sys
import tarfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = ROOT / "deploy" / "macos-client"
DIST = ROOT / "dist"


def read_version() -> str:
    version_file = ROOT / "VERSION"
    if not version_file.is_file():
        raise SystemExit(f"File VERSION non trovato in {ROOT}")
    return version_file.read_text(encoding="utf-8").strip()


def read_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in {".py", ".sh", ".command", ".template", ".txt", ".md", ".plist"} or path.name in {
        "InstallaSecurtek",
        "VERSION",
        "LEGGIMI.txt",
    }:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if not data.endswith(b"\n"):
            data += b"\n"
    return data


def payload_files() -> dict[str, bytes]:
    helper_src = ROOT / "scripts" / "securtek_desktop_helper.py"
    if not helper_src.is_file():
        helper_src = CLIENT_DIR / "securtek_desktop_helper.py"
    required = {
        "install-client.sh": CLIENT_DIR / "install-client.sh",
        "securtek_desktop_helper.py": helper_src,
        "SecurtekLauncher.template": CLIENT_DIR / "SecurtekLauncher.template",
        "InstallaSecurtek": CLIENT_DIR / "InstallaSecurtek",
        "InstallClient.command": CLIENT_DIR / "InstallClient.command",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise SystemExit("File mancanti in macos-client: " + ", ".join(missing))
    files = {name: read_bytes(path) for name, path in required.items()}
    files["VERSION"] = (read_version() + "\n").encode("utf-8")
    return files


def info_plist(version: str) -> bytes:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleExecutable</key>
	<string>InstallaSecurtek</string>
	<key>CFBundleIdentifier</key>
	<string>local.securtek.installer</string>
	<key>CFBundleName</key>
	<string>Installa Securtek</string>
	<key>CFBundleDisplayName</key>
	<string>Installa Securtek</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>CFBundleVersion</key>
	<string>{version}</string>
	<key>CFBundleShortVersionString</key>
	<string>{version}</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>LSUIElement</key>
	<false/>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>NSAppleEventsUsageDescription</key>
	<string>Securtek chiede l'URL del server e mostra lo stato dell'installazione.</string>
</dict>
</plist>
"""
    return xml.encode("utf-8")


def zip_readme(version: str) -> bytes:
    text = f"""Securtek — installer client Mac v. {version}
=============================================

Cosa fa
- Installa l'helper cartelle (Scegli / Apri sul QUESTO Mac)
- Crea Securtek.app sul Desktop (finestra Edge/Chrome verso il Mini)
- Avvio automatico dell'helper al login

Installazione (consigliata)
1. Estrai questo zip (doppio clic).
2. Doppio clic su "Installa Securtek".
   Se macOS blocca: tasto destro sull'app → Apri → Apri.
3. Inserisci l'URL del Mac Mini, ad esempio:
   http://192.168.2.76:8000
4. Sul Desktop compare Securtek.app. Aprila da li (non Safari).

File unico (AirDrop / una sola copia)
- InstallaSecurtek.command  (nello zip, oppure dist/InstallaSecurtek-v{version}.command)
- Doppio clic. Se dice "non hai i privilegi":
  apri Terminale e incolla:

  bash ~/Downloads/InstallaSecurtek.command

  (se il file e altrove, cambia il percorso)

Requisiti
- Stessa rete del Mac Mini server
- Microsoft Edge (consigliato) o Google Chrome
- Python 3 (di solito gia presente). Se manca, l'installer apre xcode-select.

Verifica helper
  curl http://127.0.0.1:18765/health

Disinstallazione
  launchctl bootout "gui/$(id -u)/com.securtek.desktop-helper"
  rm -f "$HOME/Library/LaunchAgents/com.securtek.desktop-helper.plist"
  rm -rf "$HOME/Library/Application Support/Securtek/desktop-helper"
  rm -rf "$HOME/Desktop/Securtek.app"

Non installa Django, PostgreSQL o il progetto server.
"""
    return text.replace("\r\n", "\n").encode("utf-8")


def self_extract_command(version: str, payload_b64: str) -> bytes:
    header = f"""#!/bin/bash
# Securtek client Mac v. {version} — installer autoinstallante (file unico).
# Doppio clic, oppure: bash InstallaSecurtek.command
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin:${{PATH:-}}"

SELF="${{BASH_SOURCE[0]:-$0}}"
HERE="$(cd "$(dirname "$SELF")" && pwd)"
SELF_PATH="${{HERE}}/$(basename "$SELF")"

xattr -dr com.apple.quarantine "$SELF_PATH" 2>/dev/null || true
perl -pi -e 's/\\r\\n?/\\n/g' "$SELF_PATH" 2>/dev/null || true
chmod +x "$SELF_PATH" 2>/dev/null || true

TMP="$(mktemp -d /tmp/securtek-client-XXXXXX)"
cleanup() {{ rm -rf "$TMP"; }}
trap cleanup EXIT

PAYLOAD_LINE="$(awk '/^#__SECURTEK_PAYLOAD__$/ {{ print NR + 1; exit }}' "$SELF_PATH")"
if [[ -z "${{PAYLOAD_LINE}}" ]]; then
  osascript -e 'display alert "Securtek" message "Installer danneggiato (payload mancante)." as critical' 2>/dev/null || true
  echo "Installer danneggiato: payload mancante." >&2
  exit 1
fi

decode_base64() {{
  if [[ "$(uname -s)" == Darwin ]]; then
    base64 -D
  else
    base64 -d
  fi
}}

tail -n +"${{PAYLOAD_LINE}}" "$SELF_PATH" | tr -d '\\r' | tr -d '\\n' | decode_base64 | tar -xzf - -C "$TMP"

cd "$TMP"
chmod +x install-client.sh InstallaSecurtek InstallClient.command 2>/dev/null || true
set +e
/bin/bash ./install-client.sh
status=$?
set -e

echo
if [[ "${{status}}" -eq 0 ]]; then
  echo "Installazione completata. Puoi chiudere questa finestra."
else
  echo "Installazione non completata (codice ${{status}})."
fi
if [[ -t 0 ]]; then
  echo
  read -r -p "Premi Invio per chiudere..." _
fi
exit "${{status}}"

#__SECURTEK_PAYLOAD__
"""
    wrapped = "\n".join(payload_b64[i : i + 76] for i in range(0, len(payload_b64), 76))
    return (header + wrapped + "\n").encode("utf-8")


def make_tar_gz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    now = int(time.time())
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = now
            info.uid = 0
            info.gid = 0
            executable = name.endswith((".sh", ".command")) or name == "InstallaSecurtek"
            info.mode = 0o755 if executable else 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def add_zip_dir(zf: zipfile.ZipFile, arcname: str) -> None:
    name = arcname.replace("\\", "/").rstrip("/") + "/"
    info = zipfile.ZipInfo(name)
    info.date_time = time.localtime()[:6]
    info.create_system = 3
    info.external_attr = (0o40755 << 16) | 0x10
    zf.writestr(info, b"")


def add_zip_file(zf: zipfile.ZipFile, arcname: str, data: bytes, executable: bool = False) -> None:
    name = arcname.replace("\\", "/")
    info = zipfile.ZipInfo(name)
    info.date_time = time.localtime()[:6]
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    unix_mode = 0o100755 if executable else 0o100644
    info.external_attr = unix_mode << 16
    zf.writestr(info, data)


def write_tree(dest: Path, relative: str, data: bytes) -> None:
    path = dest / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build() -> None:
    version = read_version()
    files = payload_files()
    folder_name = f"Securtek-client-mac-v{version}"
    out_dir = DIST / f"securtek-client-mac-v{version}"
    zip_path = DIST / f"{folder_name}.zip"
    command_name = f"InstallaSecurtek-v{version}.command"
    command_path = DIST / command_name

    if out_dir.exists():
        for child in sorted(out_dir.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        out_dir.rmdir()
    out_dir.mkdir(parents=True, exist_ok=True)

    app_rel = "Installa Securtek.app"
    app_files = {
        f"{app_rel}/Contents/Info.plist": info_plist(version),
        f"{app_rel}/Contents/PkgInfo": b"APPL????",
        f"{app_rel}/Contents/MacOS/InstallaSecurtek": files["InstallaSecurtek"],
        f"{app_rel}/Contents/Resources/VERSION": files["VERSION"],
        f"{app_rel}/Contents/Resources/install-client.sh": files["install-client.sh"],
        f"{app_rel}/Contents/Resources/securtek_desktop_helper.py": files["securtek_desktop_helper.py"],
        f"{app_rel}/Contents/Resources/SecurtekLauncher.template": files["SecurtekLauncher.template"],
        f"{app_rel}/Contents/Resources/InstallClient.command": files["InstallClient.command"],
    }

    tar_gz = make_tar_gz(files)
    command_bytes = self_extract_command(version, base64.b64encode(tar_gz).decode("ascii"))
    readme = zip_readme(version)

    for rel, data in app_files.items():
        write_tree(out_dir, rel, data)
    write_tree(out_dir, "InstallaSecurtek.command", command_bytes)
    write_tree(out_dir, "LEGGIMI.txt", readme)
    DIST.mkdir(parents=True, exist_ok=True)
    command_path.write_bytes(command_bytes)

    client_helper = CLIENT_DIR / "securtek_desktop_helper.py"
    client_helper.write_bytes(files["securtek_desktop_helper.py"])
    (CLIENT_DIR / "VERSION").write_bytes(files["VERSION"])

    if zip_path.exists():
        zip_path.unlink()

    executable_names = {
        f"{app_rel}/Contents/MacOS/InstallaSecurtek",
        f"{app_rel}/Contents/Resources/install-client.sh",
        f"{app_rel}/Contents/Resources/InstallClient.command",
        "InstallaSecurtek.command",
    }
    dir_names = [
        f"{folder_name}/",
        f"{folder_name}/{app_rel}/",
        f"{folder_name}/{app_rel}/Contents/",
        f"{folder_name}/{app_rel}/Contents/MacOS/",
        f"{folder_name}/{app_rel}/Contents/Resources/",
    ]

    with zipfile.ZipFile(zip_path, "w") as zf:
        for directory in dir_names:
            add_zip_dir(zf, directory)
        for rel, data in app_files.items():
            add_zip_file(
                zf,
                f"{folder_name}/{rel}",
                data,
                executable=rel in executable_names,
            )
        add_zip_file(zf, f"{folder_name}/InstallaSecurtek.command", command_bytes, executable=True)
        add_zip_file(zf, f"{folder_name}/LEGGIMI.txt", readme, executable=False)

    print(f"Cartella:  {out_dir}")
    print(f"Zip:       {zip_path}")
    print(f"Command:   {command_path}")
    print(f"Versione:  {version}")
    print(f"Zip size:  {zip_path.stat().st_size} bytes")
    print(f"Helper:    {CLIENT_DIR / 'securtek_desktop_helper.py'}")


if __name__ == "__main__":
    try:
        build()
    except KeyboardInterrupt:
        sys.exit(130)
