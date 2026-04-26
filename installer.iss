; AutonomicLab Inno Setup Script

#define AppName "AutonomicLab"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Astrid Juhl Terkelsen, Aarhus University"
#ifndef UsersDbToken
  #define UsersDbToken ""
#endif
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
#ifdef AppPassword
Password={#AppPassword}
Encryption=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\{#AppExeName}";          DestDir: "{app}"; Flags: ignoreversion
Source: "dist\autonomiclab_splash.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer_config.yaml";        DestDir: "{app}"; DestName: "config.yaml"; Flags: ignoreversion
Source: "dist\UserGuide.pdf";           DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{userdesktop}\{#AppName}";          Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userdesktop}\{#AppName} User Guide"; Filename: "{app}\UserGuide.pdf"; Tasks: desktopicon; Check: FileExists(ExpandConstant('{app}\UserGuide.pdf'))
Name: "{userprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{userprograms}\{#AppName}\User Guide"; Filename: "{app}\UserGuide.pdf"; Check: FileExists(ExpandConstant('{app}\UserGuide.pdf'))
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
      StringChangeEx(DocsPath, '\', '/', True);
      ConfigContent.Add('data_folder: "' + DocsPath + '"');
      ConfigContent.Add('');
      ConfigContent.Add('users_db_token: "{#UsersDbToken}"');
      ConfigContent.Add('allow_guest: true');
      ConfigContent.SaveToFile(ConfigFile);
    finally
      ConfigContent.Free;
    end;
  end;
end;
