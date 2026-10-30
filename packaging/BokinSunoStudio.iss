; Inno Setup script for Bokin Suno Studio: dist\BokinSunoStudio\ (PyInstaller) -> BokinSunoStudio-Setup-<version>.exe
; Per-user install, no admin rights: %LOCALAPPDATA%\Programs\Bokin Suno Studio, Start menu and desktop shortcuts, an
; entry in Settings > Apps. Downloaded and mastered songs live in Music\Bokin Suno Studio (or the folders chosen in
; the app) and the app's data (the Suno accounts and their Chrome profiles too) in %APPDATA%\Bokin\SunoStudio, so
; updates and uninstalls keep them. (Built like Bokin Suno Master's BokinSunoMaster.iss.)
;   iscc /DAppVersion=1.0.1 packaging\BokinSunoStudio.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef DistDir
  #define DistDir "..\dist"
#endif
#define AppName "Bokin Suno Studio"
#define AppExe "BokinSunoStudio.exe"

[Setup]
; the AppId never changes: a new version installs over the old one
AppId={{3C9B1E57-2A64-4F0D-9E83-B7D5A1C46F20}
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
OutputBaseFilename=BokinSunoStudio-Setup-{#AppVersion}
SetupIconFile=studio.ico
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
Source: "{#DistDir}\BokinSunoStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; an update started from the app (its update button passes /RELAUNCH=1) starts it again; its window reconnects
Filename: "{app}\{#AppExe}"; Parameters: "--updated"; Flags: nowait; Check: Relaunch

[Code]
{ Before files are replaced, the installed app closes a running copy of itself (BokinSunoStudio.exe --close). It
  answers 3 while that copy is busy (downloading from Suno, mastering a song): setup stops then and says why. A copy
  that does not answer is ended. }
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
      Result := 'Bokin Suno Studio is still downloading from Suno or mastering a song. Wait until it has finished (or press its Stop button), then run this setup again.';
      exit;
    end;
  end;
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;
