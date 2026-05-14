import type * as React from "react"
import {
  AlertCircle,
  CheckCircle2,
  CircleDot,
  FileInput,
  Link2,
  Loader2,
  Plus,
  Upload,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import type { KnowledgeCardPayload, SourcePayload } from "@/lib/api"
import { sourceTypes } from "@/lib/samples"
import {
  cardStatusOptions,
  cardTypeOptions,
  confidenceOptions,
  ingestionFlowSteps,
  initialCardForm,
  initialSourceForm,
  parseTokens,
  serializeTokens,
  sourceContentPlaceholder,
  type IngestionProgress,
} from "@/lib/source-panel"
import { cn } from "@/lib/utils"

function IngestionFlowProgress({ progress }: { progress: IngestionProgress }) {
  const activeIndex = ingestionFlowSteps.findIndex((step) => step.id === progress.activeStep)
  const statusLabel =
    progress.status === "running"
      ? "Running"
      : progress.status === "complete"
        ? "Complete"
        : progress.status === "error"
          ? "Error"
          : "Ready"

  return (
    <div className="mb-5 rounded-xl border bg-muted/20 p-4" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold">LangGraph ingestion flow</div>
          <p className="mt-1 break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">{progress.detail}</p>
        </div>
        <Badge variant={progress.status === "error" ? "destructive" : progress.status === "complete" ? "default" : "secondary"}>
          {progress.status === "running" && <Loader2 data-icon="inline-start" className="animate-spin" />}
          {statusLabel}
        </Badge>
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {ingestionFlowSteps.map((step, index) => {
          const isComplete = progress.status === "complete" || index < activeIndex
          const isActive = progress.status === "running" && index === activeIndex
          const isError = progress.status === "error" && index === activeIndex
          const StepIcon = isError ? AlertCircle : isComplete ? CheckCircle2 : isActive ? Loader2 : CircleDot
          return (
            <div
              key={step.id}
              className={cn(
                "min-w-0 rounded-lg border bg-background p-3",
                isComplete && "border-primary/40 bg-primary/5",
                isActive && "border-primary bg-primary/10",
                isError && "border-destructive bg-destructive/10",
              )}
            >
              <div className="flex items-center gap-2">
                <StepIcon className={cn("size-4 shrink-0", isActive && "animate-spin", isError && "text-destructive", isComplete && "text-primary")} />
                <span className="break-words text-sm font-medium [overflow-wrap:anywhere]">{step.label}</span>
              </div>
              <p className="mt-1 break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">{step.description}</p>
            </div>
          )
        })}
      </div>
      <p className="mt-3 break-words text-xs font-medium text-muted-foreground [overflow-wrap:anywhere]">{progress.summary}</p>
    </div>
  )
}

export function SourceConsole({
  sourceForm,
  setSourceForm,
  ingestionProgress,
  onSubmit,
  onUpload,
  fileRef,
  disabled,
}: {
  sourceForm: SourcePayload
  setSourceForm: React.Dispatch<React.SetStateAction<SourcePayload>>
  ingestionProgress: IngestionProgress
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  onUpload: (event: React.FormEvent<HTMLFormElement>) => void
  fileRef: React.RefObject<HTMLInputElement | null>
  disabled: boolean
}) {
  const update = (patch: Partial<SourcePayload>) => setSourceForm((current) => ({ ...current, ...patch }))

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 data-icon="inline-start" />
            Multi-source ingestion
          </CardTitle>
          <CardDescription>직접 입력, Notion, GitHub, Slack, Linear, MCP, Web Link, 그리고 .txt/.md/.pdf/.csv 파일을 같은 저장 파이프라인으로 넣습니다. 내용이 비어 있으면 링크 fetch를 시도합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <IngestionFlowProgress progress={ingestionProgress} />
          <form id="source-ingestion-form" className="flex flex-col gap-5" onSubmit={onSubmit}>
            <FieldSet>
              <FieldGroup>
                <Field>
                  <FieldLabel>Source Type</FieldLabel>
                  <Select value={sourceForm.source_type} onValueChange={(value) => update({ source_type: value ?? "manual" })}>
                    <SelectTrigger className="w-full">
                      <SelectValue>
                        {(value) => sourceTypes.find((source) => source.value === value)?.label ?? value ?? "Manual"}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {sourceTypes.map((source) => (
                          <SelectItem key={source.value} value={source.value}>
                            {source.label}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  <FieldDescription>{sourceTypes.find((source) => source.value === sourceForm.source_type)?.hint}</FieldDescription>
                </Field>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field>
                    <FieldLabel htmlFor="source-url">Source link</FieldLabel>
                    <Input id="source-url" value={sourceForm.source_url} onChange={(event) => update({ source_url: event.target.value })} placeholder="https://github.com/org/repo/blob/main/prd.md" />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="source-external-id">External ID</FieldLabel>
                    <Input id="source-external-id" value={sourceForm.external_id} onChange={(event) => update({ external_id: event.target.value })} placeholder="notion page id or github ref" />
                  </Field>
                </div>
                <Field>
                  <FieldLabel htmlFor="source-title">Stored title</FieldLabel>
                  <Input id="source-title" value={sourceForm.title} onChange={(event) => update({ title: event.target.value })} placeholder="mentor-feedback.md" />
                </Field>
                <Field>
                  <FieldLabel htmlFor="source-content">Pasted connector content</FieldLabel>
                  <Textarea id="source-content" className="min-h-56 max-h-96 [field-sizing:fixed]" value={sourceForm.content} onChange={(event) => update({ content: event.target.value })} placeholder={sourceContentPlaceholder} />
                  <FieldDescription>내용이 비어 있으면 링크에서 자동 fetch를 시도합니다. 인증이 필요한 서비스는 서버 .env 토큰이 없으면 설정 오류를 표시합니다.</FieldDescription>
                </Field>
              </FieldGroup>
            </FieldSet>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={disabled}>
                <FileInput data-icon="inline-start" />
                Save Source
              </Button>
              <Button type="button" variant="outline" onClick={() => setSourceForm(initialSourceForm)}>
                Reset
              </Button>
            </div>
          </form>
          <Separator className="my-5" />
          <form className="flex flex-col gap-3" onSubmit={onUpload}>
            <Field>
              <FieldLabel htmlFor="upload-file">File upload</FieldLabel>
              <Input id="upload-file" ref={fileRef} type="file" accept=".txt,.md,.markdown,.pdf,.csv" />
              <FieldDescription>.txt / .md / .markdown / .pdf (텍스트 기반) / .csv 파일을 원본·source metadata와 함께 저장합니다. 파일 확장자에서 자동으로 document_type을 추론합니다.</FieldDescription>
            </Field>
            <Button type="submit" variant="secondary" disabled={disabled}>
              <Upload data-icon="inline-start" />
              Upload File
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export function ManualCardConsole({
  cardForm,
  setCardForm,
  onSubmit,
  disabled,
}: {
  cardForm: KnowledgeCardPayload
  setCardForm: React.Dispatch<React.SetStateAction<KnowledgeCardPayload>>
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  disabled: boolean
}) {
  const update = (patch: Partial<KnowledgeCardPayload>) => setCardForm((current) => ({ ...current, ...patch }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus data-icon="inline-start" />
          Manual Card
        </CardTitle>
        <CardDescription>회의 중 바로 남길 결정, 가설, 근거 카드를 생성합니다.</CardDescription>
      </CardHeader>
      <CardContent>
        <form id="manual-card-form" className="flex flex-col gap-4" onSubmit={onSubmit}>
          <div className="grid gap-4 md:grid-cols-3">
            <Field>
              <FieldLabel>Card Type</FieldLabel>
              <Select value={cardForm.card_type} onValueChange={(value) => update({ card_type: value ?? "idea" })}>
                <SelectTrigger className="w-full">
                  <SelectValue>{(value) => value ?? "idea"}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {cardTypeOptions.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Status</FieldLabel>
              <Select value={cardForm.status} onValueChange={(value) => update({ status: value ?? "proposed" })}>
                <SelectTrigger className="w-full">
                  <SelectValue>{(value) => value ?? "proposed"}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {cardStatusOptions.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Confidence</FieldLabel>
              <Select value={cardForm.confidence} onValueChange={(value) => update({ confidence: value ?? "medium" })}>
                <SelectTrigger className="w-full">
                  <SelectValue>{(value) => value ?? "medium"}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {confidenceOptions.map((confidence) => (
                      <SelectItem key={confidence} value={confidence}>
                        {confidence}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="manual-card-title">Title</FieldLabel>
            <Input id="manual-card-title" value={cardForm.title} onChange={(event) => update({ title: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor="manual-card-summary">Summary</FieldLabel>
            <Textarea id="manual-card-summary" className="min-h-24" value={cardForm.summary} onChange={(event) => update({ summary: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor="manual-card-evidence">Evidence Quote</FieldLabel>
            <Textarea id="manual-card-evidence" className="min-h-20" value={cardForm.evidence_quote} onChange={(event) => update({ evidence_quote: event.target.value })} />
          </Field>
          <div className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="manual-card-keywords">Keywords</FieldLabel>
              <Input id="manual-card-keywords" value={serializeTokens(cardForm.keywords)} onChange={(event) => update({ keywords: parseTokens(event.target.value) })} placeholder="SQLite, MVP" />
            </Field>
            <Field>
              <FieldLabel htmlFor="manual-card-tags">Tags</FieldLabel>
              <Input id="manual-card-tags" value={serializeTokens(cardForm.tags)} onChange={(event) => update({ tags: parseTokens(event.target.value) })} placeholder="manual, decided" />
            </Field>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={disabled}>
              <Plus data-icon="inline-start" />
              Create Card
            </Button>
            <Button type="button" variant="outline" onClick={() => setCardForm(initialCardForm)}>
              Reset
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
