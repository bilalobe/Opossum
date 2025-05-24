# Advanced Reasoning with DSPy

Having covered the basics of DSPy modules in [Getting Started](getting-started.md) and how to optimize them in [Optimizing Prompts](optimizing-prompts.md), we now turn to more complex reasoning tasks. DSPy provides powerful modules that enable language models (LMs) to perform multi-step reasoning, use tools, and tackle problems that require more than a simple input-output transformation.

Within Opossum Search, these advanced techniques can enhance the system's ability to answer complex queries, compare concepts, synthesize information, and potentially interact with other internal tools or knowledge bases.

## Why Advanced Reasoning in Opossum?

-   **Deeper Understanding:** Answer "why" and "how" questions that require step-by-step thinking, aligning with Opossum's goal of providing accurate, detailed information.
-   **Comparative Analysis:** Enable comparisons between concepts (e.g., "Compare opossums to raccoons," a query type mentioned in #`docs\technical\bot-user-simulation.md`).
-   **Tool Use & Grounding:** Allow the LM to potentially use internal Opossum tools (like specific knowledge retrieval functions, or even aspects of the [Capability Matrix](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\capability-matrix.md)) to ground its responses or perform calculations. This relates to future goals like RAG (#`docs\about\roadmap.md`).
-   **Complex Task Decomposition:** Break down complex user requests into manageable sub-problems that the LM can solve sequentially.

## Key DSPy Modules for Reasoning

1.  **`dspy.ChainOfThought(Signature)`:**
    *   **Concept:** Explicitly prompts the LM to "think step-by-step" to reach the final answer. It adds a `rationale` field to the signature internally.
    *   **Use Case:** Useful for arithmetic, symbolic reasoning, or any task where breaking down the problem helps improve accuracy. Opossum could use this for explaining complex biological facts or comparing different aspects of opossum behavior.

2.  **`dspy.ReAct(Signature, tools=[Tool])`:**
    *   **Concept:** Implements the ReAct (Reasoning + Acting) framework. The LM can iteratively use provided `tools` (which are just Python functions with descriptions) to gather information or perform actions, reasoning about the next step based on tool outputs.
    *   **Use Case:** Powerful for questions requiring external knowledge lookup (beyond the LM's training data) or calculations. In Opossum, tools could potentially wrap:
        *   A specific database lookup for opossum facts (potentially using data like `opossum_dataset_converted.json`).
        *   A function to check the [Service Availability](c:\Users\beb\PycharmProjects\Opossum\docs\service-availability\context-and-scope.md) status.
        *   A calculator for simple math mentioned in queries.
        *   Even a simplified interface to the [Backend Selection](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\backend-selection.md) logic to explain *why* a certain model might be chosen.

3.  **`dspy.MultiChainComparison(Signature, num_comparisons=N)`:**
    *   **Concept:** Generates multiple `ChainOfThought` responses (`N` times) and then synthesizes them into a final answer.
    *   **Use Case:** Improves robustness and explores different reasoning paths for complex questions where a single chain might be insufficient or prone to errors.

## Example: Chain of Thought for Comparison

Let's imagine using `ChainOfThought` to handle a comparative query, drawing on general knowledge.

```python
import dspy

# Assume dspy.settings.configure(lm=...) has been called

class CompareAnimals(dspy.Signature):
    """Compare two animals based on specified criteria."""
    animal_1 = dspy.InputField(desc="The first animal.")
    animal_2 = dspy.InputField(desc="The second animal.")
    criteria = dspy.InputField(desc="Aspects to compare (e.g., diet, habitat, lifespan).")
    comparison = dspy.OutputField(desc="A detailed comparison addressing the criteria.")

# Use ChainOfThought with the signature
compare_step_by_step = dspy.ChainOfThought(CompareAnimals)

# Run the module
animal1 = "Opossum"
animal2 = "Raccoon"
comparison_criteria = "diet and typical lifespan"

result = compare_step_by_step(animal_1=animal1, animal_2=animal2, criteria=comparison_criteria)

print(f"Comparing {animal1} and {animal2} based on {comparison_criteria}:\n")
# The rationale is generated internally by ChainOfThought but not typically part of the final output field
# To see it, you might inspect the prompt history: dspy.settings.lm.inspect_history(n=1) 
print(f"Comparison Result:\n{result.comparison}") 
```

## Example: ReAct for Tool Use

Imagine we want the LM to answer questions using specific facts that might be stored in our `opossum_dataset_converted.json` or a similar knowledge source. We can create a *hypothetical* DSPy `Tool` that allows the `ReAct` agent to query this data.

```python
import dspy

# --- Hypothetical Tool Definition ---
class OpossumFactTool(dspy.Tool):
    name = "opossum_fact_lookup"
    input_variable = "query"
    output_variable = "fact"
    description = "Looks up specific facts about opossums (e.g., 'gestation period', 'number of teeth') from the Opossum knowledge base."

    def __call__(self, query: str) -> str:

        query = query.lower()
        # Example lookup logic (replace with actual JSON parsing/search)
        if "gestation period" in query:
            # Hypothetical lookup result
            return "The gestation period for the Virginia opossum is very short, typically 12-13 days." 
        elif "number of teeth" in query:
             # Hypothetical lookup result
            return "Opossums have 50 teeth, more than any other North American mammal."
        else:
            # Fallback if fact not found in our data
            return f"Fact not found in Opossum knowledge base for '{query}'." 

# --- Signature for ReAct ---
class QuestionWithFacts(dspy.Signature):
    """Answer questions, potentially using external tools to find specific facts."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="A comprehensive answer incorporating retrieved facts if necessary.")

# --- Instantiate ReAct Module ---
# Provide the tool instance to the ReAct module
agent = dspy.ReAct(QuestionWithFacts, tools=[OpossumFactTool()])

# --- Run the Agent ---
user_question = "How many teeth does an opossum have, and how long is its gestation period?"
result = agent(question=user_question)

print(f"Question: {user_question}")
print(f"Answer: {result.answer}")

# Inspect history to see the Thought/Action/Observation steps
# dspy.settings.lm.inspect_history(n=1) 
```


## Combining and Optimizing Reasoning Modules

-   **Pipelines:** You can chain these advanced modules together just like simpler ones (see [Building Pipelines](building-pipelines.md)). For example, the output of a `ChainOfThought` module could feed into a `Predict` module for summarization.
-   **Optimization:** Teleprompters like `BootstrapFewShot` can optimize reasoning modules too. The training data would need to include examples demonstrating the desired reasoning process (potentially including intermediate steps or tool usage if optimizing `ReAct`). Metrics would evaluate the final output's correctness and potentially the quality of the reasoning steps.

## Integration in Opossum Search

-   **Complex Query Handling:** Use `ChainOfThought` or `ReAct` when the [Request Analyzer](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\architecture.md) detects complex reasoning or comparative queries (#`docs\model-integration\backend-selection.md`).
-   **Fact Grounding:** Implement tools for `ReAct` that access Opossum's curated knowledge (like `opossum_dataset_converted.json`) or even external APIs, ensuring responses are grounded in reliable data.
-   **Explanation Generation:** Use `ChainOfThought` to generate explanations for *why* Opossum provided a certain answer or took a specific action (e.g., explaining fallback logic, #`docs\technical\resilience-patterns.md`).
-   **Structured Data Extraction:** While not strictly reasoning, DSPy modules can be prompted to extract structured information (e.g., parameters for [SVG Generation](c:\Users\beb\PycharmProjects\Opossum\docs\image-processing\svg-generation.md)) as part of a reasoning process.

## Conclusion

DSPy's advanced reasoning modules like `ChainOfThought` and `ReAct` provide powerful ways to build more sophisticated and capable LM applications. By incorporating these techniques, Opossum Search can move beyond simple Q&A to handle more complex user needs, provide deeper insights, and potentially leverage its internal knowledge and tools more effectively. Remember that these modules can also be optimized using DSPy's teleprompters, ensuring both capability and efficiency.