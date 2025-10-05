# C.L.A.R.I.O.N. - Climate Location & Adversity Response Integrated Operational Network

![CLARION Status](https://img.shields.io/badge/status-development-yellow)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)

## Introduction

C.L.A.R.I.O.N. (Climate Location & Adversity Response Integrated Operational Network) is an advanced emergency response system designed to provide rapid, accurate assistance during climate disasters and emergencies. The system uses a specialized multi-agent architecture with both AI-powered and local fallback capabilities to ensure reliable operation in all environments.

## Core Philosophy

Every design decision is guided by these fundamental principles:

1. **Solve Information Asymmetry**: Bridge the gap between a person's immediate situation and the broader emergency response landscape.
2. **Establish Trust Instantly**: Provide calm, verified, and authoritative information with transparent confidence levels.
3. **Optimize for Time**: Minimize the time between a request for help and the delivery of actionable information.

## Key Features

- **Multi-Agent Architecture**: Specialized agents handle different aspects of emergency response
- **Robust Fallback Mechanisms**: System remains functional even when external APIs are unavailable
- **Hybrid Contact Extraction**: Combined regex and AI approach for finding emergency contacts
- **Asynchronous Processing**: Parallel information gathering for faster responses
- **Transparent Operation**: Real-time activity tracking of each agent's operations

## System Architecture

### Multi-Agent System

The C.L.A.R.I.O.N. system is built on a specialized multi-agent architecture:

1. **Orchestrator Agent**: Central coordinator that routes queries to specialized agents based on intent classification.
2. **Rescue Agent**: Handles emergency evacuation and safety instructions for life-threatening situations.
3. **Information Agent**: Provides general emergency information, weather updates, and evacuation routes.
4. **Resource Agent**: Extracts emergency contact information from web sources using a hybrid approach.

### Local Fallback System

The system includes comprehensive local fallback mechanisms for when external APIs are unavailable:

- **Local Emergency Contacts**: Predefined emergency contacts by region
- **Local Safety Instructions**: Emergency-type specific safety guidance
- **Pattern-Based Processing**: Intent classification and information extraction without AI

## Documentation

For detailed information about the system architecture and implementation, please refer to these documentation files:

- [System Architecture](./docs/system_architecture.md): Comprehensive overview of the system design
- [File Reference](./docs/file_reference.md): Detailed breakdown of each file in the codebase
- [Multi-Agent Architecture](./docs/multi_agent_architecture.md): Technical guide to the multi-agent system
- [Enhanced Resource Agent](./docs/enhanced_resource_agent.md): Documentation for the advanced contact extraction capabilities
- [Integration Guide](./docs/integration_guide.md): Guide for integrating new components with the system

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/clarion.git
   cd clarion
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   Alternatively, use the installation script:

   ```bash
   python install_dependencies.py
   ```

3. Configure API keys:

   Option 1: Create a `.env` file in the project root (recommended):

   ```bash
   # Copy from .env.template
   cp .env.template .env
   # Then edit the .env file with your actual API keys
   ```

   Option 2: Set environment variables directly:

   ```bash
   # On Windows
   setx CEREBRAS_API_KEY "your_cerebras_api_key"
   setx EXA_API_KEY "your_exa_api_key"
   setx CARTESIA_API_KEY "your_cartesia_api_key"
   setx NASA_API_KEY "your_nasa_api_key"

   # On Linux/Mac
   export CEREBRAS_API_KEY="your_cerebras_api_key"
   export EXA_API_KEY="your_exa_api_key"
   export CARTESIA_API_KEY="your_cartesia_api_key"
   export NASA_API_KEY="your_nasa_api_key"
   ```

## Running the Application

### Standard Operation

1. Start the Streamlit UI:

   ```bash
   streamlit run streamlit_app.py
   ```

2. For voice integration, start the LiveKit agent handler in a separate terminal:

   ```bash
   python livekit_agent_handler.py
   ```

3. Navigate to the provided local URL (typically http://localhost:8501) in your web browser.

### Testing Mode

For testing without external API dependencies:

```bash
python run_system_test.py
```

This will run through predefined test scenarios with the local fallback system.

## Development

### File Structure

```
clarion/
├── agents/                       # Agent implementation files
│   ├── orchestrator.py           # Main query router
│   ├── rescue_agent.py           # Emergency response agent
│   ├── information_agent.py      # Information provider agent
│   └── resource_agent.py         # Contact extraction agent
├── utils/                        # Utility modules
│   ├── ai_helpers.py             # AI API interaction helpers
│   ├── env_config.py             # Environment configuration
│   └── ssl_fix.py                # SSL configuration utilities
├── docs/                         # Documentation files
│   ├── system_architecture.md    # System architecture documentation
│   ├── file_reference.md         # File-by-file reference
│   ├── multi_agent_architecture.md # Technical guide to multi-agent system
│   ├── enhanced_resource_agent.md # Resource agent documentation
│   └── integration_guide.md      # Integration guide
├── .env.template                 # Template for environment variables
├── requirements.txt              # Python dependencies
├── run_streamlit_simple.py       # Simplified Streamlit UI
├── run_system_test.py            # System test with local fallbacks
└── README.md                     # This file
```

### Testing

The project includes several test files for different components:

- `test_orchestrator.py`: Tests the orchestrator agent's query routing
- `test_ui_flow.py`: Tests UI flow using Streamlit
- `run_system_test.py`: End-to-end system test with local fallbacks

## Demo Scenarios

For demonstration purposes, try the following scenarios:

1. **Rescue Scenario**: "Help, I'm stuck in a flood on the Gurdaspur highway in Punjab!"
2. **Information Scenario**: "What should I do during a hurricane in Miami?"
3. **Resource Scenario**: "I need emergency contact numbers for wildfire help in California"

## Enhanced Features

Recent enhancements to the C.L.A.R.I.O.N. system include:

### 1. Advanced Contact Extraction

- Hybrid regex/AI approach for extracting contacts from websites
- Better categorization of emergency vs. standard contacts
- Asynchronous multi-URL crawling for faster results

### 2. Local Fallback System

- Pattern-matching and rule-based alternatives when APIs fail
- Predefined emergency contacts and safety instructions by region
- Graceful degradation of functionality in offline environments

### 3. Streamlined User Interface

- Real-time agent activity tracking
- Structured response formatting for better readability
- Support for voice interaction through LiveKit integration

## Limitations and Future Work

Current limitations of the system include:

1. Some Cerebras API calls are simulated where API keys are unavailable
2. Weather and other APIs return simulated data in many cases
3. Direct integration with emergency services is conceptual

Future work would focus on:

- Deploying with full API integrations
- Adding multi-language support
- Establishing secure connections to emergency services
- Expanding the range of crisis types the system can handle

## License

[MIT License](LICENSE)

## Acknowledgments

This project demonstrates the integration of several key technologies:

- **Cerebras**: Powering all reasoning, analysis, and synthesis
- **Meta (Llama)**: Providing the foundational LLM capabilities
- **Exa**: Intelligent web search capabilities
