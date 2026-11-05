#ifndef AppVersion
#define AppVersion "0.7.0"
#endif
[Setup]
AppId={{7412358D-0556-4978-AEA4-8297976D4992}
AppName=Thrift Mart Dispatch
AppVersion={#AppVersion}
AppPublisher=Thrift Mart
DefaultDirName={localappdata}\Programs\ThriftMartDispatch
DefaultGroupName=Thrift Mart Dispatch
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Thrift-Mart-Dispatch-Setup-v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\dispatch.ico
AppMutex=ThriftMartDispatchServer,ThriftMartDispatchTray
UninstallDisplayName=Thrift Mart Dispatch
DisableProgramGroupPage=yes
[Types]
Name: "server"; Description: "Thrift Mart Dispatch Server (store computer)"
Name: "remote"; Description: "Thrift Mart Dispatch Remote Manager (another computer)"
Name: "both"; Description: "Server and Remote Manager on this computer"
[Components]
Name: "server"; Description: "Thrift Mart Dispatch Server"; Types: server both
Name: "remote"; Description: "Thrift Mart Dispatch Remote Manager"; Types: remote both
[Tasks]
Name: "desktop"; Description: "Create desktop shortcuts"; Flags: unchecked
Name: "startup"; Description: "Start the server when I sign in to Windows"; Components: server; Flags: unchecked
[Files]
Source: "..\unlock_local.py"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\LOGIN-SECURITY.md"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\dist\Thrift Mart Dispatch Server Console.exe"; DestDir: "{app}"; Components: server; Flags: ignoreversion
Source: "..\dist\Thrift Mart Dispatch Server.exe"; DestDir: "{app}"; Components: server; Flags: ignoreversion
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
Source: "..\dist\Thrift Mart Dispatch Remote Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\remote\README.txt"; DestDir: "{app}"; DestName: "Remote-Manager-README.txt"; Flags: ignoreversion
[Icons]
Name: "{group}\Thrift Mart Dispatch Server Console"; Filename: "{sys}\conhost.exe"; Parameters: """{app}\Thrift Mart Dispatch Server Console.exe"" --console"; WorkingDir: "{app}"; IconFilename: "{app}\assets\dispatch.ico"; Components: server
Name: "{group}\Manage or Update Thrift Mart Dispatch Server"; Filename: "{app}\Thrift Mart Dispatch Remote Manager.exe"; Parameters: "--local-server"; Components: server
Name: "{group}\Thrift Mart Dispatch Server"; Filename: "{app}\Thrift Mart Dispatch Server.exe"; WorkingDir: "{app}"; Components: server
Name: "{group}\Thrift Mart Dispatch Remote Manager"; Filename: "{app}\Thrift Mart Dispatch Remote Manager.exe"; Components: remote
Name: "{group}\Restore Thrift Mart Dispatch Server"; Filename: "{app}\Thrift Mart Dispatch Remote Manager.exe"; Parameters: "--restore-dir ""{app}\data"""; Components: server
Name: "{userdesktop}\Thrift Mart Dispatch Server"; Filename: "{app}\Thrift Mart Dispatch Server.exe"; WorkingDir: "{app}"; Components: server; Tasks: desktop
Name: "{userdesktop}\Thrift Mart Dispatch Remote Manager"; Filename: "{app}\Thrift Mart Dispatch Remote Manager.exe"; Components: remote; Tasks: desktop
Name: "{userstartup}\Thrift Mart Dispatch Server"; Filename: "{app}\Thrift Mart Dispatch Server.exe"; WorkingDir: "{app}"; Components: server; Tasks: startup
[Run]
Filename: "{app}\Thrift Mart Dispatch Server.exe"; Description: "Start Thrift Mart Dispatch Server"; WorkingDir: "{app}"; Components: server; Flags: postinstall nowait skipifsilent shellexec unchecked
Filename: "{app}\Thrift Mart Dispatch Remote Manager.exe"; Description: "Open Thrift Mart Dispatch Remote Manager"; Components: remote; Flags: postinstall nowait skipifsilent unchecked
