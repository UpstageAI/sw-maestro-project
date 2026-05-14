package com.soma2026.tikitalka.di

import org.koin.core.KoinApplication
import org.koin.core.context.startKoin
import org.koin.core.module.Module

fun initKoin(
    baseUrl: String,
    footballApiKey: String,
    isDebug: Boolean = false,
    extraModules: List<Module> = emptyList(),
    appDeclaration: KoinApplication.() -> Unit = {},
): KoinApplication = startKoin {
    appDeclaration()
    modules(
        platformModule,
        networkModule(baseUrl, isDebug),
        footballNetworkModule(footballApiKey),
        repositoryModule,
        useCaseModule,
        viewModelModule,
        *extraModules.toTypedArray(),
    )
}