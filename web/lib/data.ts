import fs from "fs";
import path from "path";
import type { WeekData } from "./types";

const WEEKS_DIR = path.join(process.cwd(), "content", "weeks");

export function loadCurrentWeek(): WeekData | null {
  try {
    const raw = fs.readFileSync(path.join(WEEKS_DIR, "latest.json"), "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function loadWeek(slug: string): WeekData | null {
  try {
    const raw = fs.readFileSync(path.join(WEEKS_DIR, `${slug}.json`), "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function listWeeks(): string[] {
  try {
    return fs
      .readdirSync(WEEKS_DIR)
      .filter((f) => f.match(/^\d{4}-W\d{2}\.json$/))
      .map((f) => f.replace(".json", ""))
      .sort()
      .reverse();
  } catch {
    return [];
  }
}
