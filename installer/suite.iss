#ifndef AppVersion
#define AppVersion "0.49.0"
#endif
[Setup]
AppId={{2F34FB97-834C-4672-B7F2-E5463D1A3A0A}
AppName=CoastYouth Retail Computer Setup
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\CoastYouthRetailSetup
PrivilegesRequired=lowest
DisableDirPage=yes
DisableProgramGroupPage=yes
Uninstallable=no
CreateAppDir=no
WizardStyle=modern
SetupLogging=yes
OutputDir=..\dist
OutputBaseFilename=CoastYouth-Retail-Computer-Setup-v{#AppVersion}
[Types]
Name: "server"; Description: "Server computer"
Name: "office"; Description: "Office computer"
Name: "pos"; Description: "POS checkout computer"
Name: "custom"; Description: "Custom selection"; Flags: iscustom
[Components]
Name: "server"; Description: "Operations server and controller"; Types: server
Name: "office"; Description: "CoastYouth Retail OFFICE"; Types: office
Name: "pos"; Description: "CoastYouth Retail DESK"; Types: pos
Name: "ops"; Description: "CoastYouth Retail STORE OPS (all web operations)"; Types: office
[Files]
Source: "..\dist\MGC-YFC-Operations-Setup-v{#AppVersion}.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\dist\CoastYouth-Retail-OFFICE-Setup-v1.20.0.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\dist\MGC-YFC-POS-Setup-v1.24.0.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\dist\CoastYouth-Retail-STORE-OPS-Setup-v1.6.1.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\dist\CoastYouth Retail Computer Registration.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Code]
var NamePage: TInputQueryWizardPage;
    DiagnosticsDir, CompletedComponents, CurrentComputerName, RegistrationName: String;
    SuiteExitCode: Integer;
procedure InitializeWizard;
begin
 CurrentComputerName := GetComputerNameString;
 RegistrationName := CurrentComputerName;
 NamePage := CreateInputQueryPage(wpSelectComponents, 'Computer identity', 'Current Windows computer: ' + CurrentComputerName, 'Keep the name below or enter a new one. After installing, setup will verify your Operations server connection and ask an administrator to register this PC in OFFICE. Renaming requires Windows approval and takes effect after a restart. Existing data is kept.');
 NamePage.Add('Computer name (leave unchanged to keep it):', False);
 NamePage.Values[0] := CurrentComputerName;
end;
function NextButtonClick(CurPageID: Integer): Boolean;
var S: String; I: Integer; HasLetter: Boolean;
begin
 Result := True;
 if CurPageID <> NamePage.ID then Exit;
 S := Uppercase(Trim(NamePage.Values[0])); NamePage.Values[0] := S;
 if S = '' then begin NamePage.Values[0] := CurrentComputerName; Exit; end;
 if CompareText(S, CurrentComputerName) = 0 then Exit;
 HasLetter := False;
 Result := (Length(S) <= 15) and (S[1] <> '-') and (S[Length(S)] <> '-');
 for I := 1 to Length(S) do begin
  if (S[I] >= 'A') and (S[I] <= 'Z') then HasLetter := True
  else if not (((S[I] >= '0') and (S[I] <= '9')) or (S[I] = '-')) then Result := False;
 end;
 Result := Result and HasLetter;
 if not Result then MsgBox('Use 1–15 letters, numbers or hyphens, with at least one letter. Do not start or end with a hyphen.', mbError, MB_OK);
end;
function GetCustomSetupExitCode: Integer;
begin
 Result := SuiteExitCode;
end;
function ShouldSkipPage(PageID: Integer): Boolean;
begin
 Result := (PageID = wpFinished) and (SuiteExitCode <> 0);
end;
procedure PrepareDiagnostics;
begin
 if DiagnosticsDir <> '' then Exit;
 DiagnosticsDir := ExpandConstant('{param:SETUPLOGDIR|}');
 if DiagnosticsDir = '' then
  DiagnosticsDir := ExpandConstant('{localappdata}\CoastYouthRetailSetup\Logs\') +
   GetDateTimeString('yyyymmdd-hhnnss', '-', '-') + '-' + ExtractFileName(ExpandConstant('{tmp}'));
 if Pos('"', DiagnosticsDir) > 0 then RaiseException('Invalid setup log folder.');
 if not ForceDirectories(DiagnosticsDir) then
  RaiseException('Setup could not create its diagnostic log folder: ' + DiagnosticsDir + #13#10 + 'No component installers have been started.');
end;
procedure RecordComponent(MessageText: String);
begin
 Log(MessageText);
 SaveStringToFile(AddBackslash(DiagnosticsDir) + 'components.txt', MessageText + #13#10, True);
end;
function InstallerExitReason(Code: Integer): String;
begin
 case Code of
  1: Result := 'The installer could not initialize.';
  2: Result := 'Installation was canceled before it started.';
  3: Result := 'The installer failed while preparing the next installation stage.';
  4: Result := 'The installer encountered a fatal error during installation.';
  5: Result := 'Installation was canceled or aborted after it started.';
  6: Result := 'The installer was terminated by a debugger.';
  7: Result := 'The installer reported that it could not proceed.';
  8: Result := 'The installer reported that Windows must restart before it can proceed.';
 else
  Result := 'The installer reported an error or was interrupted.';
 end;
end;
procedure StopComponent(AppName, Detail, ComponentLog: String);
var MessageText, CompletedText: String;
begin
 CompletedText := CompletedComponents;
 if CompletedText = '' then CompletedText := 'None';
 MessageText := AppName + ' did not finish.' + #13#10 + Detail + #13#10#13#10 +
  'Completed before this stop: ' + CompletedText + '.' + #13#10 +
  'Remaining applications were not started.' + #13#10#13#10 +
  'Component log (if the installer started):' + #13#10 + ComponentLog + #13#10 +
  'Setup summary:' + #13#10 + AddBackslash(DiagnosticsDir) + 'components.txt' + #13#10#13#10 +
  'Keep the existing application data folders. Review the component error before retrying.';
 RecordComponent(MessageText);
 RaiseException(MessageText);
end;
procedure RunInstaller(AppName, FileName, Parameters, DirectoryOption: String);
var Code: Integer; Target, ComponentLog: String;
begin
 SuiteExitCode := 1;
 PrepareDiagnostics;
 ComponentLog := AddBackslash(DiagnosticsDir) + ChangeFileExt(FileName, '.log');
 if WizardSilent then Parameters := Parameters + ' /VERYSILENT /SUPPRESSMSGBOXES';
 Parameters := Parameters + ' /LOG="' + ComponentLog + '"';
 Target := ExpandConstant('{param:' + DirectoryOption + '|}');
 if Target <> '' then begin
  if Pos('"', Target) > 0 then RaiseException('Invalid installation folder.');
  Parameters := Parameters + ' /DIR="' + Target + '"';
 end;
 WizardForm.StatusLabel.Caption := 'Installing ' + AppName + '...';
 RecordComponent('Starting ' + AppName + ' using ' + FileName + '. Log: ' + ComponentLog);
 if not Exec(ExpandConstant('{tmp}\') + FileName, Parameters, '', SW_SHOW, ewWaitUntilTerminated, Code) then
  StopComponent(AppName, 'Windows could not start the installer. Error ' + IntToStr(Code) + ': ' + SysErrorMessage(Code), ComponentLog);
 RecordComponent(AppName + ' returned exit code ' + IntToStr(Code) + '.');
 if (Code <> 0) and (Code <> 3010) then
  StopComponent(AppName, 'Exit code ' + IntToStr(Code) + ': ' + InstallerExitReason(Code), ComponentLog);
 if CompletedComponents <> '' then CompletedComponents := CompletedComponents + ', ';
 CompletedComponents := CompletedComponents + AppName;
 SuiteExitCode := 0;
end;
procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer; Params, Apps, Role, DefaultServer: String;
begin
 if CurStep <> ssPostInstall then Exit;
 if WizardIsComponentSelected('server') then RunInstaller('Operations server and controller', 'MGC-YFC-Operations-Setup-v{#AppVersion}.exe', '/NORESTART /TYPE=both', 'SERVERDIR');
 if WizardIsComponentSelected('office') then RunInstaller('CoastYouth Retail OFFICE', 'CoastYouth-Retail-OFFICE-Setup-v1.20.0.exe', '/NORESTART /FROMCOMPUTERSETUP=1', 'OFFICEDIR');
 if WizardIsComponentSelected('pos') then RunInstaller('CoastYouth Retail DESK', 'MGC-YFC-POS-Setup-v1.24.0.exe', '/NORESTART /FROMCOMPUTERSETUP=1', 'POSDIR');
 if WizardIsComponentSelected('ops') then RunInstaller('CoastYouth Retail STORE OPS', 'CoastYouth-Retail-STORE-OPS-Setup-v1.6.1.exe', '/NORESTART /FROMCOMPUTERSETUP=1', 'OPSDIR');
 if (NamePage.Values[0] <> '') and (CompareText(NamePage.Values[0], CurrentComputerName) <> 0) then begin
  Params := '-NoProfile -Command "try { Rename-Computer -NewName ''' + NamePage.Values[0] + ''' -Force -ErrorAction Stop; exit 0 } catch { exit 1 }"';
  if not ShellExec('runas', ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '', SW_HIDE, ewWaitUntilTerminated, Code) then
   MsgBox('Computer rename was not approved. Applications remain installed using the existing computer name.', mbInformation, MB_OK)
  else if Code <> 0 then MsgBox('Windows could not rename this computer. Ask your Windows administrator. Applications remain installed.', mbError, MB_OK)
  else begin
   RegistrationName := NamePage.Values[0];
   MsgBox('Computer name change accepted. Setup will register this PC using the new name. Restart Windows after finishing all work; its stable computer identity and existing history are kept.', mbInformation, MB_OK);
  end;
 end;
 // Unattended updates retain their saved connections and do not interrupt staff with a login.
 // Interactive installs always enroll, whether the Windows name changed or stayed the same.
 if not WizardSilent then begin
  Apps := ''; Role := 'office'; DefaultServer := '';
  if WizardIsComponentSelected('office') then Apps := 'office';
  if WizardIsComponentSelected('pos') then begin
   if Apps <> '' then Apps := Apps + ',';
   Apps := Apps + 'pos'; Role := 'pos';
  end;
  if WizardIsComponentSelected('ops') then begin
   if Apps <> '' then Apps := Apps + ',';
   Apps := Apps + 'ops';
  end;
  if WizardIsComponentSelected('server') then begin Role := 'server'; DefaultServer := 'http://127.0.0.1:8080'; end;
  Params := '--apps "' + Apps + '" --role ' + Role + ' --name "' + RegistrationName + '" --server "' + DefaultServer + '"';
  SuiteExitCode := 1;
  WizardForm.StatusLabel.Caption := 'Connect to Operations and register this computer...';
  if not Exec(ExpandConstant('{tmp}\CoastYouth Retail Computer Registration.exe'), Params, '', SW_SHOW, ewWaitUntilTerminated, Code) then
   RaiseException('Applications were installed, but computer registration could not start. Run Computer Setup again to finish. Existing data and settings are kept.');
  if Code <> 0 then RaiseException('Applications were installed, but server connection and computer registration were not completed. Run Computer Setup again to finish. Existing data and settings are kept.');
  SuiteExitCode := 0;
  RecordComponent('Computer registration completed successfully.');
 end;
end;
