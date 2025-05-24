/// <reference types="vite/client" />
import { GoogleGenAI, GenerateContentResponse, Part } from "@google/genai";
// ...existing code...
import { AVAILABLE_ACTIONS } from '../constants';

// API key will be retrieved from Vite's environment variables (import.meta.env)
// Ensure VITE_GEMINI_API_KEY is set in your build environment (e.g., GitHub Actions secrets)
const apiKeyFromEnv = import.meta.env.VITE_GEMINI_API_KEY;

if (!apiKeyFromEnv) {
    console.error("CRITICAL: VITE_GEMINI_API_KEY is not defined in import.meta.env! API calls will fail.");
    // Depending on desired behavior, you might throw an error here or let individual functions handle it.
    // For now, we'll let the SDK potentially throw if it's initialized with undefined.
}

const ai = new GoogleGenAI({ apiKey: apiKeyFromEnv });

export interface GetOpossumActionParams {
  personaPrompt: string;
  currentViewText: string;
  hunger: number;
  fear: number;
  energy: number;
  memory: string;
}

function parseLLMResponse(responseText: string): LLMAction | null {
  const actionMatch = responseText.match(/ACTION:\s*(.+)/i);
  const reasonMatch = responseText.match(/REASON:\s*(.+)/i);

  let action = actionMatch?.[1]?.trim().toUpperCase() || "";
  const reason = reasonMatch?.[1]?.trim() || "No specific reason provided.";

  if (!action || !reasonMatch) {
    console.warn(`LLM response missing ACTION or REASON: '${responseText}'. Falling back.`);
    action = AVAILABLE_ACTIONS[Math.floor(Math.random() * 4)]; // Random move
    return { action, reason: "Couldn't decide clearly, so chose randomly."};
  }

  if (!AVAILABLE_ACTIONS.includes(action)) {
    console.warn(`LLM proposed an invalid action: '${action}'. Trying to salvage or falling back.`);
    const moveKeywords = ["NORTH", "SOUTH", "EAST", "WEST"];
    const eatKeyword = "EAT";
    const hissKeyword = "HISS";
    const playDeadKeyword = "PLAY_DEAD";

    let salvagedAction = "";
    if (moveKeywords.some(kw => action.includes(kw))) {
        salvagedAction = `MOVE_${moveKeywords.find(kw => action.includes(kw)) || ""}`;
    } else if (action.includes(eatKeyword)) {
        salvagedAction = "EAT";
    } else if (action.includes(hissKeyword)) {
        salvagedAction = "HISS";
    } else if (action.includes(playDeadKeyword)) {
        salvagedAction = "PLAY_DEAD";
    }

    if (AVAILABLE_ACTIONS.includes(salvagedAction)) {
        action = salvagedAction;
        console.warn(`Salvaged action to: ${action}`);
    } else {
        action = AVAILABLE_ACTIONS[Math.floor(Math.random() * 4)]; // Random move
        console.warn(`Falling back to random move action: ${action}`);
    }
  }

  return { action, reason };
}


export async function getOpossumAction(params: GetOpossumActionParams): Promise<LLMAction | null> {
  if (!apiKeyFromEnv) {
    console.error("VITE_GEMINI_API_KEY not available. Gemini API calls will fail for Opossum Action.");
    return { action: "HISS", reason: "Feeling confused due to missing API key configuration." };
  }

  const contentParts: Part[] = [
    { text: params.personaPrompt },
    { text: "\n--- CURRENT SITUATION ---" },
    { text: `Current Senses: ${params.currentViewText}` },
    { text: `Internal State: Hunger=${params.hunger.toFixed(1)}, Fear=${params.fear.toFixed(1)}, Energy=${params.energy.toFixed(1)}` },
    { text: `Memory: ${params.memory}` },
    { text: "\n--- YOUR DECISION ---" },
    { text: "Based on the above, what is your next action and why? Remember the format:\nACTION: [Your Action]\nREASON: [Your Reason]" }
  ];

  try {
    const response: GenerateContentResponse = await ai.models.generateContent({
        model: 'gemini-2.5-flash-preview-04-17',
        contents: { parts: contentParts },
        config: {
            temperature: 0.75,
            topP: 0.95,
            topK: 40,
        }
    });

    const text = response.text;
    console.log("LLM Raw Response for Opossum Action:", text);
    const parsed = parseLLMResponse(text);
    if (!parsed) {
        console.error("Failed to parse LLM response for Opossum Action:", text);
        return { action: "HISS", reason: "I'm a bit confused right now." };
    }
    return parsed;

  } catch (error) {
    console.error("Error calling Gemini API for Opossum Action:", error);
    return { action: "HISS", reason: `Something startled me! (API Error: ${error instanceof Error ? error.message : 'Unknown error'})` };
  }
}

export async function generateSceneImage(prompt: string): Promise<string | null> {
  if (!apiKeyFromEnv) {
    console.error("VITE_GEMINI_API_KEY not available. Imagen API calls will fail.");
    return null;
  }

  try {
    const response = await ai.models.generateImages({
        model: 'imagen-3.0-generate-002',
        prompt: `${prompt}, pixel art style, retro video game art, 16-bit, top-down view of the scene`,
        config: {
            numberOfImages: 1,
            outputMimeType: 'image/jpeg',
        },
    });

    if (response.generatedImages && response.generatedImages.length > 0 && response.generatedImages[0].image?.imageBytes) {
      const base64ImageBytes = response.generatedImages[0].image.imageBytes;
      return `data:image/jpeg;base64,${base64ImageBytes}`;
    }
    console.warn("Imagen API did not return any images.");
    return null;
  } catch (error) {
    console.error("Error calling Imagen API:", error);
    return null;
  }
}

export async function getGroundedResponse(query: string): Promise<{ text: string; sources: GroundingChunk[] }> {
    if (!apiKeyFromEnv) {
      console.error("VITE_GEMINI_API_KEY not available. Grounded search API calls will fail.");
      return { text: "Search is unavailable due to missing API key.", sources: [] };
    }
    try {
        const response = await ai.models.generateContent({
            model: "gemini-2.5-flash-preview-04-17",
            contents: query,
            config: {
                tools: [{ googleSearch: {} }],
            },
        });
        const text = response.text;
        const sources = response.candidates?.[0]?.groundingMetadata?.groundingChunks || [];
        return { text, sources: sources as GroundingChunk[] };
    } catch (error) {
        console.error("Error calling Gemini API with Google Search:", error);
        return { text: "Failed to get grounded response.", sources: [] };
    }
}
