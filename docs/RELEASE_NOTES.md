## Aigentics Desktop 0.2.0 — easier Windows setup

Download **Aigentics-Setup-0.2.0.exe** from the assets below and run the wizard. It bundles Python and application dependencies and creates a desktop shortcut with a custom Aigentics icon. No Python, VS Code or Git installation is needed to run this packaged app. Ollama remains a separate local service.

On launch, the app discovers installed Ollama models and checks known Desktop locations for **.env** or **.env.txt** (including redirected/OneDrive Desktop). Keys load into memory only. Recognized key variable names add matching provider profiles without calling cloud APIs. Use **Setup & updates** to refresh discovery, choose a model, select a key file manually, or disable automatic discovery.

The app checks public GitHub Releases at startup and offers checksum-verified downloads. Installation requires an explicit click, waits until no task is running, backs up local history, and opens the update wizard. Projects, history and credentials live separately from installed application files.

New local diagnostics record setup outcomes, model/key-file discovery counts, update checks, verified downloads and update version outcomes. Credentials and the contents of the Desktop key file are never logged or uploaded as telemetry.

The installer is not Authenticode-signed. SHA-256 checks verify integrity against this GitHub release; they are not an independent publisher signature. Windows may show an unknown-publisher warning. Human acceptance on Windows 10 and the user's actual Ollama/API services remains separate from automated runner checks. See the README and docs/VERIFICATION.md for verification status.
