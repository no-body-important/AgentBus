import org.gradle.api.GradleException
import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

val signingPropertiesFile = rootProject.file("signing.properties")
val releaseSigningProperties = Properties().apply {
    if (signingPropertiesFile.exists()) {
        FileInputStream(signingPropertiesFile).use { input ->
            load(input)
        }
    }
}
val releaseSigningReady = signingPropertiesFile.exists()

android {
    namespace = "com.agentbus.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.agentbus.mobile"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (releaseSigningReady) {
                signingConfig = signingConfigs.getByName("release")
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    signingConfigs {
        create("release") {
            if (releaseSigningReady) {
                val storeFilePath = releaseSigningProperties.getProperty("storeFile")
                    ?: throw GradleException("signing.properties is missing storeFile")
                val storePasswordValue = releaseSigningProperties.getProperty("storePassword")
                    ?: throw GradleException("signing.properties is missing storePassword")
                val keyAliasValue = releaseSigningProperties.getProperty("keyAlias")
                    ?: throw GradleException("signing.properties is missing keyAlias")
                val keyPasswordValue = releaseSigningProperties.getProperty("keyPassword")
                    ?: throw GradleException("signing.properties is missing keyPassword")

                storeFile = rootProject.file(storeFilePath)
                storePassword = storePasswordValue
                keyAlias = keyAliasValue
                keyPassword = keyPasswordValue
            }
        }
    }
}

if (!releaseSigningReady) {
    tasks.matching { it.name.endsWith("Release") }.configureEach {
        doFirst {
            throw GradleException(
                "Release signing is not configured. Copy android-app/signing.properties.example to android-app/signing.properties and point storeFile at your keystore.",
            )
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.documentfile)
    implementation(libs.material)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons)

    debugImplementation(libs.androidx.compose.ui.tooling)
}
