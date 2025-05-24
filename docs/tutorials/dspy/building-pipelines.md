# Building Pipelines with DSPy

In the previous tutorials, we explored [basic DSPy concepts](./getting-started.md), [optimizing prompts](./optimizing-prompts.md), and [advanced reasoning techniques](./advanced-reasoning.md). Now let's examine how to chain these components into cohesive **pipelines** - one of DSPy's most powerful features for complex language processing tasks.

## Why Build Pipelines in Opossum?

-   **Decomposition:** Break down complex language tasks into smaller, more manageable steps that are easier to develop, debug, and maintain.
-   **Specialized Processing:** Apply different DSPy modules (possibly with different LM backends) to handle specific sub-tasks they're best suited for.
-   **Controlled Information Flow:** Explicitly define how information moves through your application, reducing "lost context" problems.
-   **Resilience Enhancement:** Align with Opossum's [resilience patterns](../technical/resilience-patterns.md) by allowing fallbacks or alternative paths if a component fails.
-   **Progressive Refinement:** Gradually improve response quality through multiple processing stages.

## Pipeline Basics

DSPy pipelines are built using the `dspy.Module` class. By inheriting from this class, you can define your own multi-step modules that orchestrate calls to other DSPy modules.

The general pattern looks like this:

```python
class MyPipeline(dspy.Module):
    def __init__(self, param1, param2, ...):
        super().__init__()
        # Initialize sub-modules
        self.step1 = dspy.Predict(Step1Signature)
        self.step2 = dspy.ChainOfThought(Step2Signature)
        # ... more sub-modules
        
    def forward(self, input1, input2, ...):
        # Run first step
        step1_result = self.step1(input_field1=input1, input_field2=input2)
        
        # Use step1's output as input for step2
        step2_result = self.step2(
            input_field_for_step2=step1_result.output_field_from_step1
        )
        
        # ... more steps
        
        # Return final result
        return step2_result  # or create and return a dspy.Prediction object
```

This structure provides a clean separation of concerns while maintaining a clear information flow.

## Example: Multi-Stage Fact-Based Q&A Pipeline

Let's build a pipeline using the `OpossumFactTool` from the [Advanced Reasoning](./advanced-reasoning.md) tutorial to create a more sophisticated Q&A system:

```python
import dspy
from app.tools.fact_checker import OpossumFactTool  # Our fact lookup tool

# 1. Define signatures for each stage
class QuestionAnalysis(dspy.Signature):
    """Analyze a question to identify key concepts for lookup."""
    question = dspy.InputField()
    key_concepts = dspy.OutputField(desc="List of 2-3 key concepts to look up, separated by semicolons")
    
class FactRetrieval(dspy.Signature):
    """Retrieve facts based on key concepts."""
    key_concepts = dspy.InputField()
    retrieved_facts = dspy.OutputField(desc="Facts retrieved from knowledge base")
    
class AnswerGeneration(dspy.Signature):
    """Generate a comprehensive answer using question and retrieved facts."""
    question = dspy.InputField()
    retrieved_facts = dspy.InputField()
    answer = dspy.OutputField(desc="A comprehensive, factual answer to the question.")

# 2. Build the pipeline
class OposumQAPipeline(dspy.Module):
    def __init__(self):
        super().__init__()
        # Initialize individual modules
        self.question_analyzer = dspy.ChainOfThought(QuestionAnalysis)
        
        # Create the fact tool
        self.fact_tool = OpossumFactTool(
            threshold=0.25,
            max_results=3,
            search_method="auto"
        )
        
        # Final answer generation with reasoning
        self.answer_generator = dspy.ChainOfThought(AnswerGeneration)
        
    def forward(self, question):
        # Step 1: Analyze the question to extract key concepts
        analysis = self.question_analyzer(question=question)
        key_concepts = analysis.key_concepts
        
        # Step 2: Retrieve facts for each key concept
        retrieved_facts = []
        for concept in key_concepts.split(';'):
            if concept.strip():
                fact = self.fact_tool(concept.strip())
                if not fact.startswith("No facts found"):
                    retrieved_facts.append(fact)
                    
        # Combine all retrieved facts
        combined_facts = "\n\n".join(retrieved_facts) if retrieved_facts else "No relevant facts found."
        
        # Step 3: Generate the final answer
        result = self.answer_generator(
            question=question,
            retrieved_facts=combined_facts
        )
        
        return dspy.Prediction(answer=result.answer)

# 3. Use the pipeline
# Assuming dspy.settings.configure(lm=...) has been called
qa_pipeline = OposumQAPipeline()
response = qa_pipeline(question="What adaptations help opossums survive in urban environments?")
print(f"Answer: {response.answer}")
```

This pipeline:
1. Analyzes the question to extract key concepts
2. Retrieves facts for each concept using our specialized tool
3. Synthesizes the information into a coherent answer

## Branching and Conditional Logic

Pipelines can incorporate branching logic to handle different types of requests or implement fallback strategies:

