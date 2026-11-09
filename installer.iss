#ifndef PackageId
  #define PackageId "WeChatJumpHelper.Personal"
#endif
#ifndef PayloadDir
  #define PayloadDir "dist"
#endif
#ifndef LanguageFile
  #define LanguageFile "compiler:Default.isl"
#endif

[Setup]
AppId={#PackageId}
AppName=微信跳一跳辅助
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\WeChatJumpHelper
DefaultGroupName=微信跳一跳辅助
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19045
UninstallDisplayIcon={app}\WeChatJumpHelper.exe
OutputBaseFilename=微信跳一跳辅助-安装程序-Windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "setup"; MessagesFile: "{#LanguageFile}"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\微信跳一跳辅助"; Filename: "{app}\WeChatJumpHelper.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\微信跳一跳辅助"; Filename: "{app}\WeChatJumpHelper.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\WeChatJumpHelper.exe"; Description: "{cm:LaunchProgram,微信跳一跳辅助}"; Flags: nowait postinstall skipifsilent
