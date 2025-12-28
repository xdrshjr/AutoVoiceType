; AutoVoiceType - Inno Setup 安装脚本
; 用于创建 Windows 安装程序

#define MyAppName "AutoVoiceType"
#define MyAppNameZh "智能语音输入法"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AutoVoiceType Team"
#define MyAppURL "https://github.com/yourusername/AutoVoiceType"
#define MyAppExeName "AutoVoiceType.exe"
#define MyAppDescription "智能语音输入工具"

[Setup]
; 应用基本信息
AppId={{A5E8F9C2-D4B6-4A3E-8F2C-1D9E7B4A6C8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2025 {#MyAppPublisher}

; 安装路径
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 输出配置
OutputDir=dist\installer
OutputBaseFilename=AutoVoiceType_Setup_{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; 权限设置
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 架构设置
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; 许可和信息
LicenseFile=LICENSE.txt
; InfoBeforeFile=README.txt

; 卸载设置
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; 界面设置
ShowLanguageDialog=no
DisableWelcomePage=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "其他选项:"
Name: "quicklaunchicon"; Description: "创建快速启动栏图标(&Q)"; GroupDescription: "其他选项:"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动(&A)"; GroupDescription: "其他选项:"

[Files]
; 主程序文件（假设使用 PyInstaller 的 onedir 模式）
Source: "dist\AutoVoiceType\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 如果使用 onefile 模式，使用下面这行替代：
; Source: "dist\AutoVoiceType.exe"; DestDir: "{app}"; Flags: ignoreversion

; 配置文件模板
Source: "config\default_config.json"; DestDir: "{app}\config"; Flags: ignoreversion

; 文档文件
Source: "docs\USER_MANUAL.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
; Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\用户手册"; Filename: "{app}\docs\USER_MANUAL.md"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"

; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 快速启动栏快捷方式
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; 开机自启动注册表项（可选）
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

; 应用注册信息
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; Flags: uninsdeletekeyifempty
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\Settings"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\Settings"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

[Run]
; 安装完成后的操作
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载前的清理操作
; Filename: "{cmd}"; Parameters: "/c taskkill /f /im {#MyAppExeName}"; Flags: runhidden

[Code]
// Pascal 脚本代码

// 检查应用是否正在运行
function IsAppRunning(): Boolean;
var
  FWMIService: Variant;
  FSWbemLocator: Variant;
  FWbemObjectSet: Variant;
begin
  Result := false;
  try
    FSWbemLocator := CreateOleObject('WbemScripting.SWbemLocator');
    FWMIService := FSWbemLocator.ConnectServer('', 'root\CIMV2', '', '');
    FWbemObjectSet := FWMIService.ExecQuery('SELECT * FROM Win32_Process WHERE Name="' + '{#MyAppExeName}' + '"');
    Result := (FWbemObjectSet.Count > 0);
  except
    Result := false;
  end;
end;

// 安装前检查
function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // 检查是否已经在运行
  if IsAppRunning() then
  begin
    if MsgBox('检测到 {#MyAppName} 正在运行。'#13#10#13#10'请先关闭应用程序，然后点击"是"继续安装，或点击"否"退出安装。', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 用户选择继续，尝试结束进程
      Exec('taskkill.exe', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, Result);
      Sleep(1000);  // 等待进程完全结束
      Result := True;
    end
    else
    begin
      Result := False;
    end;
  end;
end;

// 卸载前检查
function InitializeUninstall(): Boolean;
begin
  Result := True;
  
  // 检查是否正在运行
  if IsAppRunning() then
  begin
    if MsgBox('检测到 {#MyAppName} 正在运行。'#13#10#13#10'是否关闭应用程序并继续卸载？', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('taskkill.exe', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, Result);
      Sleep(1000);
      Result := True;
    end
    else
    begin
      Result := False;
    end;
  end;
end;

// 卸载后清理
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigPath: String;
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // 询问是否删除配置文件
    ConfigPath := ExpandConstant('{%USERPROFILE}\.autovoicetype');
    if DirExists(ConfigPath) then
    begin
      if MsgBox('是否删除用户配置文件和日志？'#13#10#13#10 + ConfigPath, 
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        // 删除配置目录
        Exec('cmd.exe', '/c rmdir /s /q "' + ConfigPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
  end;
end;

// 安装完成后的提示
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 可以在这里添加额外的安装后操作
  end;
end;

