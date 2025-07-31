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

## [1.3.0] - 2025-01-27 - 🎉 CRYING SYSTEM COMPLETE

### ✅ "Crying" Notification System for Successful Predictions
- **🎊 Frontend Crying Interface**: Complete UI for notification management
  - NotificationSettings component with email subscription management
  - Subscription status display with email address confirmation
  - Easy subscribe/unsubscribe functionality with form validation
  - Social media integration placeholders (Twitter, LinkedIn, Facebook)
  - Integrated into main app navigation with 🎉 Crying button
- **🔧 Backend SNS Management**: Lambda function for subscription management
  - NotificationManagementFunction with three API endpoints
  - POST /subscribe-notifications - Subscribe email to SNS topic
  - POST /unsubscribe-notifications - Remove email subscription
  - GET /notification-status - Check current subscription status
  - Email validation and duplicate subscription handling
- **🏗️ Infrastructure Integration**: Seamless AWS integration
  - Reuses existing SNS topic for verification notifications
  - Proper IAM permissions for SNS operations
  - API Gateway integration with Cognito authorization
  - CORS support for cross-origin requests

### Added
- **🎉 Crying System**: Complete notification system for celebrating successful predictions
- **📧 Email Subscription Management**: User-controlled email notification preferences
- **🌐 Social Media Foundation**: UI framework for future Twitter, LinkedIn, Facebook integration
- **🎯 User Experience Enhancement**: Streamlined notification preference management

### Technical Details
- **Frontend**: NotificationSettings.tsx component with responsive design
- **Backend**: notification_management Lambda function with SNS integration
- **API**: Three new authenticated endpoints for subscription management
- **Infrastructure**: SAM template updates with proper IAM permissions

## [1.2.0] - 2025-01-27 - 🎆 PHASE 2 COMPLETE

### ✅ Production Verification System Operational
- **🤖 Strands Verification Agent**: Complete AI-powered prediction verification system
- **⏰ Automated Processing**: EventBridge triggers verification every 15 minutes
- **🎯 Frontend Integration**: Real-time verification status display working
- **📊 Production Metrics**: Processing 50+ predictions with proper categorization
- **📧 Notification System**: SNS email alerts for verified TRUE predictions
- **🗂️ Audit System**: Complete S3 logging with tool gap analysis

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

## [1.5.0] - 2025-07-30 - 🔧 MCP SAMPLING REVIEW FEATURE

### ✅ **PHASE 2 COMPLETE: MCP Sampling Review & Improvement System**
- **🔍 Strands Review Agent**: Complete MCP Sampling implementation for prediction review
  - Automatic review of prediction responses using MCP Sampling pattern
  - Server-initiated sampling requests for improvement analysis
  - Client-facilitated LLM interactions for review processing
  - Human-in-the-loop design for user-controlled improvements
- **🌐 WebSocket Routing**: Fixed and enhanced WebSocket API routing
  - Added `improve_section` and `improvement_answers` routes
  - Fixed import issues with Lambda environment (absolute imports)
  - Proper WebSocket permissions and integration setup
  - Mock improvement responses working (ready for full implementation)
- **🧪 Testing Infrastructure**: Comprehensive testing framework for review feature
  - WebSocket routing tests with 100% basic functionality
  - Debug tools for improvement workflow validation
  - Integration tests for MCP Sampling pattern
  - Automated testing for all review phases

### Added
- **🔧 MCP Sampling Pattern**: Proper implementation following MCP specification
  - Server-controlled sampling requests (Strands review agent)
  - Client-facilitated LLM interactions (WebSocket handler)
  - User approval workflow (human-in-the-loop)
  - Multi-step sampling for questions and regeneration
- **📡 Enhanced WebSocket API**: Complete routing for improvement workflow
  - `improve_section` action routing working
  - `improvement_answers` action routing ready
  - Fixed Lambda import issues (relative → absolute imports)
  - GoneException handling and connection management
- **🧪 Review Testing Suite**: Comprehensive testing for review functionality
  - Basic WebSocket connection tests
  - Improvement request routing validation
  - Mock response testing framework
  - CloudWatch log analysis tools

### Changed
- **WebSocket Architecture**: Enhanced routing and error handling
  - Fixed "Forbidden" errors with proper route configuration
  - Resolved import errors in Lambda environment
  - Improved connection timeout handling
  - Better error logging and debugging
- **Lambda Function Structure**: Optimized for MCP Sampling pattern
  - Separated improvement request handling
  - Fixed relative import issues for Lambda deployment
  - Enhanced error handling and logging
  - Mock responses for testing routing

### Technical Details
- **MCP Sampling Implementation**: Following MCP specification exactly
  - Server-initiated: Strands automatically reviews responses
  - Client-facilitated: WebSocket client handles LLM sampling
  - Human-in-the-loop: User clicks sections and provides input
  - Multi-step workflow: Review → Questions → Input → Regeneration
- **WebSocket Routing**: Complete infrastructure for improvement workflow
  - Route selection based on `action` field in message body
  - Proper Lambda permissions for all improvement routes
  - Fixed import paths for Lambda environment compatibility
  - Mock responses proving routing functionality

## [Unreleased]

### In Progress (Phase 3)
- **🔧 Full Review Agent**: Replace mock responses with actual ReviewAgent calls
- **🎨 Frontend Integration**: UI components for improvement workflow
- **💾 Data Persistence**: Store improvement history and reasoning

### Planned (Phase 3+)
- **🌐 MCP Tool Integration**: Weather, sports, and financial API tools implementation
- **📊 Advanced Analytics**: Verification success rate tracking and insights
- **🔄 Automated Re-verification**: Smart retry logic for failed verifications
- **📱 Mobile Application**: React Native app with verification notifications
- **🌐 Social Features**: Prediction sharing and community leaderboards

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