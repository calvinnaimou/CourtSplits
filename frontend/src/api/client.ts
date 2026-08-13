import type {
  GameDetail,
  PlayerQueryRequest,
  PlayerSeasonRequest,
  PlayerSeasonResult,
  QueryResult,
  TeamInfo,
  TeamQueryRequest,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export function listPlayers(): Promise<string[]> {
  return request("/players");
}

export function listTeams(): Promise<TeamInfo[]> {
  return request("/teams");
}

export function searchPlayers(q: string): Promise<string[]> {
  return request(`/players/search?q=${encodeURIComponent(q)}`);
}

export function searchTeams(q: string): Promise<TeamInfo[]> {
  return request(`/teams/search?q=${encodeURIComponent(q)}`);
}

export function listPlayerMetrics(): Promise<string[]> {
  return request("/players/metrics");
}

export function listPositions(): Promise<string[]> {
  return request("/players/positions");
}

export function listTeamMetrics(): Promise<string[]> {
  return request("/teams/metrics");
}

export function listTeamPeriods(): Promise<string[]> {
  return request("/teams/periods");
}

export function listTeamRestDays(): Promise<string[]> {
  return request("/teams/rest-days");
}

export function queryPlayer(body: PlayerQueryRequest): Promise<QueryResult> {
  return request("/players/query", { method: "POST", body: JSON.stringify(body) });
}

export function getPlayerSeason(body: PlayerSeasonRequest): Promise<PlayerSeasonResult> {
  return request("/players/season", { method: "POST", body: JSON.stringify(body) });
}

export function queryTeam(body: TeamQueryRequest): Promise<QueryResult> {
  return request("/teams/query", { method: "POST", body: JSON.stringify(body) });
}

export function getGameDetail(gameId: number): Promise<GameDetail> {
  return request(`/games/${gameId}`);
}
