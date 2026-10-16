"""Empacota fontes para Kali com LF, permissoes Unix e sem credenciais."""

from pathlib import Path
import hashlib
import io
import re
import tarfile

ROOT = Path(__file__).resolve().parent.parent
TOP = "monitor-precos-kali"


def build_package(output=None):
    output = Path(output or ROOT / "monitor-precos-kali.tar.gz")
    names = [
        "README.md",
        "LEIA-ME-KALI.md",
        "MERCADO-LIVRE.md",
        "STATUS-LOJAS.md",
        "VALIDACAO.md",
        ".env.example",
        "requirements.txt",
        "requirements.lock.txt",
        "requirements-server.txt",
        "requirements-browser.txt",
        "requirements-selenium.txt",
        "pytest.ini",
    ]
    files = [ROOT / name for name in names]
    for folder in ("monitor", "deploy", "scripts", "tests"):
        files.extend(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file()
            and not p.is_symlink()
            and "__pycache__" not in p.parts
            and p.suffix in (".py", ".sh", ".service", ".json", ".html", ".md", ".xml")
        )
    with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        root_info = tarfile.TarInfo(TOP)
        root_info.type = tarfile.DIRTYPE
        root_info.mode = 0o755
        archive.addfile(root_info)
        for path in sorted(files):
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
            if re.search(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b", text):
                raise ValueError("Possivel token no arquivo " + relative)
            data = text.encode("utf-8")
            info = tarfile.TarInfo(TOP + "/" + relative)
            info.mode = 0o755 if path.suffix == ".sh" else 0o644
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        checksum + "  " + output.name + "\n", encoding="ascii"
    )
    return output


if __name__ == "__main__":
    print(build_package())
