// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

import javax.inject.Inject

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.cefrium")
}

/**
 * Copies the website (../web) into the app's assets as assets/web/, leaving
 * out what an offline copy has no use for: the server-side status page, the
 * administrator and sign-up pages, and the tutorial videos (H.264/AAC, which
 * the royalty-free engine does not decode; the pages hide the video links
 * when a video is missing). It also writes the site's server.js with the
 * address of the game server, so the links to the game and its status go
 * online from the bundled copy.
 */
abstract class CopyWeb : DefaultTask() {
    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val webDir: DirectoryProperty

    @get:Input
    abstract val serverUrl: Property<String>

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @get:Inject
    abstract val fs: FileSystemOperations

    @TaskAction
    fun copy() {
        val target = outputDir.get().dir("web")
        fs.delete { delete(target.asFile) }
        fs.copy {
            from(webDir) {
                exclude("status/**", "server.js", "admin.html", "signup.html")
                exclude("tutorial/*.mp4", "tutorial/*.vtt", "**/*.md")
            }
            into(target.asFile)
        }
        target.file("server.js").asFile.writeText(
            "// Written by the Android build\n" +
                "window.CONQUER_CONFIG = { server: '${serverUrl.get()}' };\n"
        )
    }
}

android {
    namespace = "com.vejeta.conquer"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.vejeta.conquer"
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    buildTypes {
        debug {
            // The emulator on a PC is x86_64
            ndk {
                abiFilters += listOf("x86_64")
            }
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    buildFeatures {
        compose = true
    }

    // Chromium's assets must be stored uncompressed
    androidResources {
        noCompress += listOf("dat", "pak", "bin")
    }

    // Chromium reads its native libraries from disk (AGP 9 wants this here,
    // not as android:extractNativeLibs in the manifest)
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

androidComponents {
    onVariants { variant ->
        val copyWeb = tasks.register<CopyWeb>("copyWeb${variant.name.replaceFirstChar { it.uppercase() }}") {
            webDir.set(layout.dir(provider { rootProject.file("../web") }))
            serverUrl.set("https://conquer.vejeta.com")
        }
        variant.sources.assets?.addGeneratedSourceDirectory(copyWeb, CopyWeb::outputDir)
    }
}

dependencies {
    // The royalty-free engine (VP8, VP9, Opus, Vorbis): the game has no
    // video. cefrium-compose depends on the full-codec cefrium-sdk, which
    // would be a second copy of the same classes: leave it out
    implementation("com.cefrium:cefrium-sdk-libre:0.17.0")
    implementation("com.cefrium:cefrium-compose:0.17.0") {
        exclude(group = "com.cefrium", module = "cefrium-sdk")
    }

    // Runtime dependencies the engine expects (quickstart)
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.mediarouter:mediarouter:1.7.0")
    implementation("androidx.core:core:1.16.0")
    implementation("androidx.browser:browser:1.8.0")

    // The app
    implementation(platform("androidx.compose:compose-bom:2025.10.01"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.activity:activity-compose:1.11.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
}
