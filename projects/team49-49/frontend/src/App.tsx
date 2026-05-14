import { useEffect, useMemo, useRef, useState } from "react"
import type * as React from "react"
import {
  Bot,
  Boxes,
  BrainCircuit,
  Database,
  FileInput,
  FileSearch,
  GitBranch,
  Inbox,
  Loader2,
  MessageSquareText,
  Network,
  PanelRight,
  Play,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react"

import { KnowledgeGraphPanel } from "@/components/KnowledgeGraphPanel"
import { LangGraphFlowPanel } from "@/components/LangGraphFlowPanel"
import { ObsidianGraphPanel } from "@/components/ObsidianGraphPanel"
import {
  ManualCardConsole,
  SourceConsole,
} from "@/components/SourceTabPanel"
import {
  cardStatusOptions,
  cardTypeOptions,
  initialCardForm,
  initialIngestionProgress,
  initialSourceForm,
  parseTokens,
  serializeTokens,
  serverIngestionStepIds,
  type IngestionProgress,
  type IngestionStepId,
} from "@/lib/source-panel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Field,
  FieldDescription,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  apiFormRequest,
  apiRequest,
  type GraphNode,
  type IngestionResult,
  type KnowledgeCard,
  type KnowledgeCardPatch,
  type KnowledgeCardPayload,
  type KnowledgeGraph,
  type LlmAnswer,
  type RawDocument,
  type RawDocumentPatch,
  type ReviewResult,
  type SearchResponse,
  type SourcePayload,
  type Workspace,
  type WorkflowRegistry,
} from "@/lib/api"
import { sampleSources, sourceTypes } from "@/lib/samples"
import { cn, safeDisplayText } from "@/lib/utils"

type StudioTab = "graph" | "source" | "search" | "workspace"

