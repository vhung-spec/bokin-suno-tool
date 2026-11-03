; Inno Setup script for Bokin Suno Studio: dist\BokinSunoStudio\ (PyInstaller) -> BokinSunoStudio-Setup-<version>.exe
; Per-user install, no admin rights: in the folder chosen on the setup's folder page (%LOCALAPPDATA%\Programs\Bokin
; Suno Studio at first, the folder chosen before on a later setup; the app's own updates install there silently),
; Start menu and desktop shortcuts, an entry in Settings > Apps. A setup moved to another folder removes the program
; files left in the folder before. Downloaded and mastered songs live in Music\Bokin Suno Studio (or the folders chosen in
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
; the folder page on every setup run by hand (the owner's choice, 03/11/2026: not on drive C); a silent setup (the
; app's update) keeps the folder of the install before (UsePreviousAppDir)
DisableDirPage=no
UsePreviousAppDir=yes
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
  that does not answer is ended.
  The chosen folder must be one this user can write to (no admin rights: not Program Files), and not a drive's root.
  Installed in another folder before: that folder's program files are removed once the new copy is in place (the
  app's data is in %APPDATA%\Bokin\SunoStudio, the songs where they were chosen: neither is touched). }
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{3C9B1E57-2A64-4F0D-9E83-B7D5A1C46F20}_is1';

var
  PrevDir: String;

function InitializeSetup(): Boolean;
begin
  PrevDir := '';
  if not RegQueryStringValue(HKA, UninstallKey, 'Inno Setup: App Path', PrevDir) then
    PrevDir := '';
  Result := True;
end;

function Relaunch(): Boolean;
begin
  Result := ExpandConstant('{param:relaunch|0}') = '1';
end;

function SameDir(A, B: String): Boolean;
begin
  Result := CompareText(RemoveBackslashUnlessRoot(A), RemoveBackslashUnlessRoot(B)) = 0;
end;

{ '' when the app can go in Dir, else why not }
function DirProblem(Dir: String): String;
var
  Probe: String;
  Made: Boolean;
begin
  Result := '';
  Dir := RemoveBackslashUnlessRoot(Dir);
  if (Length(Dir) <= 3) or (ExtractFileName(Dir) = '') then
  begin
    Result := 'Choose a folder, not the root of a drive (for example D:\Bokin Suno Studio).';
    exit;
  end;
  Made := not DirExists(Dir);
  if Made and not ForceDirectories(Dir) then
  begin
    Result := 'This folder cannot be created: ' + Dir + #13#10 + 'Choose another folder (for example D:\Bokin Suno Studio).';
    exit;
  end;
  Probe := AddBackslash(Dir) + '.bokin-setup-write-test';
  if SaveStringToFile(Probe, 'x', False) then
    DeleteFile(Probe)
  else
    Result := 'Setup cannot write in this folder (it needs administrator rights): ' + Dir + #13#10 + 'Choose another folder (for example D:\Bokin Suno Studio).';
  if Made then
    RemoveDir(Dir);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Problem: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    Problem := DirProblem(WizardDirValue);
    if Problem <> '' then
    begin
      MsgBox(Problem, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
  Installed: String;
begin
  Result := DirProblem(ExpandConstant('{app}'));
  if Result <> '' then
    exit;
  Installed := ExpandConstant('{app}\{#AppExe}');
  if (PrevDir <> '') and FileExists(AddBackslash(PrevDir) + '{#AppExe}') then
    Installed := AddBackslash(PrevDir) + '{#AppExe}';  { (moved to another folder: the copy running is the old one) }
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

procedure CurStepChanged(CurStep: TSetupStep);
var
  NewDir: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  NewDir := ExpandConstant('{app}');
  { the folder before, if it is another one (not this folder, not inside it or around it, not a drive's root) and
    holds the app: its program files go }
  if (PrevDir = '') or SameDir(PrevDir, NewDir) or (Length(RemoveBackslashUnlessRoot(PrevDir)) <= 3) then
    exit;
  if (Pos(Lowercase(AddBackslash(PrevDir)), Lowercase(AddBackslash(NewDir))) = 1) or
     (Pos(Lowercase(AddBackslash(NewDir)), Lowercase(AddBackslash(PrevDir))) = 1) then
    exit;
  if not FileExists(AddBackslash(PrevDir) + '{#AppExe}') then
    exit;
  DelTree(AddBackslash(PrevDir) + '_internal', True, True, True);
  DeleteFile(AddBackslash(PrevDir) + '{#AppExe}');
  DeleteFile(AddBackslash(PrevDir) + 'unins000.exe');
  DeleteFile(AddBackslash(PrevDir) + 'unins000.dat');
  DeleteFile(AddBackslash(PrevDir) + 'unins000.msg');
  RemoveDir(PrevDir);  { (only when nothing else is left in it) }
end;
