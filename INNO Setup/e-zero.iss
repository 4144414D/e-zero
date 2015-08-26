; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "e-zero"
#define MyAppVersion "26-Aug-2015"
#define MyAppPublisher "Adam Swann"
#define MyAppURL "https://4144414d.github.io/e-zero/"
#define MyAppExeName "e-zero.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{D06089D9-C267-461B-BE76-FA9BFF2E61B9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes
ChangesEnvironment=true

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: modifypath; Description: "Add application directory to your environmental path"
Name: ContextMenu; Description: "Add right click context menu to verify all images within a directory"

[Code]
const 
    ModPathName = 'modifypath'; 
    ModPathType = 'user'; 

function ModPathDir(): TArrayOfString; 
begin 
    setArrayLength(Result, 1) 
    Result[0] := ExpandConstant('{app}'); 
end; 
#include "modpath.iss"

[Files]
Source: "C:\Users\Adam\Documents\GitHub\e-zero\e-zero python\dist\e-zero.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Adam\Documents\GitHub\e-zero\e-zero python\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Registry]
Root: HKCR; Subkey: "Directory\shell\e-zero verify"; Flags: uninsdeletekey; Tasks: ContextMenu
Root: HKCR; Subkey: "Directory\shell\e-zero verify\command"; ValueType: string; ValueData: "cmd /c ""echo ""%1"" & e-zero verify ""%1"" & pause"""; Tasks: ContextMenu


[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; [Run]
; Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
