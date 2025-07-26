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

## [1.1.0] - 2025-01-27

### Added
- **🤖 Strands Verification Agent**: Complete AI-powered prediction verification system
  - Intelligent routing based on verifiability categories
  - Agent verifiable: Pure reasoning and established knowledge
  - Current tool verifiable: Time-based verification with `current_time` tool
  - Strands tool verifiable: Mathematical calculations and computations
  - API tool verifiable: Tool gap detection with MCP suggestions
  - Human verifiable only: Appropriate inconclusive marking
- **🔧 Tool Gap Detection System**: Automatic identification of missing verification capabilities
  - MCP tool suggestions (mcp-weather, mcp-espn, mcp-yahoo-finance)
  - Priority-based tool development roadmap (HIGH/MEDIUM/LOW)
  - Detailed specifications for custom tool development
  - Intelligent categorization of prediction requirements
- **📊 Complete Verification Pipeline**: End-to-end automated verification workflow
  - DynamoDB scanner for pending predictions
  - S3 logging for audit trails and tool gap analysis
  - Email notifications for verified TRUE predictions with HTML formatting
  - Status updates in DynamoDB with confidence scores and processing metrics
  - Batch processing with comprehensive statistics and error handling
- **🧪 Comprehensive Testing Framework**: Mock Strands agents for development
  - Complete integration tests for all verification categories
  - Tool gap detection validation
  - Email notification testing with HTML templates
  - S3 logging verification with structured JSON format

### Changed
- **Data Modernization**: Updated 41 legacy predictions to current data structure
  - Added `verifiable_category` field with intelligent categorization
  - Added `category_reasoning` with AI explanations
  - Fixed verification date formats and added proper ISO timestamps
  - Added `prediction_date` and `date_reasoning` fields
- **Database Schema**: Enhanced DynamoDB structure for verification tracking
  - Added verification status fields (`verification_status`, `verification_confidence`)
  - Added tool gap information storage
  - Added processing metrics and agent reasoning storage
  - Fixed Decimal type support for confidence scores

### Technical Details
- **Phase 1 Implementation**: Manual verification script with complete pipeline
- **Verification Categories**: 5-category system with intelligent routing
- **Tool Gap Analysis**: Automatic MCP tool suggestion system
- **S3 Logging**: Structured audit trails with tool gap summaries
- **Email System**: HTML notifications with agent reasoning details
- **Mock Framework**: Testing support without full Strands installation

## [Unreleased]

### Planned (Phase 2)
- **🚀 Lambda Deployment**: Serverless verification execution
- **⏰ EventBridge Scheduling**: Automated cron-based verification runs
- **📧 SNS Integration**: Reliable notification delivery system
- **🌐 Enhanced MCP Tools**: Weather, sports, and financial API integrations
- **📊 Verification Analytics**: Tool gap analysis and success rate tracking

---

## Version History Summary

- **v1.1.0**: Complete Strands verification system with tool gap detection (Phase 1)
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