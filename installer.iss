; FocusGuard - Inno Setup Script
; This script creates a single Setup.exe installer for Windows users

#define MyAppName "FocusGuard Smart Examiner"
#define MyAppVersion "1.0"
#define MyAppPublisher "Your School / Organization"
#define MyAppExeName "FocusGuard_Client.exe"
#define MyServerExeName "FocusGuard_Server.exe"

[Setup]
; App Information
AppId={{D9B2B395-88A9-4B5D-BC4A-32948622A606}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Installer Output
OutputDir=Output
OutputBaseFilename=Setup_SmartExaminer
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Request admin privileges for the Anti-Cheat to be installed correctly
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Client Files
Source: "dist\FocusGuard_Client\{#MyAppExeName}"; DestDir: "{app}\Client"; Flags: ignoreversion
Source: "dist\FocusGuard_Client\*"; DestDir: "{app}\Client"; Flags: ignoreversion recursesubdirs createallsubdirs

; Server Files
Source: "dist\FocusGuard_Server\{#MyServerExeName}"; DestDir: "{app}\Server"; Flags: ignoreversion
Source: "dist\FocusGuard_Server\*"; DestDir: "{app}\Server"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu Shortcuts
Name: "{group}\FocusGuard Client (Student)"; Filename: "{app}\Client\{#MyAppExeName}"
Name: "{group}\FocusGuard Server (Teacher)"; Filename: "{app}\Server\{#MyServerExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop Shortcuts
Name: "{autodesktop}\FocusGuard Client"; Filename: "{app}\Client\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\FocusGuard Server"; Filename: "{app}\Server\{#MyServerExeName}"; Tasks: desktopicon

[Run]
; Option to launch right after installing
Filename: "{app}\Client\{#MyAppExeName}"; Description: "Launch FocusGuard Client"; Flags: nowait postinstall skipifsilent
