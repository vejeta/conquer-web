// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

plugins {
    id("com.android.application") version "9.4.0" apply false
    // Compose compiler plugin. AGP 9 has built-in Kotlin, so there is no
    // org.jetbrains.kotlin.android plugin
    id("org.jetbrains.kotlin.plugin.compose") version "2.3.0" apply false
    id("com.cefrium") version "0.17.0" apply false
}
