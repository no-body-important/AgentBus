param(
    [switch]$KeepTempSigning
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

function Resolve-BuildToolsDir {
    param([string]$SdkRoot)

    $dir = Get-ChildItem -Path (Join-Path $SdkRoot 'build-tools') -Directory | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $dir) {
        throw 'Android build-tools were not found in the SDK.'
    }
    return $dir.FullName
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$androidApp = Join-Path $repoRoot 'android-app'
$javaHome = Resolve-JavaHome
$sdkRoot = Resolve-SdkRoot
$buildToolsDir = Resolve-BuildToolsDir -SdkRoot $sdkRoot
$apkSigner = Join-Path $buildToolsDir 'apksigner.bat'
if (-not (Test-Path $apkSigner)) {
    throw "apksigner was not found at $apkSigner"
}

$keystoreDir = Join-Path $androidApp 'keystore'
$keystorePath = Join-Path $keystoreDir 'release-verification.jks'
$signingPropertiesPath = Join-Path $androidApp 'signing.properties'
$signingBackupPath = Join-Path $androidApp 'signing.properties.bak'
$tempSigningCreated = $false

New-Item -ItemType Directory -Force $keystoreDir | Out-Null
if (Test-Path $signingPropertiesPath) {
    Copy-Item $signingPropertiesPath $signingBackupPath -Force
}

try {
    $env:JAVA_HOME = $javaHome
    $env:Path = "$javaHome\bin;$env:Path"

    & (Join-Path $javaHome 'bin\keytool.exe') `
        -genkeypair `
        -v `
        -keystore $keystorePath `
        -alias agentbus `
        -keyalg RSA `
        -keysize 2048 `
        -validity 3650 `
        -storepass verification-pass `
        -keypass verification-pass `
        -dname 'CN=AgentBus, OU=AgentBus, O=AgentBus, L=Seattle, S=WA, C=US'

    @"
storeFile=keystore/release-verification.jks
storePassword=verification-pass
keyAlias=agentbus
keyPassword=verification-pass
"@ | Set-Content -Path $signingPropertiesPath -Encoding ascii
    $tempSigningCreated = $true

    Push-Location $androidApp
    try {
        & .\gradlew.bat assembleRelease
    }
    finally {
        Pop-Location
    }

    $apkPath = Join-Path $androidApp 'app\build\outputs\apk\release\app-release.apk'
    if (-not (Test-Path $apkPath)) {
        throw "Release APK was not produced at $apkPath"
    }

    & $apkSigner verify --verbose --print-certs $apkPath
    Write-Host "Verified release APK at $apkPath"
}
finally {
    if ($tempSigningCreated -and -not $KeepTempSigning) {
        Remove-Item $signingPropertiesPath -Force -ErrorAction SilentlyContinue
        Remove-Item $keystorePath -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $signingBackupPath) {
        Move-Item $signingBackupPath $signingPropertiesPath -Force
    }
}