function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [workspaceId, setWorkspaceId] = useState<number | null>(null)
  const [workspaceName, setWorkspaceName] = useState("SOMA 49 Context Hub")
  const [workspaceDescription, setWorkspaceDescription] = useState("기획 컨텍스트 저장소")
  const [documents, setDocuments] = useState<RawDocument[]>([])
  const [cards, setCards] = useState<KnowledgeCard[]>([])
  const [graph, setGraph] = useState<KnowledgeGraph>({ nodes: [], links: [] })
  const [workflowRegistry, setWorkflowRegistry] = useState<WorkflowRegistry | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<RawDocument | null>(null)
  const [selectedCard, setSelectedCard] = useState<KnowledgeCard | null>(null)
  const [sourceForm, setSourceForm] = useState<SourcePayload>(initialSourceForm)
  const [cardForm, setCardForm] = useState<KnowledgeCardPayload>(initialCardForm)
  const [question, setQuestion] = useState("GraphDB를 제외한 이유와 보완 방법은?")
  const [answer, setAnswer] = useState<LlmAnswer | null>(null)
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
  const [status, setStatus] = useState("Ready")
  const [busy, setBusy] = useState(false)
  const [activeStudioTab, setActiveStudioTab] = useState<StudioTab>("graph")
  const [ingestionProgress, setIngestionProgress] = useState<IngestionProgress>(initialIngestionProgress)
  const fileRef = useRef<HTMLInputElement | null>(null)

  const activeWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null
  const selectedGraphNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? null
  const sourceCounts = useMemo(() => countBy(documents, "source_type"), [documents])
  const cardCounts = useMemo(() => countBy(cards, "card_type"), [cards])
  const needsValidationCount = cards.filter((card) => card.status === "needs_validation" || card.status === "needs_review").length

  useEffect(() => {
    if (ingestionProgress.status !== "running") return
    const timer = window.setTimeout(() => {
      setIngestionProgress((current) => {
        if (current.status !== "running") return current
        const currentIndex = serverIngestionStepIds.findIndex((step) => step === current.activeStep)
        if (currentIndex < 0) return current
        const nextStep = serverIngestionStepIds[Math.min(currentIndex + 1, serverIngestionStepIds.length - 1)]
        return nextStep === current.activeStep ? current : { ...current, activeStep: nextStep }
      })
    }, 900)
    return () => window.clearTimeout(timer)
  }, [ingestionProgress])

  useEffect(() => {
    let mounted = true

    const load = async () => {
      try {
        setBusy(true)
        const existing = await apiRequest<Workspace[]>("/api/workspaces")
        const workspace =
          existing[0] ??
          (await apiRequest<Workspace>("/api/workspaces", {
            method: "POST",
            body: JSON.stringify({
              name: "SOMA 49 Context Hub",
              description: "기획 컨텍스트 저장소",
            }),
          }))
        const [nextWorkspaces, nextDocuments, nextCards, nextGraph, nextWorkflowRegistry] = await Promise.all([
          apiRequest<Workspace[]>("/api/workspaces"),
          apiRequest<RawDocument[]>(`/api/workspaces/${workspace.id}/documents`),
          apiRequest<KnowledgeCard[]>(`/api/workspaces/${workspace.id}/cards`),
          apiRequest<KnowledgeGraph>(`/api/workspaces/${workspace.id}/graph`),
          apiRequest<WorkflowRegistry>("/api/workflows"),
        ])
        if (!mounted) return
        setWorkspaces(nextWorkspaces.length ? nextWorkspaces : existing[0] ? existing : [workspace])
        setWorkspaceId(workspace.id)
        setWorkspaceName(workspace.name)
        setWorkspaceDescription(workspace.description)
        setDocuments(nextDocuments)
        setCards(nextCards)
        setGraph(nextGraph)
        setWorkflowRegistry(nextWorkflowRegistry)
        setStatus("Workspace loaded")
      } catch (error) {
        if (mounted) setStatus(errorMessage(error))
      } finally {
        if (mounted) setBusy(false)
      }
    }

    void load()
    return () => {
      mounted = false
    }
  }, [])

  const refreshWorkspace = async (id = workspaceId) => {
    if (!id) return
    const [nextWorkspaces, nextDocuments, nextCards, nextGraph, nextWorkflowRegistry] = await Promise.all([
      apiRequest<Workspace[]>("/api/workspaces"),
      apiRequest<RawDocument[]>(`/api/workspaces/${id}/documents`),
      apiRequest<KnowledgeCard[]>(`/api/workspaces/${id}/cards`),
      apiRequest<KnowledgeGraph>(`/api/workspaces/${id}/graph`),
      apiRequest<WorkflowRegistry>("/api/workflows"),
    ])
    setWorkspaces(nextWorkspaces)
    const currentWorkspace = nextWorkspaces.find((workspace) => workspace.id === id)
    if (currentWorkspace) {
      setWorkspaceName(currentWorkspace.name)
      setWorkspaceDescription(currentWorkspace.description)
    }
    setDocuments(nextDocuments)
    setCards(nextCards)
    setGraph(nextGraph)
    setWorkflowRegistry(nextWorkflowRegistry)
  }

  const setIngestionStep = (activeStep: IngestionStepId) => {
    setIngestionProgress((current) => ({ ...current, activeStep }))
  }

  const refreshWorkspaceAfterIngestion = async (id: number) => {
    setIngestionStep("refreshWorkspace")
    const nextWorkspaces = await apiRequest<Workspace[]>("/api/workspaces")
    setWorkspaces(nextWorkspaces)
    const currentWorkspace = nextWorkspaces.find((workspace) => workspace.id === id)
    if (currentWorkspace) {
      setWorkspaceName(currentWorkspace.name)
      setWorkspaceDescription(currentWorkspace.description)
    }

    setIngestionStep("refreshDocuments")
    const nextDocuments = await apiRequest<RawDocument[]>(`/api/workspaces/${id}/documents`)
    setDocuments(nextDocuments)

    setIngestionStep("refreshCards")
    const nextCards = await apiRequest<KnowledgeCard[]>(`/api/workspaces/${id}/cards`)
    setCards(nextCards)

    setIngestionStep("refreshGraph")
    const nextGraph = await apiRequest<KnowledgeGraph>(`/api/workspaces/${id}/graph`)
    setGraph(nextGraph)

    setIngestionStep("refreshWorkflows")
    const nextWorkflowRegistry = await apiRequest<WorkflowRegistry>("/api/workflows")
    setWorkflowRegistry(nextWorkflowRegistry)

    setIngestionStep("render")
  }

  const createWorkspace = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTask("Workspace created", async () => {
      const workspace = await apiRequest<Workspace>("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: workspaceName, description: workspaceDescription }),
      })
      setWorkspaceId(workspace.id)
      await refreshWorkspace(workspace.id)
    })
  }

  const updateWorkspace = async () => {
    await runTask("Workspace updated", async () => {
      const id = requireWorkspace()
      await apiRequest<Workspace>(`/api/workspaces/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: workspaceName, description: workspaceDescription }),
      })
      await refreshWorkspace(id)
    })
  }

  const deleteWorkspace = async () => {
    await runTask("Workspace deleted", async () => {
      const id = requireWorkspace()
      await apiRequest<void>(`/api/workspaces/${id}`, { method: "DELETE" })
      const remaining = await apiRequest<Workspace[]>("/api/workspaces")
      const next = remaining[0] ?? (await apiRequest<Workspace>("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: "Demo Workspace", description: "데모 시연용 workspace" }),
      }))
      setWorkspaceId(next.id)
      setWorkspaceName(next.name)
      setWorkspaceDescription(next.description)
      setSelectedNodeId(null)
      setSelectedDocument(null)
      setSelectedCard(null)
      await refreshWorkspace(next.id)
    })
  }

  const createManualCard = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTask("Manual card created", async () => {
      const card = await apiRequest<KnowledgeCard>(`/api/workspaces/${requireWorkspace()}/cards`, {
        method: "POST",
        body: JSON.stringify(cardForm),
      })
      setCardForm(initialCardForm)
      setSelectedNodeId(`card:${card.id}`)
      setSelectedCard(card)
      setSelectedDocument(null)
      await refreshWorkspace()
    })
  }

  const updateCard = async (cardId: number, patch: KnowledgeCardPatch) => {
    await runTask("Card updated", async () => {
      const card = await apiRequest<KnowledgeCard>(`/api/workspaces/${requireWorkspace()}/cards/${cardId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      })
      setSelectedCard(card)
      setSelectedNodeId(`card:${card.id}`)
      setSelectedDocument(null)
      await refreshWorkspace()
    })
  }

  const deleteCard = async (cardId: number) => {
    await runTask("Card deleted", async () => {
      await apiRequest<void>(`/api/workspaces/${requireWorkspace()}/cards/${cardId}`, { method: "DELETE" })
      setSelectedNodeId(null)
      setSelectedCard(null)
      setSelectedDocument(null)
      await refreshWorkspace()
    })
  }

  const ingestSource = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    startIngestionProgress("Source")
    await runTask("Source saved and indexed", async () => {
      const result = await apiRequest<IngestionResult>(
        `/api/workspaces/${requireWorkspace()}/documents/source`,
        {
          method: "POST",
          body: JSON.stringify(sourceForm),
        },
      )
      setSourceForm((current) => ({ ...initialSourceForm, source_type: current.source_type }))
      const id = requireWorkspace()
      setIngestionStep("persist")
      await refreshWorkspaceAfterIngestion(id)
      const summary = summarizeIngestion(result, "Source")
      completeIngestionProgress(summary)
      return summary
    }, { onError: (error) => failIngestionProgress(errorMessage(error)) })
  }

  const uploadFile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) {
      setStatus("업로드할 파일을 선택하세요.")
      return
    }
    startIngestionProgress("File")
    await runTask("File saved and indexed", async () => {
      const formData = new FormData()
      const lowerName = file.name.toLowerCase()
      const sourceType =
        lowerName.endsWith(".md") || lowerName.endsWith(".markdown")
          ? "md"
          : lowerName.endsWith(".pdf")
            ? "pdf"
            : lowerName.endsWith(".csv")
              ? "csv"
              : "txt"
      formData.append("file", file)
      formData.append("source_type", sourceType)
      formData.append("source_url", sourceForm.source_url)
      formData.append("external_id", sourceForm.external_id)
      const result = await apiFormRequest<IngestionResult>(
        `/api/workspaces/${requireWorkspace()}/documents/upload`,
        formData,
      )
      if (fileRef.current) fileRef.current.value = ""
      const id = requireWorkspace()
      setIngestionStep("persist")
      await refreshWorkspaceAfterIngestion(id)
      const summary = summarizeIngestion(result, "File")
      completeIngestionProgress(summary)
      return summary
    }, { onError: (error) => failIngestionProgress(errorMessage(error)) })
  }

  const updateDocument = async (documentId: number, patch: RawDocumentPatch) => {
    await runTask("Source updated and re-indexed", async () => {
      const document = await apiRequest<RawDocument>(`/api/workspaces/${requireWorkspace()}/documents/${documentId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      })
      setSelectedNodeId(`doc:${document.id}`)
      setSelectedDocument(document)
      setSelectedCard(null)
      await refreshWorkspace()
    })
  }

  const deleteDocument = async (documentId: number) => {
    await runTask("Source deleted", async () => {
      await apiRequest<void>(`/api/workspaces/${requireWorkspace()}/documents/${documentId}`, { method: "DELETE" })
      setSelectedNodeId(null)
      setSelectedDocument(null)
      setSelectedCard(null)
      await refreshWorkspace()
    })
  }

  const seedSources = async () => {
    await runTask("Sample workspace reset", async () => {
      const existingWorkspaces = await apiRequest<Workspace[]>("/api/workspaces")
      for (const workspace of existingWorkspaces) {
        await apiRequest<void>(`/api/workspaces/${workspace.id}`, { method: "DELETE" })
      }
      const workspace = await apiRequest<Workspace>("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({
          name: "ICH Demo Workspace",
          description: "GraphDB tradeoff, source intake, relation linking, grounded search 시연용 샘플",
        }),
      })
      for (const sample of sampleSources) {
        await apiRequest(`/api/workspaces/${workspace.id}/documents/source`, {
          method: "POST",
          body: JSON.stringify(sample),
        })
      }
      setWorkspaceId(workspace.id)
      setSelectedNodeId(null)
      setSelectedDocument(null)
      setSelectedCard(null)
      setAnswer(null)
      setSearchResults(null)
      setReviewResult(null)
      await refreshWorkspace(workspace.id)
    })
  }

  const runQualityReview = async () => {
    await runTask("Quality review complete", async () => {
      const result = await apiRequest<ReviewResult>(
        `/api/workspaces/${requireWorkspace()}/reviews/run`,
        { method: "POST" },
      )
      setReviewResult(result)
    })
  }

  const runLlmSearch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTask("Answer generated from stored context", async () => {
      const id = requireWorkspace()
      const [nextSearch, nextAnswer] = await Promise.all([
        apiRequest<SearchResponse>(`/api/workspaces/${id}/search?q=${encodeURIComponent(question)}`),
        apiRequest<LlmAnswer>(`/api/workspaces/${id}/search/llm`, {
          method: "POST",
          body: JSON.stringify({ query: question }),
        }),
      ])
      setSearchResults(nextSearch)
      setAnswer(nextAnswer)
    })
  }

  const selectNode = async (node: GraphNode) => {
    setSelectedNodeId(node.id)
    setSelectedDocument(null)
    setSelectedCard(null)
    if (node.id.startsWith("doc:")) {
      const documentId = Number(node.id.replace("doc:", ""))
      try {
        const document = await apiRequest<RawDocument>(`/api/workspaces/${requireWorkspace()}/documents/${documentId}`)
        setSelectedDocument(document)
      } catch (error) {
        setStatus(errorMessage(error))
      }
    }
    if (node.id.startsWith("card:")) {
      const cardId = Number(node.id.replace("card:", ""))
      setSelectedCard(cards.find((card) => card.id === cardId) ?? null)
    }
  }

  const startIngestionProgress = (kind: "Source" | "File") => {
    setIngestionProgress({
      status: "running",
      activeStep: "validate",
      summary: `${kind} processing started`,
      detail: "LangGraph source intake, chunking, card extraction, relation linking, 저장 갱신을 순서대로 실행합니다.",
    })
  }

  const completeIngestionProgress = (summary: string) => {
    setIngestionProgress({
      status: "complete",
      activeStep: "render",
      summary,
      detail: "처리가 끝났고 workspace 데이터와 그래프가 갱신되었습니다.",
    })
  }

  const failIngestionProgress = (message: string) => {
    setIngestionProgress((current) => ({
      status: "error",
      activeStep: current.activeStep,
      summary: "Source ingestion failed",
      detail: message,
    }))
  }

  const runTask = async (
    successMessage: string,
    task: () => Promise<string | void>,
    options: { onError?: (error: unknown) => void } = {},
  ) => {
    try {
      setBusy(true)
      setStatus("Running")
      const dynamicMessage = await task()
      setStatus(dynamicMessage ?? successMessage)
    } catch (error) {
      options.onError?.(error)
      setStatus(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  const summarizeIngestion = (result: IngestionResult, kind: "Source" | "File"): string => {
    const parts = [
      `${kind} ${result.chunk_count} chunks`,
      `${result.card_count} cards`,
    ]
    if (result.skipped_chunk_count) parts.push(`${result.skipped_chunk_count} skipped`)
    if (result.needs_review_count) parts.push(`${result.needs_review_count} need review`)
    if (result.child_document_ids?.length) parts.push(`${result.child_document_ids.length} child docs`)
    if (result.card_count === 0) parts.push("(no valuable markers detected — chunks stored only)")
    return parts.join(" · ")
  }

  const requireWorkspace = () => {
    if (!workspaceId) throw new Error("Workspace is not ready")
    return workspaceId
  }

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar
          workspaces={workspaces}
          activeWorkspace={activeWorkspace}
          workspaceId={workspaceId}
          onWorkspaceChange={(id) => {
            setWorkspaceId(id)
            void refreshWorkspace(id)
          }}
          activeStudioTab={activeStudioTab}
          onStudioTabChange={setActiveStudioTab}
          documents={documents}
          cards={cards}
          sourceCounts={sourceCounts}
          cardCounts={cardCounts}
        />
        <SidebarInset className="min-h-svh">
          <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-6" />
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-sm font-semibold">Ideation Context Hub</h1>
              <p className="truncate text-xs text-muted-foreground">
                LangGraph Studio식 그래프 검사 흐름으로 저장, 연결, 검색을 조작합니다.
              </p>
            </div>
            <Badge variant={busy ? "secondary" : "outline"} className="hidden sm:inline-flex">
              {busy && <Loader2 data-icon="inline-start" className="animate-spin" />}
              {status}
            </Badge>
            <Button variant="outline" size="sm" onClick={() => void refreshWorkspace()} disabled={!workspaceId || busy}>
              <RefreshCw data-icon="inline-start" />
              Sync
            </Button>
            <Button size="sm" onClick={seedSources} disabled={!workspaceId || busy}>
              <Play data-icon="inline-start" />
              Load Samples
            </Button>
          </header>

          <main
            className={cn(
              "min-h-[calc(100svh-3.5rem)] gap-4 p-4",
              activeStudioTab === "graph"
                ? "grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px]"
                : "flex flex-col",
            )}
          >
            {activeStudioTab === "graph" && (
              <>
                <section className="flex min-w-0 flex-col gap-4">
                  <WorkflowStrip documents={documents.length} cards={cards.length} links={graph.links.length} />
                  <Tabs defaultValue="studio" className="flex w-full flex-col gap-3">
                    <TabsList>
                      <TabsTrigger value="studio">Graph Studio</TabsTrigger>
                      <TabsTrigger value="obsidian">Obsidian Graph</TabsTrigger>
                      <TabsTrigger value="flows">LangGraph Flow</TabsTrigger>
                    </TabsList>
                    <TabsContent value="studio">
                      <KnowledgeGraphPanel
                        graph={graph}
                        selectedId={selectedNodeId}
                        onSelectNode={(node) => void selectNode(node)}
                        onRefresh={() => void refreshWorkspace()}
                      />
                    </TabsContent>
                    <TabsContent value="obsidian">
                      <ObsidianGraphPanel
                        graph={graph}
                        selectedId={selectedNodeId}
                        onSelectNode={(node) => void selectNode(node)}
                        onRefresh={() => void refreshWorkspace()}
                      />
                    </TabsContent>
                    <TabsContent value="flows">
                      <LangGraphFlowPanel
                        registry={workflowRegistry}
                        documents={documents.length}
                        cards={cards.length}
                        links={graph.links.length}
                        hasAnswer={Boolean(answer)}
                        onRefresh={() => void refreshWorkspace()}
                      />
                    </TabsContent>
                  </Tabs>
                </section>

                <InspectorPanel
                  selectedNode={selectedGraphNode}
                  selectedDocument={selectedDocument}
                  selectedCard={selectedCard}
                  answer={answer}
                  documents={documents}
                  needsValidationCount={needsValidationCount}
                  reviewResult={reviewResult}
                  onUpdateDocument={(documentId, patch) => void updateDocument(documentId, patch)}
                  onDeleteDocument={(documentId) => void deleteDocument(documentId)}
                  onUpdateCard={(cardId, patch) => void updateCard(cardId, patch)}
                  onDeleteCard={(cardId) => void deleteCard(cardId)}
                  onRunReview={() => void runQualityReview()}
                  busy={busy || !workspaceId}
                />
              </>
            )}

            {activeStudioTab === "source" && (
              <section className="flex min-w-0 flex-col gap-4">
                <SourceConsole
                  sourceForm={sourceForm}
                  setSourceForm={setSourceForm}
                  ingestionProgress={ingestionProgress}
                  onSubmit={ingestSource}
                  onUpload={uploadFile}
                  fileRef={fileRef}
                  disabled={busy || !workspaceId}
                />
                <ManualCardConsole
                  cardForm={cardForm}
                  setCardForm={setCardForm}
                  onSubmit={createManualCard}
                  disabled={busy || !workspaceId}
                />
              </section>
            )}

            {activeStudioTab === "search" && (
              <section className="flex min-w-0 flex-col gap-4">
                <RetrievalConsole
                  question={question}
                  setQuestion={setQuestion}
                  answer={answer}
                  searchResults={searchResults}
                  onSubmit={runLlmSearch}
                  disabled={busy || !workspaceId}
                />
              </section>
            )}

            {activeStudioTab === "workspace" && (
              <WorkspaceConsole
                workspaces={workspaces}
                activeWorkspace={activeWorkspace}
                workspaceId={workspaceId}
                onWorkspaceChange={(id) => {
                  setWorkspaceId(id)
                  void refreshWorkspace(id)
                }}
                onCreateWorkspace={createWorkspace}
                onUpdateWorkspace={() => void updateWorkspace()}
                onDeleteWorkspace={() => void deleteWorkspace()}
                busy={busy}
                workspaceName={workspaceName}
                setWorkspaceName={setWorkspaceName}
                workspaceDescription={workspaceDescription}
                setWorkspaceDescription={setWorkspaceDescription}
              />
            )}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}

function AppSidebar({
  workspaces,
  activeWorkspace,
  workspaceId,
  onWorkspaceChange,
  activeStudioTab,
  onStudioTabChange,
  documents,
  cards,
  sourceCounts,
  cardCounts,
}: {
  workspaces: Workspace[]
  activeWorkspace: Workspace | null
  workspaceId: number | null
  onWorkspaceChange: (id: number) => void
  activeStudioTab: StudioTab
  onStudioTabChange: (tab: StudioTab) => void
  documents: RawDocument[]
  cards: KnowledgeCard[]
  sourceCounts: Record<string, number>
  cardCounts: Record<string, number>
}) {
  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 rounded-lg border bg-background p-2">
          <div className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrainCircuit />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">Context Hub</div>
            <div className="truncate text-xs text-muted-foreground">{safeDisplayText(activeWorkspace?.name) || "No workspace"}</div>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {workspaces.map((workspace) => (
                <SidebarMenuItem key={workspace.id}>
                  <SidebarMenuButton isActive={workspace.id === workspaceId} onClick={() => onWorkspaceChange(workspace.id)}>
                    <Database />
                    <span>{safeDisplayText(workspace.name)}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarSeparator />
        <SidebarGroup>
          <SidebarGroupLabel>Studio</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeStudioTab === "graph"} onClick={() => onStudioTabChange("graph")}>
                  <Network />
                  <span>Graph</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeStudioTab === "source"} onClick={() => onStudioTabChange("source")}>
                  <Inbox />
                  <span>Source</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeStudioTab === "search"} onClick={() => onStudioTabChange("search")}>
                  <FileSearch />
                  <span>Search</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeStudioTab === "workspace"} onClick={() => onStudioTabChange("workspace")}>
                  <Database />
                  <span>Workspace</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarSeparator />
        <SidebarGroup>
          <SidebarGroupLabel>Source Mix</SidebarGroupLabel>
          <SidebarGroupContent className="flex flex-col gap-2 px-2">
            {Object.entries(sourceCounts).length ? (
              Object.entries(sourceCounts).map(([type, count]) => <MetricRow key={type} label={type} value={count} />)
            ) : (
              <p className="text-xs text-muted-foreground">아직 저장된 소스가 없습니다.</p>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Card Types</SidebarGroupLabel>
          <SidebarGroupContent className="flex flex-col gap-2 px-2">
            {Object.entries(cardCounts).slice(0, 7).map(([type, count]) => (
              <MetricRow key={type} label={type} value={count} />
            ))}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="rounded-lg border bg-background p-2 text-xs text-muted-foreground">
          {documents.length} documents · {cards.length} cards
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}

function WorkflowStrip({ documents, cards, links }: { documents: number; cards: number; links: number }) {
  const steps = [
    { label: "Source Intake", value: documents, icon: FileInput },
    { label: "Chunk & Filter", value: documents, icon: Boxes },
    { label: "Knowledge Cards", value: cards, icon: Sparkles },
    { label: "Graph Links", value: links, icon: GitBranch },
    { label: "Grounded Answer", value: "RAG", icon: Bot },
  ]

  return (
    <div className="workflow-strip" aria-label="Workflow status">
      {steps.map((step, index) => {
        const Icon = step.icon
        return (
          <Card key={step.label} size="sm" className="workflow-step-card">
            <CardContent className="workflow-node">
              <div className="flex items-center justify-between gap-2">
                <Icon />
                <Badge variant="secondary">{step.value}</Badge>
              </div>
              <div>
                <div className="text-sm font-medium">{step.label}</div>
                <p className="text-xs text-muted-foreground">node {index + 1}</p>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function RetrievalConsole({
  question,
  setQuestion,
  answer,
  searchResults,
  onSubmit,
  disabled,
}: {
  question: string
  setQuestion: (value: string) => void
  answer: LlmAnswer | null
  searchResults: SearchResponse | null
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  disabled: boolean
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareText data-icon="inline-start" />
            Grounded LLM Search
          </CardTitle>
          <CardDescription>LLM API는 저장된 카드와 원문 chunk만 받아 답변합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <form id="llm-search-form" className="flex flex-col gap-3" onSubmit={onSubmit}>
            <Field>
              <FieldLabel htmlFor="llm-search-query">Question</FieldLabel>
              <Textarea id="llm-search-query" className="min-h-28" value={question} onChange={(event) => setQuestion(event.target.value)} />
            </Field>
            <Button type="submit" disabled={disabled}>
              <Search data-icon="inline-start" />
              Search with LLM
            </Button>
          </form>
          <div id="llm-search-output" className="mt-5">
            {answer ? <AnswerBlock answer={answer} /> : <p className="text-sm text-muted-foreground">질문을 실행하면 근거 카드와 원문 인용이 표시됩니다.</p>}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Retrieved Context</CardTitle>
          <CardDescription>카드와 chunk 검색 결과를 분리해서 확인합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[360px] pr-3">
            <div className="flex flex-col gap-3">
              {searchResults?.cards.map((card) => (
                <div key={card.id} className="min-w-0 rounded-lg border p-3">
                  <div className="break-words text-sm font-medium [overflow-wrap:anywhere]">#{card.id} {safeDisplayText(card.title)}</div>
                  <p className="mt-1 whitespace-pre-wrap break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">{card.summary}</p>
                </div>
              ))}
              {searchResults?.chunks.map((chunk) => (
                <div key={chunk.id} className="min-w-0 rounded-lg border border-dashed p-3">
                  <div className="text-xs font-medium">chunk #{chunk.id}</div>
                  <p className="mt-1 whitespace-pre-wrap break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">{chunk.content}</p>
                </div>
              ))}
              {!searchResults && (
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <Search />
                    </EmptyMedia>
                    <EmptyTitle>No search run</EmptyTitle>
                    <EmptyDescription>질문 실행 후 검색된 컨텍스트를 확인합니다.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

function WorkspaceConsole({
  workspaces,
  activeWorkspace,
  workspaceId,
  onWorkspaceChange,
  onCreateWorkspace,
  onUpdateWorkspace,
  onDeleteWorkspace,
  busy,
  workspaceName,
  setWorkspaceName,
  workspaceDescription,
  setWorkspaceDescription,
}: {
  workspaces: Workspace[]
  activeWorkspace: Workspace | null
  workspaceId: number | null
  onWorkspaceChange: (id: number) => void
  onCreateWorkspace: (event: React.FormEvent<HTMLFormElement>) => void
  onUpdateWorkspace: () => void
  onDeleteWorkspace: () => void
  busy: boolean
  workspaceName: string
  setWorkspaceName: (value: string) => void
  workspaceDescription: string
  setWorkspaceDescription: (value: string) => void
}) {
  return (
    <section className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database data-icon="inline-start" />
            Workspace
          </CardTitle>
          <CardDescription>작업 공간 생성, 이름 수정, 삭제를 이 탭에서 관리합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={onCreateWorkspace}>
            <Field>
              <FieldLabel htmlFor="workspace-name">Workspace name</FieldLabel>
              <Input id="workspace-name" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} />
            </Field>
            <Field>
              <FieldLabel htmlFor="workspace-description">Description</FieldLabel>
              <Input id="workspace-description" value={workspaceDescription} onChange={(event) => setWorkspaceDescription(event.target.value)} />
            </Field>
            <Button type="submit" disabled={busy}>
              <Database data-icon="inline-start" />
              Create workspace
            </Button>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={onUpdateWorkspace} disabled={busy || !workspaceId}>
                <Save data-icon="inline-start" />
                Save workspace
              </Button>
              <Button type="button" variant="destructive" onClick={onDeleteWorkspace} disabled={busy || !workspaceId}>
                <Trash2 data-icon="inline-start" />
                Delete
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Workspace List</CardTitle>
          <CardDescription>{activeWorkspace ? `${safeDisplayText(activeWorkspace.name)} is selected` : "선택된 workspace가 없습니다."}</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="max-h-[420px] pr-3">
            <div className="flex flex-col gap-2">
              {workspaces.map((workspace) => (
                <button
                  key={workspace.id}
                  type="button"
                  className={cn(
                    "flex min-w-0 flex-col gap-1 rounded-lg border p-3 text-left transition hover:bg-muted/60",
                    workspace.id === workspaceId && "border-primary bg-muted/60",
                  )}
                  onClick={() => onWorkspaceChange(workspace.id)}
                >
                  <span className="break-words text-sm font-medium [overflow-wrap:anywhere]">{safeDisplayText(workspace.name)}</span>
                  <span className="break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">
                    {safeDisplayText(workspace.description) || "No description"}
                  </span>
                </button>
              ))}
              {!workspaces.length && (
                <Empty className="border">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <Database />
                    </EmptyMedia>
                    <EmptyTitle>No workspace</EmptyTitle>
                    <EmptyDescription>이름을 입력해 새 workspace를 생성합니다.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </section>
  )
}

function InspectorPanel({
  selectedNode,
  selectedDocument,
  selectedCard,
  answer,
  documents,
  needsValidationCount,
  reviewResult,
  onUpdateDocument,
  onDeleteDocument,
  onUpdateCard,
  onDeleteCard,
  onRunReview,
  busy,
}: {
  selectedNode: GraphNode | null
  selectedDocument: RawDocument | null
  selectedCard: KnowledgeCard | null
  answer: LlmAnswer | null
  documents: RawDocument[]
  needsValidationCount: number
  reviewResult: ReviewResult | null
  onUpdateDocument: (documentId: number, patch: RawDocumentPatch) => void
  onDeleteDocument: (documentId: number) => void
  onUpdateCard: (cardId: number, patch: KnowledgeCardPatch) => void
  onDeleteCard: (cardId: number) => void
  onRunReview: () => void
  busy: boolean
}) {
  return (
    <aside className="flex min-w-0 flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PanelRight data-icon="inline-start" />
            Inspector
          </CardTitle>
          <CardDescription>선택된 노드의 원문, 카드 상태, 최근 답변 근거를 봅니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="node" className="flex w-full flex-col gap-3">
            <TabsList>
              <TabsTrigger value="node">Node</TabsTrigger>
              <TabsTrigger value="answer">Answer</TabsTrigger>
            </TabsList>
            <TabsContent value="node" className="mt-4">
              <NodeInspector
                node={selectedNode}
                document={selectedDocument}
                card={selectedCard}
                documents={documents}
                onUpdateDocument={onUpdateDocument}
                onDeleteDocument={onDeleteDocument}
                onUpdateCard={onUpdateCard}
                onDeleteCard={onDeleteCard}
                busy={busy}
              />
            </TabsContent>
            <TabsContent value="answer" className="mt-4">
              {answer ? <AnswerBlock answer={answer} compact /> : <p className="text-sm text-muted-foreground">아직 생성된 답변이 없습니다.</p>}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck data-icon="inline-start" />
            Quality Signals
          </CardTitle>
          <CardDescription>저장 품질과 검색 신뢰도 점검용 상태입니다.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <SignalRow label="Needs validation" value={needsValidationCount} />
          <SignalRow label="Sources with links" value={documents.filter((document) => document.source_url).length} />
          <SignalRow label="Pasted sources" value={documents.filter((document) => document.content.length > 0).length} />
          <Button variant="outline" size="sm" onClick={onRunReview} disabled={busy} className="mt-1">
            <ShieldCheck data-icon="inline-start" />
            Run Quality Review
          </Button>
          {reviewResult && (
            <div className="flex flex-col gap-2 mt-1 min-w-0">
              <p className="text-xs text-muted-foreground">{reviewResult.quality_summary}</p>
              <ScrollArea className="max-h-72">
                <div className="flex flex-col gap-2 pr-2">
                  {reviewResult.review_targets.map((target) => (
                    <div key={target.card_id} className="rounded-lg border p-2 text-xs min-w-0">
                      <div className="flex items-center gap-1.5 mb-1 min-w-0">
                        <Badge variant="secondary" className="shrink-0">{target.card_type}</Badge>
                        <span className="break-words font-medium [overflow-wrap:anywhere]">{safeDisplayText(target.title)}</span>
                      </div>
                      <p className="break-words text-destructive [overflow-wrap:anywhere]">⚠ {target.issue}</p>
                      <p className="break-words text-muted-foreground [overflow-wrap:anywhere]">→ {target.suggestion}</p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}
        </CardContent>
      </Card>
    </aside>
  )
}

function NodeInspector({
  node,
  document,
  card,
  documents,
  onUpdateDocument,
  onDeleteDocument,
  onUpdateCard,
  onDeleteCard,
  busy,
}: {
  node: GraphNode | null
  document: RawDocument | null
  card: KnowledgeCard | null
  documents: RawDocument[]
  onUpdateDocument: (documentId: number, patch: RawDocumentPatch) => void
  onDeleteDocument: (documentId: number) => void
  onUpdateCard: (cardId: number, patch: KnowledgeCardPatch) => void
  onDeleteCard: (cardId: number) => void
  busy: boolean
}) {
  const [draft, setDraft] = useState<KnowledgeCardPayload>(initialCardForm)
  const [documentDraft, setDocumentDraft] = useState<RawDocumentPatch>({})

  useEffect(() => {
    if (!card) {
      setDraft(initialCardForm)
      return
    }
    setDraft({
      card_type: card.card_type,
      title: card.title,
      summary: card.summary,
      evidence_quote: card.evidence_quote,
      keywords: card.keywords,
      tags: card.tags,
      status: card.status,
      confidence: card.confidence,
    })
  }, [card])

  useEffect(() => {
    if (!document) {
      setDocumentDraft({})
      return
    }
    setDocumentDraft({
      filename: document.filename,
      source_type: document.source_type,
      source_url: document.source_url,
      external_id: document.external_id,
      content: document.content,
    })
  }, [document])

  const updateDraft = (patch: Partial<KnowledgeCardPayload>) => setDraft((current) => ({ ...current, ...patch }))
  const updateDocumentDraft = (patch: RawDocumentPatch) => setDocumentDraft((current) => ({ ...current, ...patch }))

  if (!node) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Network />
          </EmptyMedia>
          <EmptyTitle>Select a graph node</EmptyTitle>
          <EmptyDescription>문서나 카드를 클릭하면 상세 내용이 열립니다.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  if (document) {
    return (
      <div className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge>{document.source_type}</Badge>
          <Badge variant="outline">{document.document_type}</Badge>
        </div>
        <div className="min-w-0">
          <div className="break-words text-sm font-medium [overflow-wrap:anywhere]">{safeDisplayText(document.filename)}</div>
          <p className="break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">{document.source_url || "local input"}</p>
        </div>
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            onUpdateDocument(document.id, documentDraft)
          }}
        >
          <Field>
            <FieldLabel htmlFor={`document-filename-${document.id}`}>Stored title</FieldLabel>
            <Input
              id={`document-filename-${document.id}`}
              value={documentDraft.filename ?? ""}
              onChange={(event) => updateDocumentDraft({ filename: event.target.value })}
            />
          </Field>
          <Field>
            <FieldLabel>Source Type</FieldLabel>
            <Select value={documentDraft.source_type ?? document.source_type} onValueChange={(value) => updateDocumentDraft({ source_type: value ?? document.source_type })}>
              <SelectTrigger className="w-full">
                <SelectValue>
                  {(value) => sourceTypes.find((source) => source.value === value)?.label ?? value ?? document.source_type}
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
          </Field>
          <Field>
            <FieldLabel htmlFor={`document-url-${document.id}`}>Source link</FieldLabel>
            <Input
              id={`document-url-${document.id}`}
              value={documentDraft.source_url ?? ""}
              onChange={(event) => updateDocumentDraft({ source_url: event.target.value })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor={`document-external-${document.id}`}>External ID</FieldLabel>
            <Input
              id={`document-external-${document.id}`}
              value={documentDraft.external_id ?? ""}
              onChange={(event) => updateDocumentDraft({ external_id: event.target.value })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor={`document-content-${document.id}`}>Source Markdown</FieldLabel>
            <Textarea
              id={`document-content-${document.id}`}
              className="min-h-72 whitespace-pre-wrap text-xs leading-relaxed"
              value={documentDraft.content ?? ""}
              onChange={(event) => updateDocumentDraft({ content: event.target.value })}
            />
            <FieldDescription>원문을 수정하면 chunk와 Knowledge Card를 다시 추출합니다.</FieldDescription>
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={busy}>
              <Save data-icon="inline-start" />
              Save Source
            </Button>
            <Button type="button" size="sm" variant="destructive" onClick={() => onDeleteDocument(document.id)} disabled={busy}>
              <Trash2 data-icon="inline-start" />
              Delete Source
            </Button>
          </div>
        </form>
      </div>
    )
  }

  if (card) {
    const source = documents.find((documentItem) => documentItem.id === card.source_document_id)
    return (
      <div className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge>{card.card_type}</Badge>
          <Badge variant="outline">{card.status}</Badge>
          <Badge variant={card.confidence === "high" ? "default" : "secondary"}>{card.confidence}</Badge>
        </div>
        <div className="min-w-0">
          <div className="break-words text-sm font-medium [overflow-wrap:anywhere]">{safeDisplayText(card.title)}</div>
          <p className="break-words text-xs text-muted-foreground [overflow-wrap:anywhere]">{safeDisplayText(source?.filename) || "unknown source"}</p>
        </div>
        <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground [overflow-wrap:anywhere]">{card.summary}</p>
        <div className="whitespace-pre-wrap break-words rounded-lg border bg-muted/30 p-3 text-sm [overflow-wrap:anywhere]">"{card.evidence_quote}"</div>
        <div className="flex flex-wrap gap-1.5">
          {card.keywords.map((keyword) => (
            <Badge key={keyword} variant="secondary" className="h-auto min-h-5 max-w-full whitespace-normal text-left break-words [overflow-wrap:anywhere]">{keyword}</Badge>
          ))}
        </div>
        <Separator />
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            onUpdateCard(card.id, draft)
          }}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Field>
              <FieldLabel>Type</FieldLabel>
              <Select value={draft.card_type} onValueChange={(value) => updateDraft({ card_type: value ?? card.card_type })}>
                <SelectTrigger className="w-full">
                  <SelectValue>{(value) => value ?? draft.card_type}</SelectValue>
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
              <Select value={draft.status} onValueChange={(value) => updateDraft({ status: value ?? card.status })}>
                <SelectTrigger className="w-full">
                  <SelectValue>{(value) => value ?? draft.status}</SelectValue>
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
          </div>
          <Field>
            <FieldLabel htmlFor={`card-title-${card.id}`}>Title</FieldLabel>
            <Input id={`card-title-${card.id}`} value={draft.title} onChange={(event) => updateDraft({ title: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`card-summary-${card.id}`}>Summary</FieldLabel>
            <Textarea id={`card-summary-${card.id}`} className="min-h-24" value={draft.summary} onChange={(event) => updateDraft({ summary: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`card-evidence-${card.id}`}>Evidence Quote</FieldLabel>
            <Textarea id={`card-evidence-${card.id}`} className="min-h-20" value={draft.evidence_quote} onChange={(event) => updateDraft({ evidence_quote: event.target.value })} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor={`card-keywords-${card.id}`}>Keywords</FieldLabel>
              <Input id={`card-keywords-${card.id}`} value={serializeTokens(draft.keywords)} onChange={(event) => updateDraft({ keywords: parseTokens(event.target.value) })} />
            </Field>
            <Field>
              <FieldLabel htmlFor={`card-tags-${card.id}`}>Tags</FieldLabel>
              <Input id={`card-tags-${card.id}`} value={serializeTokens(draft.tags)} onChange={(event) => updateDraft({ tags: parseTokens(event.target.value) })} />
            </Field>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={busy}>
              <Save data-icon="inline-start" />
              Save Card
            </Button>
            <Button type="button" size="sm" variant="destructive" onClick={() => onDeleteCard(card.id)} disabled={busy}>
              <Trash2 data-icon="inline-start" />
              Delete
            </Button>
          </div>
        </form>
      </div>
    )
  }

  return <p className="text-sm text-muted-foreground">{node.label}</p>
}

function AnswerBlock({ answer, compact = false }: { answer: LlmAnswer; compact?: boolean }) {
  return (
    <div className={cn("flex flex-col gap-4 rounded-xl border bg-muted/20 p-4", compact && "p-3")}>
      <div>
        <Badge variant={answer.confidence === "high" ? "default" : "secondary"}>{answer.confidence}</Badge>
        <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed [overflow-wrap:anywhere]">{answer.answer}</p>
      </div>
      <div className="flex flex-col gap-2">
        <div className="text-xs font-medium uppercase text-muted-foreground">Evidence Cards</div>
        {answer.evidence_cards.length ? (
          answer.evidence_cards.map((card) => (
            <div key={card.card_id} className="min-w-0 rounded-lg border bg-background p-3 text-xs">
              <div className="break-words font-medium [overflow-wrap:anywhere]">card #{card.card_id} · {safeDisplayText(card.title)}</div>
              <div className="mt-1 break-words text-muted-foreground [overflow-wrap:anywhere]">{safeDisplayText(card.source_document)}</div>
              <p className="mt-2 whitespace-pre-wrap break-words leading-relaxed [overflow-wrap:anywhere]">"{card.evidence_quote}"</p>
            </div>
          ))
        ) : (
          <p className="text-xs text-muted-foreground">근거 카드가 없습니다.</p>
        )}
      </div>
      {answer.relation_evidence.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-medium uppercase text-muted-foreground">Relation Evidence</div>
          {answer.relation_evidence.map((rel) => (
            <div key={rel.relation_id} className="min-w-0 rounded-lg border bg-background p-3 text-xs">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-medium">card #{rel.source_card_id}</span>
                <Badge variant="secondary">{rel.relation_type}</Badge>
                <span className="font-medium">card #{rel.target_card_id}</span>
                <Badge variant={rel.confidence === "high" ? "default" : "secondary"}>{rel.confidence}</Badge>
              </div>
              {rel.reason && <p className="mt-2 whitespace-pre-wrap break-words text-muted-foreground [overflow-wrap:anywhere]">{rel.reason}</p>}
            </div>
          ))}
        </div>
      )}
      {answer.evidence_chunks.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-medium uppercase text-muted-foreground">Source Chunks</div>
          {answer.evidence_chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="min-w-0 rounded-lg border border-dashed bg-background p-3 text-xs">
              <div className="break-words font-medium text-muted-foreground [overflow-wrap:anywhere]">{safeDisplayText(chunk.source_document)}</div>
              <p className="mt-2 whitespace-pre-wrap break-words leading-relaxed [overflow-wrap:anywhere]">"{chunk.quote}"</p>
            </div>
          ))}
        </div>
      )}
      {answer.missing_evidence.length > 0 && (
        <div className="whitespace-pre-wrap break-words rounded-lg border border-dashed p-3 text-xs text-muted-foreground [overflow-wrap:anywhere]">
          {answer.missing_evidence.join(" ")}
        </div>
      )}
    </div>
  )
}

function MetricRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="truncate text-muted-foreground">{label}</span>
      <Badge variant="secondary">{value}</Badge>
    </div>
  )
}

function SignalRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  )
}

function countBy<T extends Record<string, unknown>>(items: T[], key: keyof T): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const value = String(item[key] || "unknown")
    counts[value] = (counts[value] ?? 0) + 1
    return counts
  }, {})
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default App
