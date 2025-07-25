# Technical Requirements Document (TRD)
## CalledIt: Serverless Prediction Verification Platform

**Document Version:** 1.0  
**Date:** January 27, 2025  
**Status:** Active

---

## 1. Executive Summary

CalledIt is a serverless web application that converts natural language predictions into structured, verifiable formats using AI agents. The system automatically categorizes predictions by verifiability type and provides real-time streaming feedback during processing.

### 1.1 Project Goals
- Convert natural language predictions to structured verification formats
- Classify predictions by verifiability methodology (5 categories)
- Provide real-time AI processing feedback via streaming
- Enable future automated verification of predictions

### 1.2 Success Criteria
- ✅ 100% prediction categorization accuracy across 5 verifiability types
- ✅ Real-time streaming response under 60 seconds
- ✅ Serverless architecture with automatic scaling
- ✅ Secure user authentication and data isolation

---

## 2. Functional Requirements

### 2.1 Core Features

#### 2.1.1 Prediction Processing
- **FR-001**: System SHALL accept natural language predictions via web interface
- **FR-002**: System SHALL process predictions using Strands AI agents
- **FR-003**: System SHALL categorize predictions into exactly one of 5 verifiability categories:
  - `agent_verifiable`: Pure reasoning/knowledge
  - `current_tool_verifiable`: Current time tool only
  - `strands_tool_verifiable`: Strands library tools
  - `api_tool_verifiable`: External API calls required
  - `human_verifiable_only`: Human observation required
- **FR-004**: System SHALL provide reasoning for category selection
- **FR-005**: System SHALL generate structured verification methods with sources, criteria, and steps

#### 2.1.2 Real-time Streaming
- **FR-006**: System SHALL provide real-time streaming feedback during prediction processing
- **FR-007**: System SHALL stream text chunks, tool usage, and status updates
- **FR-008**: System SHALL complete streaming within 60 seconds or timeout gracefully

#### 2.1.3 Data Management
- **FR-009**: System SHALL persist predictions with verifiability categories to DynamoDB
- **FR-010**: System SHALL retrieve user's historical predictions
- **FR-011**: System SHALL maintain data isolation between users

#### 2.1.4 User Interface
- **FR-012**: System SHALL provide responsive web interface for prediction creation
- **FR-013**: System SHALL display verifiability categories with visual indicators
- **FR-014**: System SHALL show real-time processing feedback
- **FR-015**: System SHALL list user's saved predictions with categories

### 2.2 Authentication & Authorization
- **FR-016**: System SHALL authenticate users via AWS Cognito
- **FR-017**: System SHALL support OAuth 2.0 flows
- **FR-018**: System SHALL authorize API access using JWT tokens
- **FR-019**: System SHALL provide secure logout functionality

---

## 3. Non-Functional Requirements

### 3.1 Performance
- **NFR-001**: Prediction processing SHALL complete within 60 seconds
- **NFR-002**: WebSocket connections SHALL timeout after 5 minutes of inactivity
- **NFR-003**: REST API responses SHALL return within 5 seconds
- **NFR-004**: System SHALL support concurrent users without performance degradation

### 3.2 Scalability
- **NFR-005**: System SHALL automatically scale Lambda functions based on demand
- **NFR-006**: System SHALL handle up to 1000 concurrent WebSocket connections
- **NFR-007**: DynamoDB SHALL scale read/write capacity automatically

### 3.3 Reliability
- **NFR-008**: System SHALL maintain 99.9% uptime
- **NFR-009**: System SHALL implement graceful error handling and fallbacks
- **NFR-010**: System SHALL validate all inputs and provide meaningful error messages
- **NFR-011**: System SHALL implement retry logic for transient failures

### 3.4 Security
- **NFR-012**: System SHALL encrypt data in transit using TLS 1.2+
- **NFR-013**: System SHALL encrypt data at rest in DynamoDB
- **NFR-014**: System SHALL implement CORS policies for web security
- **NFR-015**: System SHALL validate and sanitize all user inputs
- **NFR-016**: System SHALL not log sensitive user data

### 3.5 Maintainability
- **NFR-017**: System SHALL use Infrastructure as Code (AWS SAM)
- **NFR-018**: System SHALL implement comprehensive logging
- **NFR-019**: System SHALL provide monitoring and alerting capabilities
- **NFR-020**: System SHALL maintain 90%+ test coverage

---

## 4. Technical Architecture

### 4.1 System Architecture
- **Serverless Architecture**: AWS Lambda + API Gateway + DynamoDB
- **Real-time Communication**: WebSocket API for streaming
- **AI Processing**: Strands agents with Amazon Bedrock
- **Frontend**: React + TypeScript + Vite
- **Authentication**: AWS Cognito User Pools

### 4.2 Data Flow
```
User Input → WebSocket API → Lambda (Strands Agent) → Bedrock → Real-time Stream
                          ↓
                    REST API → Lambda → DynamoDB → User Interface
```

### 4.3 Technology Stack

