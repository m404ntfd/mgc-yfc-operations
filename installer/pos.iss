[Setup]
UninstallDisplayIcon={app}\MGC YFC Point of Sale.exe
AppId={{8CDE3797-D37D-4200-BC84-03B9F5F136AA}
AppName=CoastYouth Retail DESK
AppVersion=1.15.0
AppPublisher=CoastYouth Retail
DefaultDirName={localappdata}\Programs\MGCYFCPOS
DefaultGroupName=MGC YFC Point of Sale
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=MGC-YFC-POS-Setup-v1.15.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\desk.ico
DisableProgramGroupPage=yes
[Files]
Source: "..\dist\MGC YFC Point of Sale.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\POS-README.txt"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\CoastYouth Retail DESK"; Filename: "{app}\MGC YFC Point of Sale.exe"
Name: "{group}\Change POS server connection"; Filename: "{app}\MGC YFC Point of Sale.exe"; Parameters: "--configure"
Name: "{userdesktop}\CoastYouth Retail DESK"; Filename: "{app}\MGC YFC Point of Sale.exe"
[Run]
Filename: "{app}\MGC YFC Point of Sale.exe"; Description: "Open CoastYouth Retail DESK"; Flags: postinstall nowait skipifsilent

[InstallDelete]
Type: files; Name: "{group}\MGC YFC Point of Sale.lnk"
Type: files; Name: "{userdesktop}\MGC YFC Point of Sale.lnk"
