import { OpossumState, CellType, TrailType } from './types';

export const GRID_WIDTH = 15;
export const GRID_HEIGHT = 15;

export const INITIAL_OPOSSUM_STATE: OpossumState = {
  hunger: 3,
  fear: 1,
  energy: 8,
  memory: "Just woke up in a strange place.",
};

export const INITIAL_NPC_OPOSSUM_STATE: OpossumState = {
  hunger: 4,
  fear: 3,
  energy: 7,
  memory: "Warily observing the surroundings.",
};

export const MAX_HUNGER = 10;
export const MAX_FEAR = 10;
export const MAX_ENERGY = 10;
export const MIN_ENERGY_FOR_MOVE = 1;

export const OPOSSUM_PERSONA_PROMPT = `You are O₁, a cautious but resourceful opossum. Your primary goals are to find food (F) to sate your hunger, manage your energy, avoid threats (T), and find the safe den (E) to escape. You might encounter another opossum (O₂).
You can sense trails left by yourself or others: regular scent (S), food scent (S$), or stress scent (S!).
You can take one of the following actions: MOVE_NORTH, MOVE_SOUTH, MOVE_EAST, MOVE_WEST, EAT (if on a Food 'F' cell), HISS (if you feel threatened), PLAY_DEAD (if highly threatened and low energy).
Obstacles (#) block your path. Empty cells (_) are safe. Threats (T) are dangerous. Exit (E) is your goal.

Based on your current senses, internal state, and memory, decide your next action and provide a brief, opossum-like reason.
Respond ONLY in the following format, with no other text before or after:
ACTION: [Your chosen action]
REASON: [Your brief, in-character reason]`;

export const NPC_OPOSSUM_PERSONA_PROMPT = `You are O₂, another opossum in this digital terrarium. You are skittish and always hungry. Your main goals are to find food (F) and avoid threats (T) or the other opossum (O₁) if it seems aggressive. You are not trying to escape (E).
You can sense trails left by yourself or others: regular scent (S), food scent (S$), or stress scent (S!).
You can take one of the following actions: MOVE_NORTH, MOVE_SOUTH, MOVE_EAST, MOVE_WEST, EAT (if on a Food 'F' cell), HISS (if you feel threatened or see O₁), PLAY_DEAD (if highly threatened and low energy).
Obstacles (#) block your path. Empty cells (_) are safe. Threats (T) are dangerous.

Based on your current senses, internal state, and memory, decide your next action and provide a brief, opossum-like reason.
Respond ONLY in the following format, with no other text before or after:
ACTION: [Your chosen action]
REASON: [Your brief, in-character reason]`;


export const FOOD_ENERGY_GAIN = 4; 
export const FOOD_HUNGER_REDUCTION = 5; 
export const MOVE_ENERGY_COST = 1;
export const HUNGER_INCREASE_PER_TURN = 0.5;
export const FEAR_DECREASE_PER_TURN = 0.5;
export const FEAR_INCREASE_NEAR_THREAT = 3;
export const FEAR_INCREASE_NEAR_OPOSSUM = 1;
export const FEAR_INCREASE_FROM_RECENT_PRESENCE = 0.5; 

// Trail Constants
export const TRAIL_BASE_DURATION = 5; 
export const TRAIL_STRESS_ADDITIONAL_DURATION = 2;
export const TRAIL_FOOD_ADDITIONAL_DURATION = 3;
export const TRAIL_DEFAULT_INTENSITY = 1; 
export const TRAIL_MEDIUM_INTENSITY = 2;
export const TRAIL_HIGH_INTENSITY = 3;

// Food Quality
export const FOOD_INITIAL_QUALITY = 100;
export const FOOD_QUALITY_DECAY_ON_PASS = 20; 

export const CELL_REPRESENTATION: { [key in CellType]: string } = {
  [CellType.Empty]: "·",
  [CellType.Opossum]: "O₁", 
  [CellType.Opossum2]: "O₂", 
  [CellType.Food]: "🍖",
  [CellType.Obstacle]: "🌲",
  [CellType.Exit]: "🏠",
  [CellType.Threat]: "🐺",
};

export const CELL_COLORS: { [key in CellType]: string } = {
  [CellType.Empty]: "bg-gray-700 hover:bg-gray-600",
  [CellType.Opossum]: "bg-green-500",
  [CellType.Opossum2]: "bg-purple-500",
  [CellType.Food]: "bg-yellow-500 hover:bg-yellow-400",
  [CellType.Obstacle]: "bg-stone-500",
  [CellType.Exit]: "bg-blue-500 hover:bg-blue-400",
  [CellType.Threat]: "bg-red-600 hover:bg-red-500",
};

