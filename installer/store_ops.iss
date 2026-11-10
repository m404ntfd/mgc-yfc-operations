[Setup]
UninstallDisplayIcon={app}\CoastYouth Retail STORE OPS.exe
AppId={{A302D8B1-4C13-4DED-9B51-E64922F1A973}
AppName=CoastYouth Retail STORE OPS
AppVersion=1.1.0
AppPublisher=CoastYouth Retail
DefaultDirName={localappdata}\Programs\CoastYouthRetailStoreOps
DefaultGroupName=CoastYouth Retail
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=CoastYouth-Retail-STORE-OPS-Setup-v1.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\store-ops.ico
DisableProgramGroupPage=yes
[Files]
Source: "..\dist\CoastYouth Retail STORE OPS.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\CoastYouth Retail STORE OPS"; Filename: "{app}\CoastYouth Retail STORE OPS.exe"
Name: "{group}\Configure STORE OPS connection"; Filename: "{app}\CoastYouth Retail STORE OPS.exe"; Parameters: "--configure"
Name: "{userdesktop}\CoastYouth Retail STORE OPS"; Filename: "{app}\CoastYouth Retail STORE OPS.exe"
[Run]
Filename: "{app}\CoastYouth Retail STORE OPS.exe"; Description: "Open CoastYouth Retail STORE OPS"; Flags: postinstall nowait skipifsilent
