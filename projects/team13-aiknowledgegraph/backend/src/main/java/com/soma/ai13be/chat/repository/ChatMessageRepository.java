package com.soma.ai13be.chat.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.chat.entity.ChatMessage;
import com.soma.ai13be.chat.entity.ChatSession;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

	List<ChatMessage> findBySessionOrderBySequenceAsc(ChatSession session);

	long countBySession(ChatSession session);
}
