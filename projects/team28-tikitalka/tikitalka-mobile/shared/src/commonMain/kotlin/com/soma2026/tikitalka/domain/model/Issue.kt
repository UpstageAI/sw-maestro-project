package com.soma2026.tikitalka.domain.model

data class Issue(
    val id: String,
    val title: String,
    val summary: String,
    val tag: String,
    val publishedAt: String,
    val hotnessScore: Int,
    val url: String,
    val source: String,
    val imageUrl: String? = null,
    val originalContent: String? = null,
)