plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.agenticos.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.agenticos.app"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        // Points at the phone's own localhost, which `adb reverse tcp:8000 tcp:8000`
        // tunnels back to port 8000 on the dev machine over the USB cable. This works
        // regardless of what Wi-Fi/tethered network either device is on, unlike a LAN
        // IP. Swap for a deployed HTTPS URL for a demo-day setup.
        buildConfigField("String", "BACKEND_BASE_URL", "\"http://127.0.0.1:8000\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.activity:activity-compose:1.9.3")

    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.animation:animation")

    // Networking: REST + WebSocket to the FastAPI backend
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")

    // Lottie for the orb animation states
    implementation("com.airbnb.android:lottie-compose:6.6.0")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