#### Backend
- **Runtime**: Python 3.12
- **Framework**: AWS SAM (Serverless Application Model)
- **AI**: Strands agents + Amazon Bedrock
- **Database**: Amazon DynamoDB
- **Authentication**: AWS Cognito
- **APIs**: AWS API Gateway (REST + WebSocket)

#### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: CSS3 with responsive design
- **HTTP Client**: Axios
- **WebSocket**: Native WebSocket API

### 4.4 AWS Services
- **AWS Lambda**: Serverless compute
- **Amazon API Gateway**: REST and WebSocket APIs
- **Amazon DynamoDB**: NoSQL database
- **AWS Cognito**: User authentication
- **Amazon Bedrock**: AI/ML services
- **AWS CloudFormation**: Infrastructure deployment

---

## 5. Data Requirements

### 5.1 Data Models

#### Prediction/Call Object
```json
{
  "PK": "USER:{user_id}",
  "SK": "PREDICTION#{timestamp}",
  "prediction_statement": "string",
  "verification_date": "ISO 8601 UTC",
  "verifiable_category": "enum[5 categories]",
  "category_reasoning": "string",
  "verification_method": {
    "source": ["array of strings"],
    "criteria": ["array of strings"],
    "steps": ["array of strings"]
  },
  "initial_status": "pending",
  "createdAt": "ISO 8601 UTC",
  "updatedAt": "ISO 8601 UTC"
}
```

### 5.2 Data Storage
- **Primary Database**: DynamoDB with user-based partitioning
- **Backup Strategy**: DynamoDB Point-in-Time Recovery
- **Data Retention**: Indefinite (user-controlled deletion)

---

## 6. Integration Requirements

### 6.1 External Dependencies
- **Strands Agents Library**: AI orchestration framework
- **Amazon Bedrock**: AI reasoning models
- **AWS Services**: Core infrastructure services

### 6.2 API Integrations
- **Strands Tools**: current_time, calculator, python_repl
- **Future APIs**: External verification services (planned)

---

## 7. Testing Requirements

### 7.1 Test Coverage
- **Unit Tests**: Backend Lambda functions
- **Integration Tests**: API endpoints and WebSocket flows
- **End-to-End Tests**: Complete user workflows
- **Automated Tests**: Verifiability categorization accuracy

### 7.2 Test Automation
- **Continuous Testing**: Automated test suite for verifiability categories
- **Performance Testing**: Load testing for concurrent users
- **Security Testing**: Penetration testing and vulnerability scanning

---

## 8. Deployment Requirements

### 8.1 Environment Strategy
- **Development**: Local development with SAM local
- **Production**: AWS cloud deployment via SAM CLI
- **CI/CD**: Manual deployment (automated pipeline planned)

### 8.2 Infrastructure as Code
- **Template**: AWS SAM template.yaml
- **Configuration**: Environment-specific parameters
- **Deployment**: Single-command deployment via SAM CLI

---

## 9. Monitoring & Observability

### 9.1 Logging
- **Application Logs**: CloudWatch Logs for all Lambda functions
- **Access Logs**: API Gateway access logging
- **Error Tracking**: Structured error logging with context

### 9.2 Metrics
- **Performance Metrics**: Response times, throughput
- **Business Metrics**: Prediction counts, category distribution
- **System Metrics**: Lambda invocations, DynamoDB usage

### 9.3 Alerting
- **Error Alerts**: High error rates or critical failures
- **Performance Alerts**: Response time degradation
- **Capacity Alerts**: Resource utilization thresholds

---

## 10. Compliance & Governance

### 10.1 Data Privacy
- **User Data**: Stored securely with user consent
- **Data Access**: User-controlled data access and deletion
- **Data Sharing**: No third-party data sharing

### 10.2 Security Standards
- **AWS Security**: Following AWS Well-Architected Framework
- **Encryption**: TLS in transit, encryption at rest
- **Access Control**: Principle of least privilege

---

## 11. Future Considerations

### 11.1 Planned Enhancements
- **Automated Verification**: External API integration for prediction verification
- **Analytics Dashboard**: User statistics and accuracy tracking
- **Mobile Application**: React Native mobile app
- **Social Features**: Prediction sharing and leaderboards

### 11.2 Scalability Planning
- **Global Deployment**: Multi-region deployment strategy
- **Performance Optimization**: Caching and CDN integration
- **Advanced AI**: Enhanced prediction analysis capabilities

---

## 12. Acceptance Criteria

### 12.1 System Acceptance
- ✅ All functional requirements implemented and tested
- ✅ Non-functional requirements met and verified
- ✅ Security requirements validated
- ✅ Performance benchmarks achieved

### 12.2 User Acceptance
- ✅ Intuitive user interface with positive user feedback
- ✅ Reliable prediction processing with accurate categorization
- ✅ Real-time streaming provides immediate value
- ✅ System meets user expectations for speed and accuracy

---

**Document Control:**
- **Author**: Development Team
- **Reviewers**: Technical Lead, Product Owner
- **Approval**: Project Stakeholders
- **Next Review**: February 27, 2025