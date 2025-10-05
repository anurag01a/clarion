# Project C.L.A.R.I.O.N.

**Climate Adaptation and Response Intelligence Operations Network**
[Demo Video](https://youtu.be/BIxeWSOe6A4)

## Project Vision

C.L.A.R.I.O.N. is designed to be a planetary nervous system for climate adaptation. Its purpose is to radically reduce the time-to-help for individuals and communities caught in acute climate disasters by bridging the critical, time-sensitive information gap between a person in danger and the aid that can save them.

## Core Philosophy (First Principles)

Every design decision is guided by these truths of a disaster scenario:

1. **Solve Information Asymmetry**: The user has ground-truth on their immediate peril; the system provides the verified, actionable bigger picture.
2. **Establish Trust Instantly**: In a low-trust, high-chaos environment, our agent must be a source of calm, verified, and authoritative information. All outputs must be transparent about their confidence level.
3. **Optimize for Time**: The primary metric of success is speed. The entire system, from voice recognition to final synthesis, must operate in seconds.

## Product Vision (User Experience)

- **Voice-First Interface**: The primary interaction is through voice. Users navigate to a simple web interface and press a "Start Listening" button.
- **Conversational Interaction**: Users speak their crisis naturally (e.g., "I'm trapped by floodwaters on the Gurdaspur highway," "I see a fire approaching, where do I go?"). The agent responds with a calm, synthesized voice.
- **"Claude-Style" Artifact Sidebar**: The UI features a main chat window for the conversation and a sidebar for "Agent Activity." This sidebar is critical for transparency and shows, in real-time, which agent is active and what task it is performing.

## Technical Architecture

![CLARION Architecture Diagram](architecture_diagram.png)

### Multi-Agent Architecture

CLARION uses a specialized multi-agent system to handle different aspects of emergency response:

1. **Orchestrator Agent**: The main coordinator that handles initial user interactions, analyzes the emergency situation, and delegates tasks to specialized agents.

   - Routes queries to appropriate specialist agents
   - Maintains conversation context across agent transitions
   - Handles general inquiries and emergency triage

2. **Rescue Agent**: Focuses on immediate emergency response coordination.

   - Provides evacuation instructions and safety protocols
   - Helps coordinate rescue efforts and resources
   - Offers first aid and survival guidance

3. **Information Agent**: Provides critical information during emergencies.
   - Delivers weather updates and hazard warnings
   - Searches for emergency contacts and resources
   - Provides verified information about the disaster situation

### System Components

1. **User Interface Layer (Streamlit)**

   - Simple, clean web interface
   - Real-time agent activity sidebar
   - Conversation history display

2. **Voice & App Handler (LiveKit)**

   - Speech-to-Text using Cartesia
   - Text-to-Speech using Cartesia
   - State management through app_state.json

3. **Agentic Core (The Brain)**

   - **Orchestrator Agent**: Routes queries to specialist agents based on intent
   - **Rescue Agent**: Handles life-threatening emergency situations
   - **Resource Agent**: Deep-crawls websites to extract critical contacts with hybrid regex+AI approach
   - **Information Agent**: Provides general information and status updates

4. **External Tools & Data Sources**
   - Exa API for intelligent web searches
   - crawl4ai for content extraction
   - NASA FIRMS API for fire detection
   - Weather.gov API for weather alerts
   - Mock Rescue API (conceptual integration with emergency services)

### Technology Stack

- **AI Inference**: Cerebras Cloud SDK (featuring Meta's Llama models)
- **Voice Processing**: LiveKit with Cartesia plugins for STT/TTS
- **Web UI**: Streamlit
- **Web Crawling**: crawl4ai
- **Search**: Exa-py
- **External APIs**: Requests library
- **Containerization**: Docker MCP Gateway (conceptually)

## Installation

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/clarion.git
   cd clarion
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Configure API keys:

   Option 1: Create a `.env` file in the project root (recommended):

   ```
   # Copy from .env.template
   cp .env.template .env
   # Then edit the .env file with your actual API keys
   ```

   Option 2: Set environment variables directly:

   ```
   # On Windows
   setx EXA_API_KEY "your_exa_api_key"
   setx CEREBRAS_API_KEY "your_cerebras_api_key"
   setx CARTESIA_API_KEY "your_cartesia_api_key"
   setx NASA_API_KEY "your_nasa_api_key"

   # On Linux/Mac
   export EXA_API_KEY="your_exa_api_key"
   export CEREBRAS_API_KEY="your_cerebras_api_key"
   export CARTESIA_API_KEY="your_cartesia_api_key"
   export NASA_API_KEY="your_nasa_api_key"
   ```

   Note: The system will work with simulated responses if these APIs aren't available, but for production use, you'll want to configure them properly.

## Running the Application

1. Start the Streamlit UI:

   ```
   streamlit run streamlit_app.py
   ```

2. In a separate terminal, start the LiveKit agent handler:

   ```
   python livekit_agent_handler.py
   ```

3. Navigate to the provided local URL (typically http://localhost:8501) in your web browser.

4. Click the "Start Listening" button and speak your emergency scenario.

## Demo Scenario

For demonstration purposes, try the following scenario:

"Help, I'm stuck in a flood on the Gurdaspur highway in Punjab!"

The system will:

1. Classify this as a rescue intent
2. Extract the location and verify the flood with weather APIs
3. Find local emergency contacts
4. Provide a detailed safety response with actionable instructions

## Development

This project uses a modular design where each agent is implemented as a separate Python module. The key files are:

- `streamlit_app.py`: The user interface
- `livekit_agent_handler.py`: The voice processing and agent orchestration
- `agents/orchestrator.py`: The main router for user queries
- `agents/rescue_agent.py`: Handles life-threatening situations
- `agents/resource_agent.py`: Extracts contact information
- `agents/information_agent.py`: Provides general information

## Enhanced C.L.A.R.I.O.N. Agent System

The C.L.A.R.I.O.N. system has been enhanced with advanced contact extraction and web crawling capabilities from the Jupyter notebook integration. Here's a summary of the enhancements:

### 1. Resource Agent Enhancements

The resource agent now features:

- Advanced hybrid contact extraction using both regex patterns and AI
- Asynchronous multi-URL crawling with parallel processing
- Improved contact categorization (emergency phones, standard phones, emails, addresses)
- Better error handling and real API integration

### 2. Rescue Agent Enhancements

The rescue agent now:

- Uses a more sophisticated triage process that integrates multiple data sources
- Incorporates the enhanced resource agent for better contact discovery
- Generates more detailed safety warnings with actionable information
- Provides a structured JSON response that's easy to process

### 3. Information Agent Enhancements

The information agent now:

- Uses the enhanced web search capabilities
- Provides more detailed and organized responses
- Integrates better with external API sources

### 4. Orchestrator Updates

The orchestrator has been updated to:

- Work seamlessly with the enhanced specialist agents
- Provide better intent classification
- Handle more complex queries

### 5. Centralized Environment Configuration

The system now features a centralized environment configuration:

- All API keys are managed through a single module (`utils/env_config.py`)
- Support for loading keys from `.env` file or environment variables
- Graceful degradation when keys are missing
- Unified warning messages for missing dependencies

## Limitations and Future Work

Even with these enhancements, some components remain simulated:

1. Some Cerebras API calls are simulated where API keys are unavailable
2. Some weather and other APIs return simulated data
3. Direct integration with emergency services is conceptual

Future work would focus on:

- Deploying with full API integrations
- Adding multi-language support
- Establishing secure connections to emergency services through Docker MCP Gateway
- Expanding the range of crisis types the system can handle

## Acknowledgments

This project demonstrates the integration of several key technologies:

- **Cerebras**: Powering all reasoning, analysis, and synthesis
- **Meta (Llama)**: Providing the foundational LLM capabilities
- **Docker**: Conceptual architecture for secure tool integrations
