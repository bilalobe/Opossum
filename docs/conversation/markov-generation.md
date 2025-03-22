# Markov Chain Text Generation

The Markov chain text generation system is used specifically for creating ambient background text in the UI, combining opossum facts with technical terminology. This is not part of the actual conversation system but rather provides an engaging visual element.

## Implementation

### Text Sources

The system uses two distinct text corpora:

```python
# Opossum-related text corpus
OPOSSUM_TEXTS = [
    """The Virginia opossum is the only marsupial found north of Mexico...""",
    """Opossums have 50 teeth, more than any other North American land mammal...""",
    # Additional opossum facts...
]

# Technical/AI text corpus
TECH_TEXTS = [
    """Natural language processing (NLP) is a field of artificial intelligence...""",
    """Machine learning models learn from data, identify patterns...""",
    # Additional technical content...
]
```

## Generation Process

### Model Creation

```python
def _get_markov_models():
    """Initialize and cache Markov models."""
    global _opossum_model, _tech_model, _combined_model
    
    if (_opossum_model is None):
        _opossum_model = markovify.Text(" ".join(OPOSSUM_TEXTS), state_size=2)
        _tech_model = markovify.Text(" ".join(TECH_TEXTS), state_size=2)
        _combined_model = markovify.combine([_opossum_model, _tech_model], [1.5, 1])
```

### Text Generation Methods

1. **Pure Opossum Text**
   - Uses opossum-only Markov chain
   - Generates nature-focused content
   - Maintains factual accuracy

2. **Combined Tech-Opossum**
   - Merges both models
   - Creates unique hybrid content
   - Weights opossum content higher (1.5:1)

3. **Tech with Opossum Terms**
   - Injects opossum terminology into tech text
   - Creates amusing technical-sounding content
   - Maintains readability

## Emoji Integration

The system incorporates emojis into the generated text:

```python
EMOJI_CATEGORIES = [
    'animal',
    'nature',
    'science',
    'computer',
    'office',
    'technical_symbol'
]
```

### Special Event: Opossum National Day

On October 18th, the system switches to opossum-specific emojis:

```python
opossum_emojis = [
    "🦝",  # Closest to opossum
    "🌙",  # Nocturnal
    "🌳",  # Habitat
    "🍃",  # Nature
    "🐾",  # Paw prints
    "🌿",  # Forest
    "🦊",  # Another marsupial-like emoji
    "🌑",  # Night time
    "🌴",  # Trees
    "🪨"   # Habitat
]
```

## Technical Enhancements

### Line Generation Types

1. **Pure Markov Chain**
```python
line = opossum_model.make_short_sentence(80)
```

2. **Combined Model**
```python
line = combined_model.make_short_sentence(100)
```

3. **Technical Mashup**
```python
term1 = random.choice(opossum_terms)
term2 = random.choice(tech_terms)
patterns = [
    f"The {term1} exhibits properties similar to {term2}",
    f"{term2} analysis of {term1} reveals interesting patterns"
]
```

### Visual Formatting

The system adds technical-looking prefixes:
```python
prefixes = [
    f"[ANALYSIS-{random.randint(100, 999)}]",
    f"<opossum-token-{random.randint(1000, 9999)}>",
    f"// TOKEN_{random.randint(10000, 99999)}:",
    f"/* {random.choice(['DEBUG', 'INFO', 'TRACE'])}: */",
]
```

## Usage Example

```python
# Generate background text
gibberish_text = _generate_nlp_gibberish(num_lines=25)

# Example output:
# [ANALYSIS-247] The opossum's prehensile tail demonstrates neural network adaptability 🦝
# <opossum-token-4891> Analyzing marsupial behavior through transformer architecture 🔬
# /* DEBUG */ Virginia opossum embeddings show remarkable feature extraction 🧪
```

## Configuration

- Line generation: 10-100 lines per request
- Emoji probability: 70% per line
- Technical prefix probability: 30% per line
- Model state size: 2 (for coherent sentence structure)
- Opossum:Tech weight ratio: 1.5:1
