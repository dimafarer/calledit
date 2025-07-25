# Changelog

All notable changes to the CalledIt project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-27

### Added
- **Verifiability Categorization System**: Complete 5-category classification system for predictions
  - 🧠 `agent_verifiable` - Pure reasoning/knowledge verification
  - ⏰ `current_tool_verifiable` - Current time tool verification  
  - 🔧 `strands_tool_verifiable` - Strands library tools verification
  - 🌐 `api_tool_verifiable` - External API verification
  - 👤 `human_verifiable_only` - Human observation verification
- **Automated Testing Suite**: Comprehensive tests for all verifiability categories with 100% success rate
- **Enhanced UI Display**: Visual category badges with icons, colors, and reasoning explanations
- **DynamoDB Persistence**: Complete storage of verifiability categories and reasoning
- **TypeScript Type Updates**: Updated interfaces to use "call" terminology matching app branding

### Changed
- **Agent System Prompt**: Enhanced Strands agent with verifiability categorization logic
- **Response Processing**: Added validation and fallback handling for category classification
- **Frontend Components**: Updated StreamingCall and ListPredictions to display categories
- **Data Model**: Extended prediction/call objects with `verifiable_category` and `category_reasoning` fields

### Technical Details
- **Backend**: Updated `strands_make_call_stream.py` with 5-category classification
- **Frontend**: Enhanced UI components with category display functions
- **Database**: Extended DynamoDB schema to persist verifiability data
- **Testing**: Added WebSocket-based automated testing framework

## [0.9.0] - 2025-01-26

### Added
- **Real-time WebSocket Streaming**: Live prediction processing with immediate user feedback
- **Strands Agent Integration**: AI orchestration between reasoning models and tools
- **Timezone Intelligence**: Automatic timezone handling and 12/24-hour time conversion
- **Enhanced Prediction Processing**: Structured verification method generation

### Changed
- **Architecture**: Migrated from simple REST API to WebSocket streaming architecture
- **AI Processing**: Replaced direct Bedrock calls with Strands agent orchestration
- **User Experience**: Added real-time streaming feedback during prediction processing

### Technical Details
- **WebSocket API**: Added AWS API Gateway WebSocket support
- **Lambda Functions**: Created streaming-capable Lambda functions
- **Frontend**: Implemented WebSocket client for real-time communication

## [0.8.0] - 2025-01-25

### Added
- **Core Prediction System**: Basic prediction creation and storage
- **AWS Serverless Architecture**: Complete serverless backend infrastructure
- **User Authentication**: AWS Cognito integration with OAuth flows
- **Data Persistence**: DynamoDB storage for predictions and user data
- **React Frontend**: TypeScript-based responsive user interface

### Technical Details
- **Backend**: AWS SAM template with Lambda functions
- **Frontend**: React + TypeScript + Vite development stack
- **Authentication**: Cognito User Pool with hosted UI
- **Database**: DynamoDB with user-based data partitioning

## [Unreleased]

### Planned
- **Verification Automation**: Automated verification of predictions using external APIs
- **Prediction Analytics**: User statistics and accuracy tracking
- **Social Features**: Prediction sharing and leaderboards
- **Mobile App**: React Native mobile application
- **Advanced AI**: Enhanced prediction analysis and suggestions

---

## Version History Summary

- **v1.0.0**: Verifiability categorization system with automated testing
- **v0.9.0**: Real-time streaming and Strands agent integration  
- **v0.8.0**: Core serverless prediction platform
- **v0.7.0 and earlier**: Initial development and prototyping

## Contributing

When adding entries to this changelog:
1. Add new entries under `[Unreleased]` section
2. Use semantic versioning for releases
3. Group changes by type: Added, Changed, Deprecated, Removed, Fixed, Security
4. Include technical details for significant changes
5. Move unreleased changes to versioned sections upon release