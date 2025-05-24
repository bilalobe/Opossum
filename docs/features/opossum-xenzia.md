<!-- filepath: docs/features/opossum-xenzia.md -->
# Opossum Xenzia: Interactive Learning Environment

Opossum Xenzia is a unique interactive feature within the Opossum Search ecosystem. It serves multiple purposes:

1.  **Educational Tool:** To playfully educate users about Virginia Opossums, their behaviors, diet, and ecological importance.
2.  **AI Research Testbed:** To explore and refine AI concepts like agent-based reasoning, context management (MCP), and multi-agent interactions in a controlled, game-like environment.
3.  **Community Engagement:** To provide a fun and memorable way for users to connect with the Opossum Search project and its themes.

## Gameplay Concept

Inspired by classic "snake" games, Opossum Xenzia places the player (or an LLM-driven agent) in the role of an opossum navigating a 2D grid world. The core loop involves:

*   **Perception:** The game presents a textual or simple visual representation of the opossum's immediate surroundings and internal state (e.g., hunger, fear). This forms a simplified MCP `ContextObject` for the agent.
*   **Decision:** The agent (player or LLM) is prompted: "You are an opossum. Based on your senses and state, what do you do next and why?"
*   **Action:** The chosen action (e.g., move, eat "food" items, interact with "threats," "play dead") is executed.
*   **World Update:** The game state and the agent's MCP `ContextObject` are updated based on the action's outcome.

## Key Planned Features & Mechanics:

*   **LLM-Driven Agent:** The primary "player" opossum can be controlled by an LLM, making decisions based on its persona and the MCP context provided by the game.
*   **NPC Opossum:** Introduction of a second, independently operating opossum (also potentially LLM-driven) to create dynamic interactions, competition for resources, or observational learning opportunities.
*   **Scent Trails & Shadows:**
    *   **Trails:** Opossums leave temporary "scent trails" that other agents can detect and interpret, influencing navigation.
    *   **Shadows:** A more abstract mechanic where an opossum's passage might have subtle, delayed, or unpredictable influences on the environment or other agents, symbolizing unseen ecological connections.
*   **Educational Triggers:** Specific game events (e.g., eating a "tick" item, encountering a "car" threat) can trigger informative pop-ups about real opossum facts and conservation.
*   **Data Source for MCP Enhancement:** Interactions and outcomes within Opossum Xenzia, especially from LLM-driven agents, will provide valuable data for training and refining the self-enhancing capabilities of the main Opossum Search MCP (see [Roadmap & Vision](../about/roadmap-vision.md)).

## Technical Considerations:

*   The game environment will be kept relatively simple initially to focus on agent logic and MCP interaction.
*   The "senses" provided to the LLM agent will be carefully curated to mimic limited, localized perception.
*   The LLM's action space will be constrained to relevant opossum behaviors.

Opossum Xenzia is envisioned as a living part of the Opossum Search project, evolving alongside our core AI capabilities and serving as a charming ambassador for both the technology and its marsupial inspiration.

[Play Opossum Xenzia Now!](Opossum/opossum-xenzia/)