[Setup]
UninstallDisplayIcon={app}\CoastYouth Retail OFFICE.exe
AppId={{CF27FBAA-F830-4BF3-A509-417F1D4A3B99}
AppName=CoastYouth Retail OFFICE
AppVersion=1.12.0
AppPublisher=CoastYouth Retail
DefaultDirName={localappdata}\Programs\CoastYouthRetailOffice
DefaultGroupName=CoastYouth Retail
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=CoastYouth-Retail-OFFICE-Setup-v1.12.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\office.ico
DisableProgramGroupPage=yes
[Files]
Source: "..\dist\CoastYouth Retail OFFICE.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\CoastYouth Retail OFFICE"; Filename: "{app}\CoastYouth Retail OFFICE.exe"
Name: "{group}\Configure OFFICE connection"; Filename: "{app}\CoastYouth Retail OFFICE.exe"; Parameters: "--configure"
Name: "{userdesktop}\CoastYouth Retail OFFICE"; Filename: "{app}\CoastYouth Retail OFFICE.exe"
[Run]
Filename: "{app}\CoastYouth Retail OFFICE.exe"; Description: "Open CoastYouth Retail OFFICE"; Flags: postinstall nowait skipifsilent
