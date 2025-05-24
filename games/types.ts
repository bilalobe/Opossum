export enum CellType {
  Empty = '_',
  Opossum = 'O', // Player Opossum (O₁)
  Food = 'F',
  Obstacle = '#',
  Exit = 'E',
  Threat = 'T',
  Opossum2 = 'P2', // NPC Opossum (O₂)
}

export enum TrailType {
  REGULAR = 'REGULAR',
  FOOD_SCENT = 'FOOD_SCENT',
  STRESS_SCENT = 'STRESS_SCENT',
}

export interface Trail {
  type: TrailType;
  intensity: number; // e.g., 1 (faint) to 3 (strong)
  source: 'player' | 'npc';
  decayIn: number; // Turns left until it disappears
}

export interface GridCell {
  type: CellType;
  id: string; // For key prop in React
  trail?: Trail;
  foodQuality?: number; // For CellType.Food, 0-100
}

export type Grid = GridCell[][];

export interface OpossumState {
  hunger: number; // 0-10 (0 full, 10 starving)
  fear: number;   // 0-10 (0 calm, 10 terrified)
  energy: number; // 0-10 (0 exhausted, 10 energetic)
  memory: string;
}

export interface OpossumPosition {
  x: number;
  y: number;
}

export interface LLMAction {
  action: string; // e.g., MOVE_NORTH, EAT, HISS
  reason: string;
}

export interface GroundingChunk {
  web?: {
    uri: string;
    title: string;
  };
  retrievedContext?: {
    uri: string;
    title: string;
  };
}