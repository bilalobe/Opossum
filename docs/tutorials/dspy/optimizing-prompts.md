# Optimizing Prompts with DSPy

In the [Getting Started](getting-started.md) guide, we saw how to define DSPy modules and signatures to interact with language models (LMs) like [Gemini](c:\Users\beb\PycharmProjects\Opossum\docs\model-integration\providers.md) or [Ollama](c:\Users\beb\PecharmProjects\Opossum\docs\model-integration\providers.md) within Opossum Search. Now, let's explore one of DSPy's most powerful features: **optimizing** the prompts used by these modules automatically.

Manually crafting the perfect prompt ("prompt engineering") can be time-consuming and brittle. DSPy replaces this manual effort with **optimizers** (called "Teleprompters") that algorithmically search for effective prompts based on your specific needs and data.

## Why Optimize Prompts in Opossum?

-   **Improved Accuracy & Relevance:** Generate prompts that lead to more accurate and relevant responses from the underlying LMs for search queries or conversational tasks, aligning with Opossum's goal of providing scientifically accurate facts.
-   **Enhanced Efficiency:** Discover prompts that achieve the desired outcome with fewer tokens or faster response times, contributing to [Optimization Strategies](c:\Users\beb\PycharmProjects\Opossum\docs\infrastructure\optimization-strategies.md).
-   **Adaptability:** Automatically adjust prompts when underlying models change or when new data reveals weaknesses in existing prompts.
-   **Consistency:** Ensure more consistent behavior across different types of inputs.
-   **Constraint Adherence:** Optimize prompts to better follow specific constraints defined within Opossum (e.g., response format, tone, adherence to `evaluation_criteria` found in datasets like `opossum_dataset_converted.json`).

## Core Concepts for Optimization

1.  **Training Data:** Optimizers need examples to learn from. This typically consists of input/output pairs that demonstrate the desired behavior. For Opossum, this data could come from:
    *   Curated examples like those in `opossum_dataset_converted.json`, mapping `user_input` to `expected_response`.
    *   Logged interactions (potentially filtered or annotated).
    *   Synthetic data generated for specific scenarios.
    *   Data used for evaluating [response generation](c:\Users\beb\PecharmProjects\Opossum\docs\conversation\response-generation.md) quality.

2.  **Metric:** You need a way to tell the optimizer what "good" looks like. A metric is a function that scores the output of your DSPy module against the desired output in your training data. Examples:
    *   Exact match accuracy on a specific field (e.g., `main_fact`).
    *   F1 score for information extraction.
    *   LLM-based evaluation (using another LM to judge quality based on criteria like `accuracy` or `completeness` from the dataset).
    *   Custom metrics specific to Opossum's goals (e.g., checking if an SVG response is valid, measuring adherence to safety guidelines, validating against `evaluation_criteria`).

3.  **Teleprompters (Optimizers):** These are the DSPy algorithms that perform the optimization. They take your un-optimized module(s), training data, and a metric, then experiment with different prompts (and potentially demonstrations) to create an optimized version of your module. Common teleprompters include:
    *   `BootstrapFewShot`: Generates demonstrations (examples) to include in the prompt context. Effective for few-shot learning.
    *   `MIPRO (Multi-stage Instruction Prompt Refinement)`: Iteratively refines the instruction part of the prompt using Bayesian Optimization. Good for complex instructions.
    *   `SignatureOptimizer`: Optimizes the textual descriptions within your signature (e.g., `InputField` descriptions).
    *   Others like `BootstrapFewShotWithRandomSearch`.

## The Optimization Process (Compilation)

Optimizing in DSPy is often referred to as "compiling" your program. The general steps are:

1.  **Prepare Data:** Load your data (e.g., from `opossum_dataset_converted.json`) and format it into a list of `dspy.Example` objects. Each example should map the input fields (like `user_input`) to the desired ground truth output fields (like `main_fact` or a structured version of `expected_response`).
2.  **Define Metric:** Write a Python function `metric(gold, prediction, trace?) -> score` where `gold` is the `dspy.Example` (ground truth) and `prediction` is the output from your module. The score is typically a boolean or a float (higher is better).
3.  **Instantiate Teleprompter:** Choose an optimizer and configure it with your metric and any specific parameters (e.g., `teleprompter = dspy.BootstrapFewShot(metric=your_metric, max_bootstrapped_demos=4)`).
4.  **Compile:** Call the teleprompter's `compile` method, passing your *student* module (the one to be optimized), training data, and potentially validation data (`optimizer.compile(student=your_module, trainset=your_training_data, valset=your_validation_data)`). This returns a *new*, optimized module instance.
5.  **Evaluate (Optional but Recommended):** Test the compiled module on a separate test dataset (not used during training or validation) to get an unbiased estimate of its performance.

## Optimization Example using Opossum Dataset

Let's adapt the Q&A example, imagining we load data from `opossum_dataset_converted.json`.

