; RL Tracker – Installer (Inno Setup 6)
; Baut aus dist\RLTracker die Datei Output\RLTracker-Setup-<Version>.exe
; Aufruf: ISCC.exe installer\setup.iss   (macht build_setup.bat automatisch)

#define AppName "RL Tracker"
; Version kommt vom Build (ISCC /DAppVersion=1.2.0), sonst dieser Standardwert
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "RL Tracker Fan-Projekt"
#define AppExe "RLTracker.exe"

[Setup]
; Feste ID – nie aendern, sonst erkennt Windows Updates nicht als dieselbe App
AppId={{8F3C2A51-6B7D-4E2A-9C41-5D2E7A9B1C03}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppComments=Inoffizielle Statistik-App für Rocket League. Nicht mit Psyonix, Epic Games oder Valve verbunden.
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\Output
; Fester Name, damit der Download-Link auf der Webseite immer die neueste Version liefert
OutputBaseFilename=RLTracker-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=Nutzungsbedingungen.txt
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
; Adminrechte: noetig, um in Program Files zu installieren und die Rocket-League-INI zu aendern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\RLTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "Nutzungsbedingungen.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Live-Statistiken und Match-Analyse für Rocket League"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Nur wenn auf der Zustimmungsseite erlaubt: Stats API in allen gefundenen Installationen einschalten
Filename: "{app}\{#AppExe}"; Parameters: "--grant-access"; StatusMsg: "Richte den Zugriff auf Rocket League ein ..."; Flags: runhidden waituntilterminated; Check: AccessGranted
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
; Beim Deinstallieren die Stats API wieder ausschalten
Filename: "{app}\{#AppExe}"; Parameters: "--revoke-access"; Flags: runhidden waituntilterminated; RunOnceId: "RevokeAccess"

[Code]
var
  AccessPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  AccessPage := CreateInputOptionPage(wpSelectTasks,
    'Zugriff auf Rocket League',
    'RL Tracker braucht deine Erlaubnis, um mit Rocket League zu arbeiten.',
    'Damit RL Tracker deine Matches aufzeichnen kann, wird die offizielle Stats-Schnittstelle von Rocket League ' +
    'eingeschaltet. Dafür ändert der Installer in jedem gefundenen Rocket-League-Ordner (Steam und Epic) die Datei ' +
    'TAGame\Config\DefaultStatsAPI.ini bzw. TAStatsAPI.ini – vorher wird eine Sicherung angelegt. ' +
    'Außerdem liest die App deine gespeicherten Replays.' + #13#10 + #13#10 +
    'Es werden keine Spieldateien verändert, keine Mods installiert und keine Daten verschickt. ' +
    'Beim Deinstallieren wird die Einstellung zurückgenommen. Läuft Rocket League gerade, starte es danach neu.',
    True, False);
  AccessPage.Add('Ja, ich erlaube RL Tracker den Zugriff auf Rocket League (empfohlen)');
  AccessPage.Add('Nein, jetzt nicht – ich kann das später in der App erlauben');
  { Bewusst nichts vorauswählen: die Zustimmung muss aktiv gegeben werden }
  AccessPage.Values[0] := False;
  AccessPage.Values[1] := False;
end;

function IsUpgrade: Boolean;
var
  Key: String;
begin
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3C2A51-6B7D-4E2A-9C41-5D2E7A9B1C03}_is1';
  Result := RegKeyExists(HKLM, Key) or RegKeyExists(HKCU, Key);
end;

{ Bei einem Update nicht erneut fragen – die Entscheidung von der Erstinstallation gilt weiter }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = AccessPage.ID) and IsUpgrade;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = AccessPage.ID) and (not AccessPage.Values[0]) and (not AccessPage.Values[1]) then
  begin
    MsgBox('Bitte wähle aus, ob RL Tracker auf Rocket League zugreifen darf.', mbInformation, MB_OK);
    Result := False;
  end;
end;

function AccessGranted: Boolean;
begin
  Result := AccessPage.Values[0];
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := MemoDirInfo + NewLine + NewLine;
  if MemoTasksInfo <> '' then
    Result := Result + MemoTasksInfo + NewLine + NewLine;
  if IsUpgrade then
  begin
    Result := Result + 'Update – deine bisherigen Einstellungen und Matches bleiben erhalten.';
    exit;
  end;
  Result := Result + 'Zugriff auf Rocket League:' + NewLine + Space;
  if AccessGranted then
    Result := Result + 'erlaubt – Stats-Schnittstelle wird eingeschaltet'
  else
    Result := Result + 'nicht erlaubt – kann später in der App erlaubt werden';
end;
