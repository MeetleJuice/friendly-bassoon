#ifndef AppVersion
  #define AppVersion "0.15.0"
#endif
#define AppName "Aigentics Desktop"

[Setup]
AppId={{A8934D3C-272C-4DAD-A267-AC4D74188343}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Aigentics
AppPublisherURL=https://github.com/MeetleJuice/friendly-bassoon
AppUpdatesURL=https://github.com/MeetleJuice/friendly-bassoon/releases
DefaultDirName={localappdata}\Programs\Aigentics Desktop
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
SetupIconFile=..\aigentics\assets\icon.ico
UninstallDisplayIcon={app}\Aigentics.exe
OutputDir=..\dist\installer
OutputBaseFilename=Aigentics-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter=Aigentics.exe
RestartApplications=no
VersionInfoVersion={#AppVersion}.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Aigentics\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\Aigentics Desktop"; Filename: "{app}\Aigentics.exe"; Tasks: desktopicon
Name: "{group}\Aigentics Desktop"; Filename: "{app}\Aigentics.exe"

[Run]
Filename: "{app}\Aigentics.exe"; Description: "Launch Aigentics Desktop"; Flags: nowait postinstall skipifsilent; Check: not IsUpdate

; An update requested inside the app must restart it even in unattended mode.
Filename: "{app}\Aigentics.exe"; Flags: nowait; Check: IsUpdate

[Code]
function IsUpdate: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;
