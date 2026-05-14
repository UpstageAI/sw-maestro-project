import { NextResponse } from "next/server";
import { promotionGraph } from "@/lib/agent/graph";

export function GET() {
  const mermaid = promotionGraph.getGraph().drawMermaid();
  return NextResponse.json({ mermaid });
}
