package com.soma2026.tikitalka.app

import androidx.compose.ui.window.ComposeUIViewController
import com.soma2026.tikitalka.di.appModule
import com.soma2026.tikitalka.di.initKoin

fun MainViewController() = ComposeUIViewController { App() }

fun startKoinIos(baseUrl: String, footballApiKey: String) = initKoin(
    baseUrl = baseUrl,
    footballApiKey = footballApiKey,
    extraModules = listOf(appModule),
)