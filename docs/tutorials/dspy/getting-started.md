# Getting Started with DSPy

Welcome to the DSPy tutorial for Opossum Search! DSPy is a framework for algorithmically optimizing language model (LM) prompts and weights, especially when LMs are used in pipelines. Within Opossum Search, DSPy helps us build more robust, efficient, and adaptable interactions with the underlying language models like [Gemini](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\providers.md), [Ollama](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\providers.md), and [Transformers](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\providers.md).

## Why DSPy in Opossum Search?

-   **Systematic Prompt Engineering:** Move beyond manual prompt tweaking to algorithmic optimization.
-   **Modular Pipelines:** Construct complex LM workflows (e.g., for multi-step reasoning or specialized response generation) using composable modules.
-   **Adaptability:** Optimize prompts and module interactions based on performance metrics, making the system more resilient to changes in underlying models or data.
-   **Integration with Existing Infrastructure:** DSPy can work alongside Opossum's existing [hybrid model selection](c:\Users\beb\PycharmProjects\Opossum\docs\technical\hybrid-model-selection.md) and [resilience patterns](c:\Users\beb\PycharmProjects\Opossum\docs\technical\resilience-patterns.md).

## Core Concepts

1.  **Signatures:** Define the input/output behavior of an LM task (e.g., `Question -> Answer`). They specify the fields your LM module should expect and produce.
2.  **Modules:** Building blocks of DSPy programs (e.g., `dspy.Predict`, `dspy.ChainOfThought`, `dspy.ReAct`). Modules take Signatures and handle the interaction with the LM.
3.  **Language Models (LMs):** DSPy interacts with LMs. In Opossum, this could be configured to use Gemini, Ollama, or local Transformers based on availability and configuration ([`docs/model-integration/configuration.md`](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\configuration.md)).
4.  **Optimizers (Teleprompters):** Algorithms that tune the prompts and/or weights within your DSPy modules based on a defined metric and training data (more in the [Optimizing Prompts](optimizing-prompts.md) tutorial).

## Prerequisites

-   Ensure your Opossum Search development environment is set up according to the [DevOps Guide](c:\Users\beb\PecharmProjects\Opossum\docs\technical\devops-guide.md).
-   DSPy should be included in the project's Python dependencies (`requirements.txt` or similar).
-   Familiarity with Opossum's configuration for LM providers ([`app/config.py`](c:\Users\beb\PecharmProjects\Opossum\docs\technical\devops-guide.md)).

## Basic Usage Example

Let's configure a simple DSPy interaction using one of Opossum's configured LMs.

```python
# Example: Assumes LM configuration is loaded elsewhere
# (e.g., from Opossum's config module)
import dspy
from app.core.llm_clients import get_configured_lm # Hypothetical function

# 1. Configure the Language Model (using Opossum's setup)
# This might involve selecting Gemini, Ollama, etc. based on Opossum's logic
# For simplicity, let's assume we get a configured dspy LM client
try:
    # Attempt to get a high-capability model like Gemini first
    lm_client = get_configured_lm(prefer_service="gemini") 
except Exception:
    # Fallback if preferred service fails (using Opossum's resilience)
    lm_client = get_configured_lm(prefer_service="ollama") 

dspy.settings.configure(lm=lm_client)

# 2. Define a Signature
class BasicQA(dspy.Signature):
    """Answer questions based on context."""
    context = dspy.InputField(desc="May contain relevant facts.")
    question = dspy.InputField()
    answer = dspy.OutputField(desc="Often short, concise answer.")

# 3. Use a Module
generate_answer = dspy.Predict(BasicQA)

# 4. Run the module
context_data = "Opossums are marsupials native to the Americas. They are known for playing dead."
question_to_ask = "What defense mechanism are opossums known for?"

prediction = generate_answer(context=context_data, question=question_to_ask)

print(f"Question: {question_to_ask}")
print(f"Predicted Answer: {prediction.answer}")

```

*(Note: The `get_configured_lm` function is hypothetical and represents how Opossum's existing LM client management and selection logic would integrate with DSPy's `dspy.settings.configure`.)*

## Integration Points in Opossum

-   **LM Configuration:** DSPy needs to be configured to use the LM instances managed by Opossum (Gemini, Ollama, Transformers). This involves wrapping or adapting Opossum's clients for DSPy compatibility.
-   **Pipeline Construction:** DSPy modules can be used to define specific parts of the request processing pipeline, potentially replacing or augmenting existing logic in [`app/pipelines`](c:\Users\beb\PycharmProjects\Opossum\docs\infrastructure\pipeline-optimization.md) or similar areas.
-   **Prompt Management:** DSPy's optimization capabilities can enhance Opossum's [prompt management strategies](c:\Users\beb\PycharmProjects\Opossum\docs\technical\prompt-management.md).

## Next Steps

-   Learn how to automatically improve prompts in [Optimizing Prompts with DSPy](optimizing-prompts.md).
-   Discover how to chain modules together in [Building Pipelines with DSPy](building-pipelines.md).
-   Explore more complex techniques in [Advanced Reasoning with DSPy](advanced-reasoning.md).