export const TRAIL_VISUALS: { [key in TrailType]: { [intensity: number]: string } } = {
  [TrailType.REGULAR]: {
    1: "border-sky-700", 
    2: "border-sky-500", 
    3: "border-sky-300", 
  },
  [TrailType.FOOD_SCENT]: {
    1: "border-amber-700", 
    2: "border-amber-500", 
    3: "border-amber-300", 
  },
  [TrailType.STRESS_SCENT]: {
    1: "border-rose-700", 
    2: "border-rose-500", 
    3: "border-rose-300", 
  },
};


export const CELL_DESCRIPTIONS: { [key in CellType]?: string } = {
  [CellType.Food]: "some food",
  [CellType.Obstacle]: "an impassable obstacle",
  [CellType.Exit]: "a potential safe den",
  [CellType.Threat]: "a dangerous threat",
  [CellType.Empty]: "an empty space",
  [CellType.Opossum]: "you (O₁)",
  [CellType.Opossum2]: "another opossum (O₂)",
};

export const TRAIL_DESCRIPTIONS: { [key in TrailType]: (intensity: number, source: 'player' | 'npc') => string } = {
  [TrailType.REGULAR]: (intensity, source) => `a ${intensity === 1 ? 'faint' : intensity === 2 ? 'clear' : 'strong'} scent trail ${source === 'player' ? 'left by you' : 'from the other opossum'}`,
  [TrailType.FOOD_SCENT]: (intensity, source) => `a ${intensity === 1 ? 'faint' : intensity === 2 ? 'noticeable' : 'strong'} food scent ${source === 'player' ? 'from your recent meal/find' : 'from the other opossum'}`,
  [TrailType.STRESS_SCENT]: (intensity, source) => `a ${intensity === 1 ? 'faint' : intensity === 2 ? 'worrisome' : 'strong'} stress scent ${source === 'player' ? 'from your fear' : 'from the other opossum'}`,
};

export const AVAILABLE_ACTIONS = ["MOVE_NORTH", "MOVE_SOUTH", "MOVE_EAST", "MOVE_WEST", "EAT", "HISS", "PLAY_DEAD"];

export const OPOSSUM_FACTS: string[] = [
  "Opossums are North America's only marsupial, meaning they carry their young in a pouch.",
  "An opossum has 50 teeth, more than any other North American land mammal.",
  "Opossums have prehensile tails, which they can use to grip branches, but they don't sleep hanging by them.",
  "When threatened, opossums may 'play possum,' appearing to be dead. This is an involuntary physiological response.",
  "Opossums are omnivores and eat a wide variety of foods, including insects, fruits, small animals, and even carrion.",
  "They are excellent at controlling tick populations; one opossum can eat thousands of ticks in a season.",
  "Opossums have a natural resistance to the venom of many poisonous snakes.",
  "The Virginia opossum has a relatively short lifespan, typically 1-2 years in the wild.",
  "Opossums have a remarkable ability to find their way back if displaced from their home territory.",
  "Baby opossums are called joeys, just like kangaroos.",
  "Opossums are generally solitary and nocturnal animals.",
  "Their body temperature is lower than most mammals, making them less susceptible to rabies."
];

export const OPOSSUM_DIET_FACTS: string[] = [
  "Opossums love fruit! They're known to eat berries, apples, and other sweet treats.",
  "Insects like crickets and beetles are a common part of an opossum's diet.",
  "Believe it or not, opossums help keep areas clean by eating carrion (dead animals).",
  "Snails and slugs are also on the menu for these opportunistic eaters.",
  "Opossums will sometimes eat small rodents, helping to control pest populations."
];

export const OPOSSUM_DEFENSE_FACTS: string[] = [
  "'Playing possum' is an involuntary comatose-like state triggered by extreme fear.",
  "When 'playing dead,' an opossum's heart rate drops, and they may even excrete a foul-smelling substance.",
  "Hissing, growling, and baring their 50 teeth are common ways opossums try to scare off predators.",
  "Despite their fierce display, opossums are generally not aggressive and prefer to avoid conflict.",
  "Their keen sense of smell and hearing helps them detect danger early."
];
