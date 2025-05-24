import React, { useState, useEffect, useCallback } from 'react';
import { Grid, CellType, OpossumState, OpossumPosition, LLMAction, Trail, TrailType, GridCell } from './types';
import {
  GRID_WIDTH, GRID_HEIGHT, INITIAL_OPOSSUM_STATE, INITIAL_NPC_OPOSSUM_STATE,
  MAX_HUNGER, MAX_FEAR, MAX_ENERGY, FOOD_ENERGY_GAIN, FOOD_HUNGER_REDUCTION,
  MOVE_ENERGY_COST, HUNGER_INCREASE_PER_TURN, FEAR_DECREASE_PER_TURN,
  FEAR_INCREASE_NEAR_THREAT, FEAR_INCREASE_NEAR_OPOSSUM, FEAR_INCREASE_FROM_RECENT_PRESENCE,
  CELL_DESCRIPTIONS, TRAIL_DESCRIPTIONS, MIN_ENERGY_FOR_MOVE,
  OPOSSUM_PERSONA_PROMPT, NPC_OPOSSUM_PERSONA_PROMPT,
  TRAIL_BASE_DURATION, TRAIL_STRESS_ADDITIONAL_DURATION, TRAIL_FOOD_ADDITIONAL_DURATION,
  TRAIL_DEFAULT_INTENSITY, TRAIL_MEDIUM_INTENSITY, TRAIL_HIGH_INTENSITY,
  FOOD_INITIAL_QUALITY, FOOD_QUALITY_DECAY_ON_PASS,
  OPOSSUM_FACTS, OPOSSUM_DIET_FACTS, OPOSSUM_DEFENSE_FACTS
} from './constants';
import GridDisplay from './components/GridDisplay';
import StateDisplay from './components/StateDisplay';
import ActionLog from './components/ActionLog';
import SceneImage from './components/SceneImage';
import LoadingSpinner from './components/LoadingSpinner';
import FactModal from './components/FactModal'; // Import new component
import { getOpossumAction, generateSceneImage } from './services/geminiService';

const getRandomFact = (factArray: string[] = OPOSSUM_FACTS): string => {
  return factArray[Math.floor(Math.random() * factArray.length)];
};

const generateInitialGrid = (): { grid: Grid, playerPos: OpossumPosition, npcPos: OpossumPosition } => {
  let newGrid: Grid = Array(GRID_HEIGHT).fill(null).map((_, r) =>
    Array(GRID_WIDTH).fill(null).map((_, c) => ({ type: CellType.Empty, id: `cell-${r}-${c}` }))
  );

  const occupied = new Set<string>();

  const placeItem = (type: CellType | null, itemProps?: Partial<GridCell>): OpossumPosition => {
    let x, y;
    do {
      x = Math.floor(Math.random() * GRID_WIDTH);
      y = Math.floor(Math.random() * GRID_HEIGHT);
    } while (occupied.has(`${x},${y}`));
    occupied.add(`${x},${y}`);
    if (type !== null) {
      newGrid[y][x] = { ...newGrid[y][x], type, ...itemProps };
    }
    return { x, y };
  };

  const playerPos = placeItem(null); 
  const npcPos = placeItem(null);    
  placeItem(CellType.Exit);

  for (let i = 0; i < 5; i++) placeItem(CellType.Food, { foodQuality: FOOD_INITIAL_QUALITY });
  const numObstacles = Math.floor((GRID_WIDTH * GRID_HEIGHT * 0.15));
  for (let i = 0; i < numObstacles; i++) placeItem(CellType.Obstacle);
  for (let i = 0; i < 2; i++) placeItem(CellType.Threat);

  return { grid: newGrid, playerPos, npcPos };
};