```python
import dspy
import json
from dspy.teleprompt import BootstrapFewShot
from dspy.evaluate.evaluate import Evaluate 

# Assume dspy.settings.configure(lm=...) has been called using Opossum's LM config

# --- Data Loading and Preparation ---
def load_opossum_data(filepath="c:/Users/beb/PycharmProjects/Opossum/opossum_dataset_converted.json"):
    """Loads data and converts it to dspy.Example format."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    examples = []
    for item in data.get("prompts", []):
        prompt_data = item.get("prompt", {})
        user_input = prompt_data.get("user_input")
        expected_response = prompt_data.get("expected_response", {})
        main_fact = expected_response.get("main_fact")
        # Add other fields as needed for your signature/metric
        
        if user_input and main_fact:
            # Create a dspy.Example. Input field is 'question', output field is 'answer'.
            # We map 'user_input' to 'question' and 'main_fact' to 'answer'.
            example = dspy.Example(question=user_input, answer=main_fact).with_inputs("question")
            examples.append(example)
            
    return examples

# Load and split data (simple split for demonstration)
all_examples = load_opossum_data()
split_point = int(len(all_examples) * 0.7)
trainset = all_examples[:split_point]
valset = all_examples[split_point:] # Use a separate validation set for compilation

# --- Signature Definition ---
class OpossumQA(dspy.Signature):
    """Answer questions about opossums based on general knowledge."""
    question = dspy.InputField(desc="A question about opossums.")
    answer = dspy.OutputField(desc="A concise factual answer, focusing on the main point.")

# --- Metric Definition ---
def validate_opossum_answer(gold, pred, trace=None):
    """Checks if the predicted answer is contained within the gold answer (case-insensitive)."""
    # A simple metric; more sophisticated ones (e.g., using evaluation_criteria) are possible
    gold_answer = gold.answer.lower()
    pred_answer = pred.answer.lower()
    return pred_answer in gold_answer or gold_answer in pred_answer # Allow for slight variations

# --- Teleprompter Instantiation ---
# Configure BootstrapFewShot: Use validation set, metric, and specify max demos
teleprompter = BootstrapFewShot(metric=validate_opossum_answer, 
                                max_bootstrapped_demos=4, # Number of examples to find for the prompt
                                ) 

# --- Compilation ---
# Define the student module we want to optimize
uncompiled_qa = dspy.Predict(OpossumQA) 

# Compile the module using the training set and validation set
# The teleprompter uses the valset to guide the search for good prompts/demos
compiled_qa = teleprompter.compile(student=uncompiled_qa, 
                                   trainset=trainset, 
                                   valset=valset)

# --- Evaluation (Optional) ---
# Set up the evaluator
evaluate = Evaluate(devset=valset, # Evaluate on the validation set (or better, a separate test set)
                    metric=validate_opossum_answer, 
                    num_threads=4, 
                    display_progress=True, 
                    display_table=5)

# Evaluate the compiled module
score = evaluate(compiled_qa)
print(f"Evaluation score after compilation: {score}")

# --- Using the Optimized Module ---
question_to_ask = "Do opossums carry rabies?"
prediction = compiled_qa(question=question_to_ask)
print(f"\nQuestion: {question_to_ask}")
print(f"Optimized Predicted Answer: {prediction.answer}")

# Inspect the final prompt used (including generated demonstrations)
# dspy.settings.lm.inspect_history(n=1)
```

## Choosing Metrics and Teleprompters

-   **Metrics:** Start simple (e.g., exact match, keyword check). If needed, create more complex metrics, potentially using another LM (`dspy.Suggest`) to evaluate based on criteria like accuracy, completeness, and relevance defined in your dataset (`evaluation_criteria`). Align the metric closely with Opossum's specific goals for the task.
-   **Teleprompters:**
    -   `BootstrapFewShot` is often a good starting point, especially if providing good examples in the prompt is effective.
    -   `MIPRO` or `SignatureOptimizer` might be better if the core instruction needs refinement rather than just examples.
    -   Experimentation is key. Try different teleprompters and parameters on your validation set.

## Integration in Opossum Search

-   **Offline Process:** Compilation is computationally intensive and typically done offline as part of a model/prompt refinement workflow, not during live user requests.
-   **Workflow:**
    1.  Collect and prepare training/validation/test data (e.g., from `opossum_dataset_converted.json`, logs).
    2.  Define DSPy Signatures and Modules for the target task within Opossum (e.g., a specific step in [Pipeline Optimization](c:\Users\beb\PycharmProjects\Opossum\docs\infrastructure\pipeline-optimization.md)).
    3.  Define appropriate metrics aligned with Opossum's quality requirements (accuracy, adherence to constraints).
    4.  Run the DSPy compilation process using configured LMs ([`app/core/llm_clients.py`](app/core/llm_clients.py)).
    5.  Evaluate the compiled module thoroughly on a held-out test set.
    6.  Store the state of the optimized module (DSPy provides methods like `save()`/`load()`). This saves the learned prompts/demonstrations.
    7.  Load the *compiled* module into the Opossum application (e.g., within [`app/pipelines`](c:\Users\beb\PycharmProjects\Opossum\docs\infrastructure\pipeline-optimization.md) or relevant service) for use during runtime. This ensures production uses the optimized prompts.

## Next Steps

-   Explore how to combine multiple optimized modules in [Building Pipelines with DSPy](building-pipelines.md).
-   Dive into more complex reasoning patterns in [Advanced Reasoning with DSPy](advanced-reasoning.md).
-   Consult the official DSPy documentation for details on different teleprompters and advanced metric definition.