package com.soma.ai13be.knowledge.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.soma.ai13be.knowledge.entity.KnowledgeEdge;

public interface KnowledgeEdgeRepository extends JpaRepository<KnowledgeEdge, Long> {

	@Query("""
		select edge
		from KnowledgeEdge edge
		join fetch edge.sourceNode
		join fetch edge.targetNode
		where edge.sourceNode.id = :nodeId
		   or edge.targetNode.id = :nodeId
		order by edge.createdAt desc
		""")
	List<KnowledgeEdge> findOneHopEdges(@Param("nodeId") Long nodeId);
}
