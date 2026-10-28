; Inno Setup script for Bokin Suno Master: dist\BokinSunoMaster\ (PyInstaller) -> BokinSunoMaster-Setup-<version>.exe
; Per-user install, no admin rights: %LOCALAPPDATA%\Programs\Bokin Suno Master, Start menu and desktop shortcuts, an
; entry in Settings > Apps. Mastered songs live in Music\Bokin Suno Master and the app's data in
; %APPDATA%\Bokin\SunoMaster, so updates and uninstalls keep them. (Built like Bokin FX's BokinFX.iss.)
;   iscc /DAppVersion=1.0.1 packaging\BokinSunoMaster.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef DistDir
  #define DistDir "..\dist"
#endif
#define AppName "Bokin Suno Master"
#define AppExe "BokinSunoMaster.exe"

[Setup]
; the AppId never changes: a new version installs over the old one
AppId={{6E2F4C1A-93B8-4D27-B5A0-8C1D7E3F9A52}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Bokin
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir={#DistDir}
OutputBaseFilename=BokinSunoMaster-Setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; drop the previous version's libraries before copying the new ones
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#DistDir}\BokinSunoMaster\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; an update started from the app ("Cập nhật ngay" passes /RELAUNCH=1) starts it again; its window reconnects
Filename: "{app}\{#AppExe}"; Parameters: "--updated"; Flags: nowait; Check: Relaunch

[Code]
{ Before files are replaced, the installed app closes a running copy of itself (BokinSunoMaster.exe --close). It
  answers 3 while that copy is mastering a song: setup stops then and says why. A copy that does not answer is ended. }
function Relaunch(): Boolean;
begin
  Result := ExpandConstant('{param:relaunch|0}') = '1';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
  Installed: String;
begin
  Result := '';
  Installed := ExpandConstant('{app}\{#AppExe}');
  if FileExists(Installed) then
  begin
    if Exec(Installed, '--close', '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 3) then
    begin
      Result := 'Bokin Suno Master is still mastering a song. Wait until it has finished, then run this setup again.';
      exit;
    end;
  end;
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;
