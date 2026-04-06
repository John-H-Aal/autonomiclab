; AutonomicLab Inno Setup Script

#define AppName "AutonomicLab"
#define AppVersion "1.0.0"
#define AppPublisher "Astrid Juhl Terkelsen, Aarhus University"
#define AppURL "https://github.com/John-H-Aal/autonomiclab"
#define AppExeName "AutonomicLab.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=AutonomicLab_Setup
SetupIconFile=assets\autonomiclab.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\{#AppExeName}";         DestDir: "{app}"; Flags: ignoreversion
Source: "dist\autonomiclab_splash.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer_config.yaml";       DestDir: "{app}"; DestName: "config.yaml"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{userprograms}\{#AppName}\Uninstall"; Filename: "{uninstallexe}"

[Dirs]
Name: "{userdocs}\AutonomicLab\data"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch AutonomicLab"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: string;
  ConfigContent: TStringList;
  DocsPath: string;
begin
  if CurStep = ssPostInstall then
  begin
    DocsPath := ExpandConstant('{userdocs}\AutonomicLab\data');
    ConfigFile := ExpandConstant('{app}\config.yaml');
    ConfigContent := TStringList.Create;
    try
      ConfigContent.Add('# AutonomicLab configuration');
      ConfigContent.Add('# Edit data_folder to match the location of your Finapres data');
      ConfigContent.Add('');
      ConfigContent.Add('data_folder: "' + StringReplace(DocsPath, '\', '/', [rfReplaceAll]) + '"');
      ConfigContent.SaveToFile(ConfigFile);
    finally
      ConfigContent.Free;
    end;
  end;
end;
