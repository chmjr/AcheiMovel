"use server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.RADAR_API_TOKEN_WEB ?? "dev-token";

function apiHeaders() {
  return { "X-Radar-Token": API_TOKEN, "Content-Type": "application/json" };
}

export async function triggerScraper(source: string): Promise<{ status: string; source?: string; error?: string }> {
  try {
    const res = await fetch(`${API_URL}/api/v1/scrapers/${source}/trigger`, {
      method: "POST",
      headers: apiHeaders(),
    });
    return res.json();
  } catch (e) {
    return { status: "error", error: String(e) };
  }
}

export async function triggerFullAnalysis(): Promise<{ status: string }> {
  try {
    const res = await fetch(`${API_URL}/api/v1/market/analyze`, {
      method: "POST",
      headers: apiHeaders(),
    });
    return res.json();
  } catch (e) {
    return { status: "error" };
  }
}
