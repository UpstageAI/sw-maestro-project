package com.soma.ai13be.persona.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.persona.entity.Persona;

public interface PersonaRepository extends JpaRepository<Persona, Long> {

	boolean existsByDomainName(String domainName);

	List<Persona> findByEnabledTrueOrderByDomainNameAsc();
}
