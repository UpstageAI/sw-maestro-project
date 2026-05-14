package com.soma2026.tikitalka.ui.util

import kotlin.math.max

private const val CHARS_PER_MINUTE = 800

fun estimatedReadingMinutes(text: String): Int =
    max(1, (text.trim().length + CHARS_PER_MINUTE - 1) / CHARS_PER_MINUTE)
