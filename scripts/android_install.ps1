param(
    [switch]$Release,
    [switch]$NoLaunch,
    [string]$DeviceSerial
)

$ErrorActionPreference = 'Stop'

function Resolve-JavaHome {
    if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME 'bin\java.exe'))) {
        return $env:JAVA_HOME
    }

    $candidates = @(
        'C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot',
        'C:\Program Files\Android\Android Studio\jbr'
    )

    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate 'bin\java.exe')) {
            return $candidate
        }
    }

    throw 'Java 17 was not found. Install the JDK or set JAVA_HOME before running this helper.'
}

function Resolve-SdkRoot {
    $androidApp = Join-Path $PSScriptRoot '..\android-app'
    $localProperties = Join-Path $androidApp 'local.properties'
    if (Test-Path $localProperties) {
        $sdkLine = Get-Content $localProperties | Where-Object { $_ -match '^sdk\.dir=' } | Select-Object -First 1
        if ($sdkLine) {
            return $sdkLine.Substring(8)
        }
    }

    if ($env:ANDROID_SDK_ROOT -and (Test-Path $env:ANDROID_SDK_ROOT)) {
        return $env:ANDROID_SDK_ROOT
    }

    throw 'Android SDK root was not found. Make sure android-app/local.properties exists or set ANDROID_SDK_ROOT.'
}

function Resolve-ApkPath {
    param([string]$Variant)

    $androidApp = Join-Path $PSScriptRoot '..\android-app'
    $apkPath = Join-Path $androidApp "app\build\outputs\apk\$Variant\app-$Variant.apk"
    if (-not (Test-Path $apkPath)) {
        throw "APK not found at $apkPath"
    }

    return $apkPath
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$androidApp = Join-Path $repoRoot 'android-app'
$variant = if ($Release) { 'release' } else { 'debug' }
$gradleTask = if ($Release) { 'assembleRelease' } else { 'assembleDebug' }

$javaHome = Resolve-JavaHome
$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;$env:Path"
$sdkRoot = Resolve-SdkRoot
$adb = Join-Path $sdkRoot 'platform-tools\adb.exe'
if (-not (Test-Path $adb)) {
    throw "adb.exe was not found at $adb"
}

Push-Location $androidApp
try {
    & .\gradlew.bat $gradleTask
    $apkPath = Resolve-ApkPath -Variant $variant

    $deviceSerials = @()
    if ($DeviceSerial) {
        $deviceSerials = @($DeviceSerial)
    } else {
        $deviceSerials = & $adb devices | Select-String '\tdevice$' | ForEach-Object {
            ($_ -split '\s+')[0]
        }
    }

    if ($deviceSerials.Count -eq 0) {
        Write-Host "Built $apkPath"
        Write-Host 'No connected device found, so the APK was not installed.'
        exit 0
    }

    if ($deviceSerials.Count -gt 1 -and -not $DeviceSerial) {
        throw 'More than one connected device was found. Re-run with -DeviceSerial <serial>.'
    }

    foreach ($serial in $deviceSerials) {
        & $adb -s $serial install -r $apkPath
        if (-not $NoLaunch) {
            & $adb -s $serial shell am start -n com.agentbus.mobile/.MainActivity
        }
    }
}
finally {
    Pop-Location
}
