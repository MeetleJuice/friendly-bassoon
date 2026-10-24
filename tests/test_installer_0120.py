"""In-app silent updates restart, manual wizard installation retains its checkbox."""

from pathlib import Path


def test_installer_distinguishes_explicit_update_from_normal_installation():
    text = (Path(__file__).parents[1] / "packaging" / "installer.iss").read_text()
    run = text.split("[Run]", 1)[1].split("[Code]", 1)[0]
    entries = [line for line in run.splitlines() if line.startswith("Filename:")]
    assert len(entries) == 2
    manual, update = entries
    assert 'Filename: "{app}\\Aigentics.exe"' in manual
    assert "postinstall skipifsilent; Check: not IsUpdate" in manual
    assert 'Filename: "{app}\\Aigentics.exe"; Flags: nowait; Check: IsUpdate' == update
    assert "ExpandConstant('{param:UPDATE|0}') = '1'" in text
    assert "RestartApplications=no" in text
    assert "PrivilegesRequired=lowest" in text
