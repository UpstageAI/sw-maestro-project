import { NextResponse } from "next/server";
import { isSolarConfigured } from "@/lib/solar";
import { isAzureImageConfigured } from "@/lib/image-gen";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    ok: true,
    solarConfigured: isSolarConfigured(),
    imageProvider: isAzureImageConfigured() ? "azure" : "mock",
    service: "bossmate",
  });
}
