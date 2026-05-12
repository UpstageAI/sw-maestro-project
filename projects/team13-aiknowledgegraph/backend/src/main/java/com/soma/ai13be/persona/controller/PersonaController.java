package com.soma.ai13be.persona.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.soma.ai13be.common.dto.ErrorResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.persona.dto.request.CreatePersonaCommand;
import com.soma.ai13be.persona.dto.request.UpdatePersonaCommand;
import com.soma.ai13be.persona.dto.response.PersonaResult;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.service.PersonaService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

@Tag(name = "Persona", description = "페르소나 관리 API")
@RestController
@RequestMapping("/api/personas")
@RequiredArgsConstructor
public class PersonaController {

	private final PersonaService personaService;

	@Operation(
		summary = "페르소나 생성",
		description = "도메인 이름을 입력받아 Solar API를 호출해 페르소나 이름과 시스템 프롬프트를 자동 생성합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "201", description = "페르소나 생성 성공",
			content = @Content(schema = @Schema(implementation = PersonaResult.class))),
		@ApiResponse(responseCode = "400", description = "domainName이 null 또는 공백",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "409", description = "동일한 domainName의 페르소나가 이미 존재",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "Solar API 프롬프트 생성 실패",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping
	public ResponseEntity<PersonaResult> create(@RequestBody CreatePersonaCommand command) {
		if (command == null || !StringUtils.hasText(command.domainName())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "domainName must not be blank");
		}

		Persona persona = personaService.create(command.domainName());

		return ResponseEntity.status(HttpStatus.CREATED).body(PersonaResult.from(persona));
	}

	@Operation(
		summary = "페르소나 목록 조회",
		description = "저장된 모든 페르소나를 조회합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "페르소나 목록 조회 성공",
			content = @Content(array = @ArraySchema(schema = @Schema(implementation = PersonaResult.class))))
	})
	@GetMapping
	public ResponseEntity<List<PersonaResult>> findAll() {
		return ResponseEntity.ok(
			personaService.findAll().stream()
				.map(PersonaResult::from)
				.toList()
		);
	}

	@Operation(
		summary = "페르소나 시스템 프롬프트 재생성",
		description = "Solar API를 다시 호출하여 해당 페르소나의 시스템 프롬프트를 새로 생성합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "재생성 성공",
			content = @Content(schema = @Schema(implementation = PersonaResult.class))),
		@ApiResponse(responseCode = "404", description = "페르소나를 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "Solar API 프롬프트 생성 실패",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping("/{personaId}/regenerate")
	public ResponseEntity<PersonaResult> regenerate(
		@Parameter(description = "재생성할 페르소나 ID", example = "1")
		@PathVariable Long personaId
	) {
		Persona persona = personaService.regenerate(personaId);
		return ResponseEntity.ok(PersonaResult.from(persona));
	}

	@Operation(
		summary = "페르소나 시스템 프롬프트 수정",
		description = "페르소나의 시스템 프롬프트를 직접 수정합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "수정 성공",
			content = @Content(schema = @Schema(implementation = PersonaResult.class))),
		@ApiResponse(responseCode = "400", description = "systemPrompt가 null 또는 공백",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "404", description = "페르소나를 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PutMapping("/{personaId}")
	public ResponseEntity<PersonaResult> update(
		@Parameter(description = "수정할 페르소나 ID", example = "1")
		@PathVariable Long personaId,
		@RequestBody UpdatePersonaCommand command
	) {
		if (command == null || !StringUtils.hasText(command.systemPrompt())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "systemPrompt must not be blank");
		}

		Persona persona = personaService.update(personaId, command.systemPrompt());
		return ResponseEntity.ok(PersonaResult.from(persona));
	}

	@Operation(
		summary = "페르소나 삭제",
		description = "페르소나를 삭제합니다. 기본 내장 페르소나(builtIn=true)는 삭제할 수 없습니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "204", description = "삭제 성공"),
		@ApiResponse(responseCode = "404", description = "페르소나를 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "409", description = "기본 내장 페르소나는 삭제할 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@DeleteMapping("/{personaId}")
	public ResponseEntity<Void> delete(
		@Parameter(description = "삭제할 페르소나 ID", example = "1")
		@PathVariable Long personaId
	) {
		personaService.delete(personaId);

		return ResponseEntity.noContent().build();
	}
}
