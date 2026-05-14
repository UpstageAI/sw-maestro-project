package com.newspick.quiz;

public record QuizQuestion(
        String id,
        String question,
        boolean answer,
        String explanation
) {
}
