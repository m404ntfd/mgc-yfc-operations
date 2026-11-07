[Setup]
AppId={{8CDE3797-D37D-4200-BC84-03B9F5F136AA}
AppName=MGC YFC Point of Sale
AppVersion=1.1.0
AppPublisher=MGC YFC
DefaultDirName={localappdata}\Programs\MGCYFCPOS
DefaultGroupName=MGC YFC Point of Sale
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=MGC-YFC-POS-Setup-v1.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\dispatch.ico
DisableProgramGroupPage=yes
[Files]
Source: "..\dist\MGC YFC Point of Sale.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\POS-README.txt"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\MGC YFC Point of Sale"; Filename: "{app}\MGC YFC Point of Sale.exe"
Name: "{group}\Change POS server connection"; Filename: "{app}\MGC YFC Point of Sale.exe"; Parameters: "--configure"
Name: "{userdesktop}\MGC YFC Point of Sale"; Filename: "{app}\MGC YFC Point of Sale.exe"
[Run]
Filename: "{app}\MGC YFC Point of Sale.exe"; Description: "Open MGC YFC Point of Sale"; Flags: postinstall nowait skipifsilent
