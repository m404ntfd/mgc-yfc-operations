#ifndef AppVersion
#define AppVersion "0.7.0"
#endif
[Setup]
AppId={{7412358D-0556-4978-AEA4-8297976D4992}
AppName=MGC YFC Operations
AppVersion={#AppVersion}
AppPublisher=MGC YFC
DefaultDirName={localappdata}\Programs\ThriftMartDispatch
DefaultGroupName=MGC YFC Operations
UsePreviousGroup=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=MGC-YFC-Operations-Setup-v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\dispatch.ico
AppMutex=ThriftMartDispatchServer,ThriftMartDispatchTray
UninstallDisplayName=MGC YFC Operations
DisableProgramGroupPage=yes
[Types]
Name: "server"; Description: "MGC YFC Operations Server (store computer)"
Name: "remote"; Description: "MGC YFC Operations Remote Manager (another computer)"
Name: "both"; Description: "Server and Remote Manager on this computer"
[Components]
Name: "server"; Description: "MGC YFC Operations Server"; Types: server both
Name: "remote"; Description: "MGC YFC Operations Remote Manager"; Types: remote both
[Tasks]
Name: "desktop"; Description: "Create desktop shortcuts"; Flags: unchecked
Name: "startup"; Description: "Start the server when I sign in to Windows"; Components: server; Flags: unchecked
[Files]
Source: "..\Start-MGC-YFC-Operations-Server.bat"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\verify_dispatch_backup.py"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\DISPATCH-JOURNAL.md"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\unlock_local.py"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\LOGIN-SECURITY.md"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\dist\MGC YFC Operations Server Console.exe"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\dist\MGC YFC Operations Server.exe"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\assets\dispatch.ico"; DestDir: "{app}\assets"; Components: server; Flags: ignoreversion
Source: "..\server.py"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\updater.py"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\launcher.py"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\README.txt"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\RELEASE-GUIDE.txt"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\Start-Thrift-Mart-Dispatch-Server.bat"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\Start-Store-Dispatch.bat"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\static\*"; DestDir: "{app}\static"; Components: server; Flags: ignoreversion recursesubdirs
Source: "..\runtime\*"; DestDir: "{app}\runtime"; Components: server; Flags: ignoreversion recursesubdirs
Source: "..\dist\MGC YFC Operations Remote Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\remote\README.txt"; DestDir: "{app}"; DestName: "Remote-Manager-README.txt"; Flags: ignoreversion
Source: "..\dist\MGC YFC Operations Server.exe"; DestDir: "{app}"; DestName: "Thrift Mart Dispatch Server.exe"; Components: server; Flags: ignoreversion
Source: "..\dist\MGC YFC Operations Server Console.exe"; DestDir: "{app}"; DestName: "Thrift Mart Dispatch Server Console.exe"; Components: server; Flags: ignoreversion
Source: "..\dist\MGC YFC Operations Remote Manager.exe"; DestDir: "{app}"; DestName: "Thrift Mart Dispatch Remote Manager.exe"; Flags: ignoreversion
[Icons]
Name: "{group}\MGC YFC Operations Server Console"; Filename: "{sys}\conhost.exe"; Parameters: """{app}\MGC YFC Operations Server Console.exe"" --console"; WorkingDir: "{app}"; IconFilename: "{app}\assets\dispatch.ico"; Components: server
Name: "{group}\Manage or Update MGC YFC Operations Server"; Filename: "{app}\MGC YFC Operations Remote Manager.exe"; Parameters: "--local-server"; Components: server
Name: "{group}\MGC YFC Operations Server"; Filename: "{app}\MGC YFC Operations Server.exe"; WorkingDir: "{app}"; Components: server
Name: "{group}\MGC YFC Operations Remote Manager"; Filename: "{app}\MGC YFC Operations Remote Manager.exe"; Components: remote
Name: "{group}\Restore MGC YFC Operations Server"; Filename: "{app}\MGC YFC Operations Remote Manager.exe"; Parameters: "--restore-dir ""{app}\data"""; Components: server
Name: "{userdesktop}\MGC YFC Operations Server"; Filename: "{app}\MGC YFC Operations Server.exe"; WorkingDir: "{app}"; Components: server; Tasks: desktop
Name: "{userdesktop}\MGC YFC Operations Remote Manager"; Filename: "{app}\MGC YFC Operations Remote Manager.exe"; Components: remote; Tasks: desktop
Name: "{userstartup}\MGC YFC Operations Server"; Filename: "{app}\MGC YFC Operations Server.exe"; WorkingDir: "{app}"; Components: server; Tasks: startup
[Run]
Filename: "{app}\MGC YFC Operations Server.exe"; Description: "Start MGC YFC Operations Server"; WorkingDir: "{app}"; Components: server; Flags: postinstall nowait skipifsilent shellexec unchecked
Filename: "{app}\MGC YFC Operations Remote Manager.exe"; Description: "Open MGC YFC Operations Remote Manager"; Components: remote; Flags: postinstall nowait skipifsilent unchecked

[Code]
procedure MigrateShortcut(OldName, NewName: String);
begin
  if FileExists(OldName) then begin
    if FileExists(NewName) then DeleteFile(OldName)
    else RenameFile(OldName, NewName);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    if WizardIsComponentSelected('server') then begin
      MigrateShortcut(ExpandConstant('{userstartup}\Thrift Mart Dispatch Server.lnk'), ExpandConstant('{userstartup}\MGC YFC Operations Server.lnk'));
      MigrateShortcut(ExpandConstant('{userdesktop}\Thrift Mart Dispatch Server.lnk'), ExpandConstant('{userdesktop}\MGC YFC Operations Server.lnk'));
    end;
    if WizardIsComponentSelected('remote') then
      MigrateShortcut(ExpandConstant('{userdesktop}\Thrift Mart Dispatch Remote Manager.lnk'), ExpandConstant('{userdesktop}\MGC YFC Operations Remote Manager.lnk'));
  end;
end;
