#ifndef AppVersion
#define AppVersion "0.46.0"
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
[Files]
Source: "..\dist\MGC-YFC-Operations-Setup-v{#AppVersion}.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\dist\CoastYouth-Retail-OFFICE-Setup-v1.5.0.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\dist\MGC-YFC-POS-Setup-v1.8.0.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Code]
var NamePage: TInputQueryWizardPage;
procedure InitializeWizard;
begin
 NamePage := CreateInputQueryPage(wpSelectComponents, 'Computer identity', 'Optional Windows computer name', 'Leave blank to keep the current name. Renaming requires Windows administrator approval and takes effect after a later restart. Terminal registration is completed in DESK and managed in OFFICE. Renaming a server may require updating its address on client computers. Existing data is kept.');
 NamePage.Add('New computer name (letters, numbers, hyphens; maximum 15):', False);
end;
function NextButtonClick(CurPageID: Integer): Boolean;
var S: String; I: Integer; HasLetter: Boolean;
begin
 Result := True;
 if CurPageID <> NamePage.ID then Exit;
 S := Uppercase(Trim(NamePage.Values[0])); NamePage.Values[0] := S;
 if S = '' then Exit;
 HasLetter := False;
 Result := (Length(S) <= 15) and (S[1] <> '-') and (S[Length(S)] <> '-');
 for I := 1 to Length(S) do begin
  if (S[I] >= 'A') and (S[I] <= 'Z') then HasLetter := True
  else if not (((S[I] >= '0') and (S[I] <= '9')) or (S[I] = '-')) then Result := False;
 end;
 Result := Result and HasLetter;
 if not Result then MsgBox('Use 1–15 letters, numbers or hyphens, with at least one letter. Do not start or end with a hyphen.', mbError, MB_OK);
end;
procedure RunInstaller(FileName, Parameters, DirectoryOption: String);
var Code: Integer; Target: String;
begin
 if WizardSilent then Parameters := Parameters + ' /VERYSILENT /SUPPRESSMSGBOXES';
 Target := ExpandConstant('{param:' + DirectoryOption + '|}');
 if Target <> '' then begin
  if Pos('"', Target) > 0 then RaiseException('Invalid installation folder.');
  Parameters := Parameters + ' /DIR="' + Target + '"';
 end;
 if not Exec(ExpandConstant('{tmp}\') + FileName, Parameters, '', SW_SHOW, ewWaitUntilTerminated, Code) then
  RaiseException('Could not start the selected installer. Existing application data has not been reset.');
 if (Code <> 0) and (Code <> 3010) then RaiseException('The selected installer did not finish. Setup stopped; review its error before retrying.');
end;
procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer; Params: String;
begin
 if CurStep <> ssPostInstall then Exit;
 if WizardIsComponentSelected('server') then RunInstaller('MGC-YFC-Operations-Setup-v{#AppVersion}.exe', '/NORESTART /TYPE=both', 'SERVERDIR');
 if WizardIsComponentSelected('office') then RunInstaller('CoastYouth-Retail-OFFICE-Setup-v1.5.0.exe', '/NORESTART', 'OFFICEDIR');
 if WizardIsComponentSelected('pos') then RunInstaller('MGC-YFC-POS-Setup-v1.8.0.exe', '/NORESTART', 'POSDIR');
 if NamePage.Values[0] <> '' then begin
  Params := '-NoProfile -Command "try { Rename-Computer -NewName ''' + NamePage.Values[0] + ''' -Force -ErrorAction Stop; exit 0 } catch { exit 1 }"';
  if not ShellExec('runas', ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '', SW_HIDE, ewWaitUntilTerminated, Code) then
   MsgBox('Computer rename was not approved. Applications remain installed using the existing computer name.', mbInformation, MB_OK)
  else if Code <> 0 then MsgBox('Windows could not rename this computer. Ask your Windows administrator. Applications remain installed.', mbError, MB_OK)
  else MsgBox('Computer name changed. Restart Windows after finishing all work. Setup will not restart it automatically.', mbInformation, MB_OK);
 end;
 if not WizardSilent then MsgBox('Connect DESK and OFFICE to the existing Operations server address. On each checkout, sign in as an administrator and choose Terminal setup. Use OFFICE > Terminals to assign its layout. Keep the existing server data folder and settings.', mbInformation, MB_OK);
end;
