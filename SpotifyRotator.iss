; SpotifyRotator.iss
; Inno Setup installer script for Spotify Playlist Rotator v4.0

#define AppName      "Spotify Playlist Rotator"
#define AppVersion   "4.0.0"
#define AppPublisher "ShadowAndrei"
#define AppURL       "https://github.com/ShadowAndrei/spotify-playlist-rotator"
#define AppExeName   "SpotifyRotator.exe"
#define AppID        "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
#define SourceDir    "dist\SpotifyRotator"

[Setup]
AppId={{#AppID}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=SpotifyRotator_v{#AppVersion}_Setup
WizardStyle=modern
WizardSizePercent=100
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start automatically with Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im {#AppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
function IsWebView2Installed: Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or 
            RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
end;

procedure InitializeWizard;
begin
  if not IsWebView2Installed then
  begin
    MsgBox('Microsoft WebView2 Runtime is required but was not found.' + #13#10 + #13#10 + 'Please install it for the app to work correctly.', mbInformation, MB_OK);
  end;
end;