package com.soma.ai13be.common.client.dto;

public record SolarChatMessage(
	String role,
	String content
) {

	public SolarChatMessage {
		if (isBlank(role)) {
			throw new IllegalArgumentException("role must not be blank");
		}
		if (isBlank(content)) {
			throw new IllegalArgumentException("content must not be blank");
		}
	}

	public static SolarChatMessage system(String content) {
		return new SolarChatMessage("system", content);
	}

	public static SolarChatMessage user(String content) {
		return new SolarChatMessage("user", content);
	}

	public static SolarChatMessage assistant(String content) {
		return new SolarChatMessage("assistant", content);
	}

	private static boolean isBlank(String value) {
		return value == null || value.isBlank();
	}
}
