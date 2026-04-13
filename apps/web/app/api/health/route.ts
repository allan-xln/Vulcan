import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    status: "ok",
    phase: "phase-1"
  });
}