```python
class SmartOposumPipeline(dspy.Module):
    def __init__(self):
        super().__init__()
        self.classifier = dspy.Predict(QueryClassifier)
        self.factual_pipeline = OposumQAPipeline()
        self.comparison_pipeline = ComparisonPipeline()  # Hypothetical comparison module
        self.default_responder = dspy.ChainOfThought(DefaultResponse)
        
    def forward(self, user_query):
        # Classify the query type
        classification = self.classifier(query=user_query)
        query_type = classification.query_type
        
        # Route to appropriate pipeline based on classification
        if query_type == "factual":
            return self.factual_pipeline(question=user_query)
        elif query_type == "comparison":
            return self.comparison_pipeline(question=user_query)
        else:
            # Handle other query types
            return self.default_responder(question=user_query)
```

This pattern aligns well with Opossum's [model selection](../model-integration/backend-selection.md) architecture, where different query types might be routed to different processing pipelines.

## Pipeline Optimization

Entire pipelines can be optimized just like individual modules. This is one of DSPy's most powerful features, as it allows end-to-end optimization of complex workflows.

```python
import dspy
from dspy.teleprompt import BootstrapFewShot

# Define a pipeline
my_pipeline = OposumQAPipeline()

# Define a metric for the entire pipeline
def pipeline_quality_metric(gold, pred, trace=None):
    # Evaluate end-to-end performance
    # gold.answer is the ground truth
    # pred.answer is the pipeline's prediction
    return quality_score(gold.answer, pred.answer)

# Create an optimizer
teleprompter = BootstrapFewShot(metric=pipeline_quality_metric)

# Optimize the pipeline end-to-end
optimized_pipeline = teleprompter.compile(student=my_pipeline, 
                                          trainset=train_examples,
                                          valset=validation_examples)

# The optimized pipeline can then be saved and used in production
optimized_pipeline.save("./models/optimized_pipeline.dspy")
```

## Persistent Pipelines

Pipelines can be saved and loaded, preserving their optimized state:

```python
# Save an optimized pipeline
optimized_pipeline.save("./models/qa_pipeline_v1.dspy")

# Load the pipeline later
from dspy.utils import load_module
loaded_pipeline = load_module("./models/qa_pipeline_v1.dspy")

# Use the loaded pipeline
result = loaded_pipeline(question="What do opossums eat?")
```

This enables a workflow where pipelines are optimized offline and then deployed to production, aligning with Opossum's design for [API integration](../api/routes.md).

## Integrating with Opossum's Architecture

Within Opossum Search, DSPy pipelines can serve various roles:

-   **Query Processing Pipeline:** Handle user queries with multiple steps (understanding, retrieval, generation)
-   **Content Filtering:** Implement content safety checks and post-processing
-   **Model Fallback Chain:** Implement the fallback logic between different LM providers
-   **SVG Generation:** Process natural language descriptions into structured SVG parameters

Example integration point with Opossum's infrastructure:

```python
from app.core.config import get_settings
from app.core.llm_clients import get_lm_client
from app.tools.fact_checker import OpossumFactTool
import dspy

class OpossumSearchHandler:
    def __init__(self):
        # Configure DSPy with Opossum's LM client
        settings = get_settings()
        lm_client = get_lm_client(settings.preferred_provider)
        dspy.settings.configure(lm=lm_client)
        
        # Load the pre-optimized pipeline
        self.pipeline = dspy.utils.load_module(settings.dspy_pipeline_path)
        
    async def process_query(self, user_query, conversation_context=None):
        try:
            # Process through the DSPy pipeline
            result = self.pipeline(question=user_query, context=conversation_context)
            return {
                "response": result.answer,
                "success": True
            }
        except Exception as e:
            # Implement fallback logic
            logger.error(f"Pipeline error: {e}")
            return {
                "response": "I'm sorry, I encountered an issue processing your request.",
                "success": False
            }
```

## Monitoring and Observability

Integrate DSPy pipeline tracing with Opossum's existing [OpenTelemetry integration](../technical/opentelemetry-integration.md):

```python
from app.telemetry import get_tracer
from opentelemetry import trace

# Create a custom DSPy module that adds telemetry
class TracedModule(dspy.Module):
    def __init__(self, module, name):
        super().__init__()
        self.module = module
        self.name = name
        self.tracer = get_tracer(f"dspy.{name}")
        
    def forward(self, **kwargs):
        with self.tracer.start_as_current_span(self.name) as span:
            # Add request metadata to span
            span.set_attribute("input_keys", str(list(kwargs.keys())))
            
            # Process through the underlying module
            start_time = time.time()
            result = self.module(**kwargs)
            duration = time.time() - start_time
            
            # Add response metadata to span
            span.set_attribute("duration_seconds", duration)
            
            return result
```

## Conclusion

DSPy pipelines provide a powerful framework for orchestrating complex language processing tasks within Opossum Search. By decomposing tasks into well-defined modules with clear interfaces, you can build maintainable, resilient, and optimizable systems that leverage the best capabilities of language models.

As Opossum continues to evolve, these pipeline patterns can help implement increasingly sophisticated features while maintaining code quality and performance. The ability to optimize entire pipelines end-to-end is particularly valuable for maximizing quality while controlling costs.

For more advanced usage, explore the DSPy documentation and consider how these patterns can be combined with Opossum's existing architecture for [system resilience](../technical/resilience-patterns.md) and [observability](../technical/opentelemetry-integration.md).