const App: React.FC = () => {
  const [grid, setGrid] = useState<Grid>([]);
  const [opossumPosition, setOpossumPosition] = useState<OpossumPosition>({ x: 0, y: 0 });
  const [opossumState, setOpossumState] = useState<OpossumState>(INITIAL_OPOSSUM_STATE);
  const [previousPlayerPosition, setPreviousPlayerPosition] = useState<OpossumPosition | null>(null);

  const [opossum2Position, setOpossum2Position] = useState<OpossumPosition | null>(null);
  const [opossum2State, setOpossum2State] = useState<OpossumState | null>(null);
  const [previousNpcPosition, setPreviousNpcPosition] = useState<OpossumPosition | null>(null);
  
  const [turnNumber, setTurnNumber] = useState<number>(0);
  const [gameLog, setGameLog] = useState<string[]>([]);
  const [currentLLMAction, setCurrentLLMAction] = useState<LLMAction | null>(null);
  const [currentImage, setCurrentImage] = useState<string | null>(null);
  
  const [isPlayerLLMLoading, setIsPlayerLLMLoading] = useState<boolean>(false);
  const [isNPCLoading, setIsNPCLoading] = useState<boolean>(false);
  const [isImageLoading, setIsImageLoading] = useState<boolean>(false);
  
  const [isGameOver, setIsGameOver] = useState<boolean>(false);
  const [gameMessage, setGameMessage] = useState<string>("");

  const [showFactModal, setShowFactModal] = useState<boolean>(false);
  const [currentDisplayFact, setCurrentDisplayFact] = useState<string | null>(null);
  const [loadingFact, setLoadingFact] = useState<string | null>(null);

  const resetGame = useCallback(() => {
    const { grid: newGrid, playerPos, npcPos } = generateInitialGrid();
    setGrid(newGrid);
    setOpossumPosition(playerPos);
    setOpossumState(INITIAL_OPOSSUM_STATE);
    setPreviousPlayerPosition(playerPos);
    setOpossum2Position(npcPos);
    setOpossum2State(INITIAL_NPC_OPOSSUM_STATE);
    setPreviousNpcPosition(npcPos);
    setTurnNumber(0);
    setGameLog([]);
    setCurrentLLMAction(null);
    setCurrentImage(null);
    setIsPlayerLLMLoading(false);
    setIsNPCLoading(false);
    setIsImageLoading(false);
    setIsGameOver(false);
    setGameMessage("Game started! Two opossums (O₁ & O₂) in the terrarium...");
    setShowFactModal(false);
    setCurrentDisplayFact(null);
    setLoadingFact(getRandomFact());
  }, []);

  useEffect(() => {
    resetGame();
  }, [resetGame]);

  useEffect(() => {
    if (isPlayerLLMLoading || isNPCLoading || isImageLoading) {
      setLoadingFact(getRandomFact());
    }
  }, [isPlayerLLMLoading, isNPCLoading, isImageLoading]);

  const handleShowFact = () => {
    setCurrentDisplayFact(getRandomFact());
    setShowFactModal(true);
  };

  const getCellDescriptionForLLM = useCallback((x: number, y: number, forNPC: boolean = false): string => {
    if (x < 0 || x >= GRID_WIDTH || y < 0 || y >= GRID_HEIGHT) return "a solid wall";
    
    const cell = grid[y][x];
    let description = "";

    const playerIsHere = opossumPosition.x === x && opossumPosition.y === y;
    const npcIsHere = opossum2Position && opossum2Position.x === x && opossum2Position.y === y;

    if (forNPC) {
      if (playerIsHere) description = CELL_DESCRIPTIONS[CellType.Opossum] || "the other opossum (O₁)";
      else if (npcIsHere) description = "yourself (O₂)";
      else description = CELL_DESCRIPTIONS[cell.type] || "an unknown area";
    } else { 
      if (npcIsHere) description = CELL_DESCRIPTIONS[CellType.Opossum2] || "another opossum (O₂)";
      else if (playerIsHere) description = "yourself (O₁)";
      else description = CELL_DESCRIPTIONS[cell.type] || "an unknown area";
    }
    
    if (cell.type === CellType.Food && cell.foodQuality !== undefined) {
      description += ` (Quality: ${cell.foodQuality}%)`;
      if (cell.foodQuality < 70) description += ", seems a bit disturbed";
    }

    if (cell.trail) {
      const trailSource = forNPC ? (cell.trail.source === 'npc' ? 'your' : 'O₁\'s') : (cell.trail.source === 'player' ? 'your' : 'O₂\'s');
      description += `. There's ${TRAIL_DESCRIPTIONS[cell.trail.type](cell.trail.intensity, cell.trail.source).replace(cell.trail.source === 'player' ? 'left by you' : 'from the other opossum', `from ${trailSource} trail`)}`;
    }
    return description;
  }, [grid, opossumPosition, opossum2Position]);


  const getCurrentViewTextForLLM = useCallback((pos: OpossumPosition, forNPC: boolean = false): string => {
    if (!grid || grid.length === 0) return "The world is a blur.";
    const { x, y } = pos;
    
    let currentCellDesc = "";
    const currentGridCell = grid[y]?.[x];
    if (!currentGridCell) return "Error: current cell data missing.";


    if ((forNPC && opossumPosition.x === x && opossumPosition.y === y) || (!forNPC && opossum2Position && opossum2Position.x === x && opossum2Position.y === y)) {
        // Cell is occupied by the other opossum
        currentCellDesc = forNPC ? (CELL_DESCRIPTIONS[CellType.Opossum] || "O₁") : (CELL_DESCRIPTIONS[CellType.Opossum2] || "O₂");
    } else {
        currentCellDesc = CELL_DESCRIPTIONS[currentGridCell.type] || 'an empty space';
        if (currentGridCell.type === CellType.Food && currentGridCell.foodQuality !== undefined) {
            currentCellDesc += ` (Quality: ${currentGridCell.foodQuality}%)`;
            if (currentGridCell.foodQuality < 70) currentCellDesc += ", seems a bit disturbed";
        }
    }
    
    if (currentGridCell.trail) {
         const trailSource = forNPC ? (currentGridCell.trail.source === 'npc' ? 'your' : 'O₁\'s') : (currentGridCell.trail.source === 'player' ? 'your' : 'O₂\'s');
         currentCellDesc += `. You sense ${TRAIL_DESCRIPTIONS[currentGridCell.trail.type](currentGridCell.trail.intensity, currentGridCell.trail.source).replace(currentGridCell.trail.source === 'player' ? 'left by you' : 'from the other opossum', `a ${trailSource} trail`)} right here`;
    }


    return `You are at (${x},${y}). You see:
    North (${x},${y-1}): ${getCellDescriptionForLLM(x, y - 1, forNPC)}.
    East (${x+1},${y}): ${getCellDescriptionForLLM(x + 1, y, forNPC)}.
    South (${x},${y+1}): ${getCellDescriptionForLLM(x, y + 1, forNPC)}.
    West (${x-1},${y}): ${getCellDescriptionForLLM(x - 1, y, forNPC)}.
    Current location content: ${currentCellDesc}.`;
  }, [grid, getCellDescriptionForLLM, opossumPosition, opossum2Position]);


  const processOpossumAction = (
    currentPos: OpossumPosition,
    currentState: OpossumState,
    action: LLMAction,
    isNPC: boolean,
    currentGridState: Grid
  ): { newPos: OpossumPosition, newState: OpossumState, newGrid: Grid, logMsg: string, ate: boolean, actionTaken: string } => {
    let newPos = { ...currentPos };
    let newState = { ...currentState };
    let newGrid: Grid = currentGridState.map(row => row.map(cell => {
        const newCell: GridCell = { id: cell.id, type: cell.type };
        if (cell.foodQuality !== undefined) newCell.foodQuality = cell.foodQuality;
        if (cell.trail) newCell.trail = { ...cell.trail };
        return newCell;
    }));
    let logMsg = "";
    let ateFoodThisTurn = false;
    let performedAction = action.action; // For contextual facts

    const selfIdentifier = isNPC ? "Other opossum (O₂)" : "You (O₁)";
    const otherOpossumPos = isNPC ? opossumPosition : opossum2Position;
    const previousCell = newGrid[currentPos.y][currentPos.x];

    if (action.action.startsWith("MOVE_")) {
      if (newState.energy < MIN_ENERGY_FOR_MOVE) {
        logMsg = `${selfIdentifier} is too tired to move!`;
        newState.memory = `Tried to move but too tired. ${action.reason}`;
      } else {
        let dx = 0, dy = 0;
        if (action.action === "MOVE_NORTH") dy = -1;
        else if (action.action === "MOVE_SOUTH") dy = 1;
        else if (action.action === "MOVE_EAST") dx = 1;
        else if (action.action === "MOVE_WEST") dx = -1;

        const targetX = newPos.x + dx;
        const targetY = newPos.y + dy;

        const isBlockedByObstacle = targetX < 0 || targetX >= GRID_WIDTH || targetY < 0 || targetY >= GRID_HEIGHT || newGrid[targetY][targetX].type === CellType.Obstacle;
        const isBlockedByOtherOpossum = otherOpossumPos && targetX === otherOpossumPos.x && targetY === otherOpossumPos.y;

        if (!isBlockedByObstacle && !isBlockedByOtherOpossum) {
          if (previousCell.type === CellType.Food && previousCell.foodQuality !== undefined) {
             newGrid[currentPos.y][currentPos.x].foodQuality = Math.max(0, previousCell.foodQuality - FOOD_QUALITY_DECAY_ON_PASS);
             logMsg += `${selfIdentifier} disturbed food at (${currentPos.x},${currentPos.y}). `;
          }
          newPos = { x: targetX, y: targetY };
          newState.energy = Math.max(0, newState.energy - MOVE_ENERGY_COST);
          newState.memory = `Moved ${action.action.split('_')[1].toLowerCase()}. ${action.reason}`;
        } else {
          logMsg = `${selfIdentifier} bumped into something${isBlockedByOtherOpossum ? ' (the other opossum!)': ''} or reached the edge!`;
          newState.fear = Math.min(MAX_FEAR, newState.fear + (isBlockedByOtherOpossum ? FEAR_INCREASE_NEAR_OPOSSUM : 0.5) );
          newState.memory = `Tried to move ${action.action.split('_')[1].toLowerCase()} but couldn't. ${action.reason}`;
        }
      }
    } else if (action.action === "EAT") {
      if (previousCell.type === CellType.Food) {
        const qualityMultiplier = (previousCell.foodQuality || FOOD_INITIAL_QUALITY) / FOOD_INITIAL_QUALITY;
        newGrid[newPos.y][newPos.x].type = CellType.Empty;
        delete newGrid[newPos.y][newPos.x].foodQuality;
        delete newGrid[newPos.y][newPos.x].trail; 
        newState.hunger = Math.max(0, newState.hunger - (FOOD_HUNGER_REDUCTION * qualityMultiplier));
        newState.energy = Math.min(MAX_ENERGY, newState.energy + (FOOD_ENERGY_GAIN * qualityMultiplier));
        logMsg = `${selfIdentifier} ate some food (Quality: ${(qualityMultiplier*100).toFixed(0)}%)! Yum!`;
        newState.memory = `Ate food. ${action.reason}`;
        ateFoodThisTurn = true;
      } else {
        logMsg = `${selfIdentifier} tried to eat, but there's nothing here!`;
        newState.memory = `Tried to eat but no food here. ${action.reason}`;
      }
    } else if (action.action === "HISS") {
      logMsg = `${selfIdentifier} lets out a fearsome HISS!`;
      newState.fear = Math.max(0, newState.fear - 1); 
      newState.memory = `Hissed. ${action.reason}`;
    } else if (action.action === "PLAY_DEAD") {
        logMsg = `${selfIdentifier} suddenly drops and plays dead!`;
        newState.fear = Math.max(0, newState.fear - 2); // Playing dead might calm down
        newState.energy = Math.max(0, newState.energy - 0.5); // Takes a bit of energy or represents stillness
        newState.memory = `Played dead. ${action.reason}`;
        // Opossum remains in the same spot, but might be ignored by threats for a turn (not implemented yet)
    }
    
    if ( (action.action.startsWith("MOVE_") && (newPos.x !== currentPos.x || newPos.y !== currentPos.y)) || ateFoodThisTurn ) {
        let trailType = TrailType.REGULAR;
        let intensity = TRAIL_DEFAULT_INTENSITY;
        let duration = TRAIL_BASE_DURATION;

        if (ateFoodThisTurn) {
            trailType = TrailType.FOOD_SCENT;
            intensity = TRAIL_HIGH_INTENSITY;
            duration += TRAIL_FOOD_ADDITIONAL_DURATION;
        } else if (currentState.fear > MAX_FEAR * 0.6) {
            trailType = TrailType.STRESS_SCENT;
            intensity = TRAIL_MEDIUM_INTENSITY + (currentState.fear > MAX_FEAR * 0.8 ? 1 : 0);
            intensity = Math.min(TRAIL_HIGH_INTENSITY, intensity);
            duration += TRAIL_STRESS_ADDITIONAL_DURATION;
        }
        newGrid[currentPos.y][currentPos.x].trail = {
            type: trailType,
            intensity: intensity,
            source: isNPC ? 'npc' : 'player',
            decayIn: duration,
        };
    }
    
    newState.hunger = Math.min(MAX_HUNGER, newState.hunger + HUNGER_INCREASE_PER_TURN);
    
    const cellAtNewPosType = newGrid[newPos.y][newPos.x].type;
    const otherOpossumAtNewPos = otherOpossumPos && newPos.x === otherOpossumPos.x && newPos.y === otherOpossumPos.y;

    if (cellAtNewPosType === CellType.Threat) {
        newState.fear = Math.min(MAX_FEAR, newState.fear + FEAR_INCREASE_NEAR_THREAT);
        logMsg += (logMsg ? " And it" : selfIdentifier) + " feels a threat!";
        newState.memory += ` Encountered a threat.`;
         performedAction = "ENCOUNTER_THREAT"; // For contextual fact
    } else if (otherOpossumAtNewPos) { 
        newState.fear = Math.min(MAX_FEAR, newState.fear + FEAR_INCREASE_NEAR_OPOSSUM);
        logMsg += (logMsg ? " And it" : selfIdentifier) + " is very close to the other opossum!";
        newState.memory += ` Very close to other opossum.`;
    } else {
        newState.fear = Math.max(0, newState.fear - FEAR_DECREASE_PER_TURN);
    }

    return { newPos, newState, newGrid, logMsg, ate: ateFoodThisTurn, actionTaken: performedAction };
  };


  const handleNextTurn = useCallback(async () => {
    if (isGameOver || isPlayerLLMLoading || isImageLoading || isNPCLoading) return;

    setTurnNumber(prev => prev + 1);
    let currentLogEntries: string[] = [];

    let workingGrid: Grid = grid.map(row => row.map(cell => {
      const newCell: GridCell = { id: cell.id, type: cell.type };
      if (cell.foodQuality !== undefined) newCell.foodQuality = cell.foodQuality;
      if (cell.trail) newCell.trail = { ...cell.trail };
      return newCell;
    }));

    for (let r = 0; r < GRID_HEIGHT; r++) {
      for (let c = 0; c < GRID_WIDTH; c++) {
        if (workingGrid[r][c].trail) {
          workingGrid[r][c].trail!.decayIn--;
          if (workingGrid[r][c].trail!.decayIn <= 0) {
            delete workingGrid[r][c].trail;
          }
        }
      }
    }
    setGrid(workingGrid); 

    setIsPlayerLLMLoading(true);
    let playerCurrentState = {...opossumState};
    if (previousNpcPosition && opossumPosition.x === previousNpcPosition.x && opossumPosition.y === previousNpcPosition.y) {
        playerCurrentState.fear = Math.min(MAX_FEAR, playerCurrentState.fear + FEAR_INCREASE_FROM_RECENT_PRESENCE);
        playerCurrentState.memory = "Sensed O₂ was just here. " + playerCurrentState.memory;
        currentLogEntries.push("You (O₁) feel an unnerving presence... O₂ must have been here moments ago!");
    }
    setPreviousPlayerPosition({...opossumPosition}); 

    const playerViewText = getCurrentViewTextForLLM(opossumPosition, false);
    const playerLLMResponse = await getOpossumAction({
      personaPrompt: OPOSSUM_PERSONA_PROMPT,
      currentViewText: playerViewText,
      hunger: playerCurrentState.hunger,
      fear: playerCurrentState.fear,
      energy: playerCurrentState.energy,
      memory: playerCurrentState.memory,
    });
    setIsPlayerLLMLoading(false);

    if (!playerLLMResponse) {
      currentLogEntries.push("You (O₁) seem hesitant or confused.");
    } else {
      setCurrentLLMAction(playerLLMResponse);
      let playerActionLogEntry = `You (O₁) ${playerLLMResponse.action.toLowerCase().replace('_', ' ')}. Reason: "${playerLLMResponse.reason}"`;
      
      const playerTurnResult = processOpossumAction(opossumPosition, playerCurrentState, playerLLMResponse, false, workingGrid);
      
      if (playerTurnResult.actionTaken === "EAT") playerActionLogEntry += ` -- <i>Fact: ${getRandomFact(OPOSSUM_DIET_FACTS)}</i>`;
      if (playerTurnResult.actionTaken === "HISS" || playerTurnResult.actionTaken === "PLAY_DEAD") playerActionLogEntry += ` -- <i>Fact: ${getRandomFact(OPOSSUM_DEFENSE_FACTS)}</i>`;
      if (playerTurnResult.actionTaken === "ENCOUNTER_THREAT") playerActionLogEntry += ` -- <i>Fact: ${getRandomFact(OPOSSUM_DEFENSE_FACTS)}</i>`;
      currentLogEntries.push(playerActionLogEntry);


      setIsImageLoading(true);
      const npcNearby = opossum2Position && (Math.abs(opossumPosition.x - opossum2Position.x) <=2 && Math.abs(opossumPosition.y - opossum2Position.y) <=2);
      generateSceneImage(`Opossum O₁ (player) ${playerLLMResponse.action.toLowerCase().replace('_',' ')} because "${playerLLMResponse.reason}". Senses: ${playerViewText}. ${npcNearby ? 'Opossum O₂ is nearby.' : ''}`)
        .then(setCurrentImage).catch(console.error).finally(() => setIsImageLoading(false));

      setOpossumPosition(playerTurnResult.newPos);
      setOpossumState(playerTurnResult.newState);
      workingGrid = playerTurnResult.newGrid; 
      setGrid(workingGrid); 
      if (playerTurnResult.logMsg) currentLogEntries.push(playerTurnResult.logMsg);

      if (playerTurnResult.newState.energy <= 0) { setIsGameOver(true); setGameMessage(`Game Over: You (O₁) ran out of energy after ${turnNumber + 1} turns. ${getRandomFact()}`); currentLogEntries.forEach(log => setGameLog(prev => [...prev, log])); return; }
      if (playerTurnResult.newState.hunger >= MAX_HUNGER) { setIsGameOver(true); setGameMessage(`Game Over: You (O₁) starved after ${turnNumber + 1} turns. ${getRandomFact()}`); currentLogEntries.forEach(log => setGameLog(prev => [...prev, log])); return; }
      if (playerTurnResult.newState.fear >= MAX_FEAR) { setIsGameOver(true); setGameMessage(`Game Over: You (O₁) became too terrified after ${turnNumber + 1} turns. ${getRandomFact()}`); currentLogEntries.forEach(log => setGameLog(prev => [...prev, log])); return; }
      if (workingGrid[playerTurnResult.newPos.y][playerTurnResult.newPos.x].type === CellType.Exit) { setIsGameOver(true); setGameMessage(`Congratulations O₁! You found the den and escaped in ${turnNumber + 1} turns! ${getRandomFact()}`); currentLogEntries.forEach(log => setGameLog(prev => [...prev, log])); return; }
    }
    
    if (isGameOver || !opossum2Position || !opossum2State) {
      currentLogEntries.forEach(log => setGameLog(prev => [...prev, log]));
      return;
    }

    setIsNPCLoading(true);
    let npcCurrentState = {...opossum2State};
    if (previousPlayerPosition && opossum2Position.x === previousPlayerPosition.x && opossum2Position.y === previousPlayerPosition.y) {
        npcCurrentState.fear = Math.min(MAX_FEAR, npcCurrentState.fear + FEAR_INCREASE_FROM_RECENT_PRESENCE);
        npcCurrentState.memory = "Sensed O₁ was just here. " + npcCurrentState.memory;
        currentLogEntries.push("Other opossum (O₂) seems spooked... perhaps it sensed you?");
    }
    if(opossum2Position) setPreviousNpcPosition({...opossum2Position});

    const npcViewText = getCurrentViewTextForLLM(opossum2Position, true);
    const npcLLMResponse = await getOpossumAction({
      personaPrompt: NPC_OPOSSUM_PERSONA_PROMPT,
      currentViewText: npcViewText,
      hunger: npcCurrentState.hunger,
      fear: npcCurrentState.fear,
      energy: npcCurrentState.energy,
      memory: npcCurrentState.memory,
    });
    setIsNPCLoading(false);

    if (!npcLLMResponse) {
      currentLogEntries.push("Other opossum (O₂) seems hesitant.");
    } else {
      let npcActionLogEntry = `Other opossum (O₂) ${npcLLMResponse.action.toLowerCase().replace('_', ' ')}. Reason: "${npcLLMResponse.reason}"`;
      
      const npcTurnResult = processOpossumAction(opossum2Position, npcCurrentState, npcLLMResponse, true, workingGrid);

      if (npcTurnResult.actionTaken === "EAT") npcActionLogEntry += ` -- <i>Fact: ${getRandomFact(OPOSSUM_DIET_FACTS)}</i>`;
      if (npcTurnResult.actionTaken === "HISS" || npcTurnResult.actionTaken === "PLAY_DEAD") npcActionLogEntry += ` -- <i>Fact: ${getRandomFact(OPOSSUM_DEFENSE_FACTS)}</i>`;
      if (npcTurnResult.actionTaken === "ENCOUNTER_THREAT") npcActionLogEntry += ` -- <i>Fact: ${getRandomFact(OPOSSUM_DEFENSE_FACTS)}</i>`;
      currentLogEntries.push(npcActionLogEntry);
      
      setOpossum2Position(npcTurnResult.newPos);
      setOpossum2State(npcTurnResult.newState);
      setGrid(npcTurnResult.newGrid); 
      if (npcTurnResult.logMsg) currentLogEntries.push(npcTurnResult.logMsg);
      
      if (npcTurnResult.newState.energy <= 0 || npcTurnResult.newState.hunger >= MAX_HUNGER || npcTurnResult.newState.fear >= MAX_FEAR) {
        currentLogEntries.push("The other opossum (O₂) seems to be in a bad state... It has become inactive. " + getRandomFact());
        setOpossum2Position(null); 
        setOpossum2State(null);
      }
    }
    currentLogEntries.forEach(log => setGameLog(prev => [...prev, log]));

  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isGameOver, isPlayerLLMLoading, isImageLoading, isNPCLoading, opossumPosition, opossumState, opossum2Position, opossum2State, grid, turnNumber, getCurrentViewTextForLLM, previousPlayerPosition, previousNpcPosition]);

  if (!grid || grid.length === 0 ) { 
    return <div className="min-h-screen flex items-center justify-center bg-gray-900"><LoadingSpinner text="Initializing Terrarium..." factText={loadingFact} /></div>;
  }
  
  const overallLoading = isPlayerLLMLoading || isImageLoading || isNPCLoading;
  let buttonText = "Next Turn";
  if (isPlayerLLMLoading) buttonText = "O₁ Thinking...";
  else if (isImageLoading) buttonText = "Visualizing Scene...";
  else if (isNPCLoading) buttonText = "O₂ Thinking...";
  if (isGameOver) buttonText = "Game Over";


  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-4 lg:p-8 flex flex-col">
      <header className="mb-6 text-center">
        <div className="flex justify-center items-center gap-4">
            <h1 className="text-4xl lg:text-5xl font-bold text-teal-400 tracking-tight">Opossum's Digital Terrarium</h1>
            <button
                onClick={handleShowFact}
                className="bg-sky-600 hover:bg-sky-500 text-white font-semibold py-2 px-3 rounded-lg shadow-md transition-colors duration-150 text-sm"
                title="Learn a random opossum fact!"
            >
                Opossum Wisdom 💡
            </button>
        </div>
        {isGameOver && <p className="text-xl md:text-2xl text-yellow-400 mt-3">{gameMessage}</p>}
        {!isGameOver && turnNumber >= 0 && <p className="text-lg text-gray-300 mt-2">{gameMessage || `Turn: ${turnNumber + 1}`}</p>}
      </header>

      <main className="flex-grow grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
        <div className="lg:col-span-1 flex flex-col gap-4 lg:gap-6">
          <GridDisplay grid={grid} opossumPosition={opossumPosition} opossum2Position={opossum2Position} />
          <StateDisplay opossumState={opossumState} /> 
          {opossum2State && opossum2Position && (
            <div className="p-4 bg-gray-800 rounded-lg shadow-xl border border-gray-700 mt-2">
                 <h3 className="text-lg font-semibold mb-2 text-purple-400 border-b border-gray-700 pb-1">Opossum O₂ Vitals</h3>
                 <p className="text-sm text-gray-300">Energy: {opossum2State.energy.toFixed(1)}, Hunger: {opossum2State.hunger.toFixed(1)}, Fear: {opossum2State.fear.toFixed(1)}</p>
                 <p className="text-sm text-gray-400 italic mt-1 h-12 overflow-y-auto">Memory: {opossum2State.memory}</p>
            </div>
          )}
        </div>

        <div className="lg:col-span-1 flex flex-col">
           <SceneImage 
            imageUrl={currentImage} 
            isLoading={isImageLoading} 
            actionDescription={currentLLMAction ? `Your (O₁) action: ${currentLLMAction.action.toLowerCase()}` : "Awaiting your move..."}
          />
        </div>
        
        <div className="lg:col-span-1 flex flex-col gap-4 lg:gap-6">
          <ActionLog logs={gameLog} />
          <div className="p-4 bg-gray-800 rounded-lg shadow-xl border border-gray-700">
            <h3 className="text-xl font-semibold mb-3 text-teal-400">Controls</h3>
            <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleNextTurn}
              disabled={isGameOver || overallLoading}
              className="flex-1 bg-teal-600 hover:bg-teal-500 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg shadow-md transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:ring-opacity-75 flex items-center justify-center"
            >
              {overallLoading && <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg> }
              {buttonText}
            </button>
            <button
              onClick={resetGame}
              className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-opacity-75"
            >
              Reset Game
            </button>
            </div>
            {overallLoading && <LoadingSpinner text="Please wait..." factText={loadingFact} />}
          </div>
        </div>
      </main>
      <footer className="mt-8 text-center text-sm text-gray-500">
        <p>Powered by Gemini & Imagen. Opossum AI by Noodles.</p>
         <p>Player is O₁, NPC is O₂. Trails affect scents. Movement can spoil food.</p>
      </footer>
      {showFactModal && currentDisplayFact && (
        <FactModal fact={currentDisplayFact} onClose={() => setShowFactModal(false)} onNewFact={handleShowFact} />
      )}
    </div>
  );
};

export default App;
