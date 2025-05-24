# DSPy Usage Examples

## Basic DSPy Pipeline

This example demonstrates creating a basic DSPy pipeline for multi-step reasoning:

```python
# Example: Step-by-step reasoning with DSPy
import dspy
from app.integrations.dspy.manager import DSPyManager

# Initialize DSPy
dspy_manager = DSPyManager()

# Define a signature for question-answering
class QuestionAnswerer(dspy.Signature):
    """Answer questions with detailed reasoning."""
    question = dspy.InputField()
    reasoning = dspy.OutputField(desc="Step-by-step reasoning process")
    answer = dspy.OutputField(desc="Final concise answer")

# Create a chain-of-thought module
reasoner = dspy.ChainOfThought(QuestionAnswerer)

# Use the module
response = reasoner(question="What characteristics make opossums adaptable?")
print(f"Reasoning: {response.reasoning}")
print(f"Answer: {response.answer}")
```

## Optimizing Opossum's Prompts

This example shows how to optimize existing prompts from the YAML configuration:

```python
# Example: Optimizing an existing prompt template
from app.integrations.dspy.prompt_adapter import PromptOptimizer
from app.integrations.dspy.manager import DSPyManager

# Initialize components
dspy_manager = DSPyManager()
optimizer = PromptOptimizer(dspy_manager)

# Optimize a specific prompt template
optimized_prompt = optimizer.optimize(
    template_name="conversation.system_prompt",
    context="This prompt is for general conversation with users interested in adaptable systems"
)

print("Optimized Prompt:")
print(optimized_prompt)

# Save the optimized prompt for future use
from app.prompts.store import save_optimized_prompt
save_optimized_prompt("conversation.system_prompt", optimized_prompt)
```

## Enhanced Chat2SVG Pipeline

This example demonstrates using DSPy to enhance the Chat2SVG pipeline:

```python
# Example: Using the DSPy-enhanced Chat2SVG pipeline
from app.models.chat2svg.dspy_pipeline import DSPyEnhancedPipeline

# Initialize enhanced pipeline
pipeline = DSPyEnhancedPipeline()

# Process a request
svg_result = pipeline.process(
    description="A diagram showing an opossum's adaptable nature, with branches for different environments",
    style="minimalist",
    format="svg"
)

# Use the result
print(f"SVG Result (first 100 chars): {svg_result[:100]}...")
```

## Teleprompter for Automatic Optimization

This example shows using DSPy's teleprompter for automatic prompt optimization:

```python
# Example: Using Teleprompter for automatic optimization
import dspy
from app.integrations.dspy.manager import DSPyManager
from app.data.examples import load_examples

# Initialize DSPy
dspy_manager = DSPyManager()

# Load training examples
examples = load_examples("service_visualization")

# Define the task signature
class SVGGenerator(dspy.Signature):
    """Generate SVG code based on a description."""
    description = dspy.InputField()
    svg_code = dspy.OutputField()

# Create a basic module
basic_generator = dspy.Predict(SVGGenerator)

# Optimize with teleprompter
teleprompter = dspy.Teleprompter(basic_generator)
optimized_generator = teleprompter.optimize(examples)

# Use the optimized module
result = optimized_generator(description="A pie chart showing Opossum Search's backend usage distribution")
print(result.svg_code)
```

## Multistage Reasoning with Feedback

This example demonstrates complex multi-stage reasoning with feedback:

```python
# Example: Multi-stage reasoning with feedback
import dspy

class PlanGenerator(dspy.Signature):
    """Generate a resilience plan."""
    scenario = dspy.InputField()
    plan = dspy.OutputField()

class PlanValidator(dspy.Signature):
    """Validate a resilience plan."""
    scenario = dspy.InputField() 
    plan = dspy.InputField()
    issues = dspy.OutputField()

class PlanImprover(dspy.Signature):
    """Improve a plan based on identified issues."""
    scenario = dspy.InputField()
    plan = dspy.InputField()
    issues = dspy.InputField()
    improved_plan = dspy.OutputField()

# Create a multi-stage pipeline
def resilience_pipeline(scenario):
    # Stage 1: Generate initial plan
    generator = dspy.Predict(PlanGenerator)
    result = generator(scenario=scenario)
    initial_plan = result.plan
    
    # Stage 2: Validate the plan
    validator = dspy.Predict(PlanValidator)
    validation = validator(scenario=scenario, plan=initial_plan)
    issues = validation.issues
    
    # Stage 3: Improve the plan if issues exist
    if issues and issues.strip() != "No issues found.":
        improver = dspy.Predict(PlanImprover)
        improved = improver(
            scenario=scenario,
            plan=initial_plan,
            issues=issues
        )
        return improved.improved_plan
    
    return initial_plan

# Use the pipeline
scenario = "A service with fluctuating user demand and occasional API outages"
final_plan = resilience_pipeline(scenario)
print(final_plan)
```

⏱️ 10m - Setting up DSPy integration
⏱️ 15m - Optimizing existing prompts
⏱️ 20m - Enhancing Chat2SVG pipeline
⏱️ 25m - Implementing advanced reasoning chains

## Temporal Markers

┌─────────────────────────────────────────────────────────┐
│ Last updated: 2025-04-11                                │
│ Estimated reading time: 15 minutes                      │
│ Documentation heartbeat: 0 days since last validation   │
└─────────────────────────────────────────────────────────┘

## Related Documentation

- DSPy Integration Overview
- DSPy Technical Implementation 
- DSPy Metrics & Performance
- Chat2SVG Pipeline
