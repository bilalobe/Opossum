# Model Context Protocol (MCP) Architecture

## Overview

The Model Context Protocol (MCP) is a cornerstone of the Opossum Search system, designed to provide rich, dynamic, and relevant context to all AI models and decision-making components. It acts as the primary sensory and short-term memory system, ensuring that interactions are coherent, informed, and adaptive. The MCP is inspired by an opossum's acute senses, particularly its whiskers and olfactory system, which allow it to navigate its environment effectively.

## Core Responsibilities

1.  **Context Aggregation:**
    *   Dynamically collects information from user inputs, conversation history, system state, tool availability (e.g., Chat2SVG, OpossumFactTool), and relevant data from backend knowledge sources (including semi-structured datasets accessed via the GraphQL API).
2.  **Contextual Structuring:**
    *   Organizes aggregated information into a standardized `ContextObject`. This object serves as the single source of truth for contextual understanding during an interaction.
3.  **Dynamic Reformulation:**
    *   The MCP is not static. It actively processes and refines context by:
        *   Summarizing or truncating conversation history to fit model constraints.
        *   Prioritizing information based on inferred user intent or task requirements.
        *   Enriching context with data fetched on-demand.
4.  **State Management:**
    *   Maintains the `ContextObject` throughout a user session, ensuring continuity.
5.  **Interface to AI Models:**
    *   Provides tailored "views" or "slices" of the `ContextObject` to different consumers, such as DSPy programs or specific LLM backends, ensuring they receive context in their optimal format.

## Key Components of the MCP

*   **MCP Manager:** The central orchestrator of the MCP. It handles the logic for aggregation, reformulation, and state updates.
*   **`ContextObject`:** A structured data object (e.g., a Python dictionary or class instance) that holds all relevant contextual information for the current interaction. This includes:
    *   `session_id`
    *   `user_query_history` (list of turns)
    *   `current_user_query`
    *   `detected_intent`
    *   `active_tools_state` (e.g., status of Chat2SVG, results from OpossumFactTool)
    *   `system_persona_directives`
    *   `retrieved_knowledge_snippets`
    *   `operational_flags` (e.g., resource constraints)
*   **Context Adapters:** (Conceptual) Modules responsible for transforming the `ContextObject` into the specific input format required by different LLMs or DSPy programs.

## Interaction with Other Systems

*   **Backend Orchestrator:** The main application logic interacts heavily with the MCP Manager to update and retrieve context.
*   **DSPy Integration:** DSPy programs are primary consumers of the context provided by the MCP. The richness of this context is vital for effective prompt optimization and few-shot learning.
*   **GraphQL API:** The MCP may trigger internal GraphQL queries to fetch supplementary data needed to enrich the `ContextObject`.
*   **LLM Clients:** Receive their final, context-laden prompts, which have been shaped by the MCP's understanding of the interaction.

## Architectural Goals

*   **Decoupling:** Decouple AI models from the raw complexities of state management and context gathering.
*   **Consistency:** Ensure all parts of the system operate from a consistent understanding of the current context.
*   **Extensibility:** Allow new sources of context or new consumers of context to be integrated with relative ease.
*   **Foundation for Learning:** Provide the structured data necessary for future self-enhancement capabilities (see [Roadmap & Vision](../about/roadmap-vision.md)).


The MCP is critical for enabling the nuanced, adaptive, and intelligent behavior that Opossum Search aims to deliver, truly embodying the "sensory acuity" of its namesake.