# CF2 — Protecting Data Using AWS
## Practice Question Set (27 Questions)

> **Domains covered**
> 1.0 — Data classification and data perimeters (9 Qs)
> 2.0 — Encrypting data at rest and in transit (10 Qs)
> 3.0 — AWS incident response (8 Qs)
>
> Questions are interspersed across domains. Four answer options per question; correct answers are distributed evenly across A-D with no letter repeating three times in a row.

---

### Question 1
**Domain 1.0** — A security team is analyzing the AWS security controls that must be in place for a new application. The team has recommended that a data classification approach be used to help determine the security requirements. What should the security team consider for the purposes of their analysis? (Select the BEST answer.)

A) The team should estimate how much storage will be needed and recommend the most cost-effective storage services  
B) The team should consider whether there are any contractual obligations that must be met for the type of data that the application will use  
C) The team should focus exclusively on the database engine types that will be used  
D) The team should determine the number of AWS Regions the application will be deployed to

<br><br><br><br>

**Correct Answer: B**
Data classification involves identifying data types, determining sensitivity, and assessing the potential impact of compromise, loss, or misuse. Contractual obligations, such as PCI DSS compliance, directly affect how data must be classified and protected.

---

### Question 2
**Domain 2.0** — A company stores sensitive customer records in Amazon S3 and wants Amazon S3 to manage the encryption keys with the least operational overhead. Which server-side encryption option should they choose?

A) SSE-C  
B) SSE-KMS  
C) Client-side encryption using the Amazon S3 Encryption Client  
D) SSE-S3

<br><br><br><br>

**Correct Answer: D**
SSE-S3 uses Amazon S3-managed keys and is the simplest option with the least operational overhead. S3 handles key generation, encryption, and key management entirely on the customer's behalf.

---

### Question 3
**Domain 3.0** — According to NIST, what is the difference between a security event and a security incident?

A) A security event is always malicious; a security incident is always accidental  
B) A security event is any observable occurrence in a system or network; a security incident is an event that negatively impacts business operations or violates security policies  
C) A security event only applies to on-premises systems; a security incident only applies to cloud systems  
D) There is no difference; the terms are interchangeable

<br><br><br><br>

**Correct Answer: B**
NIST defines a security event as any observable occurrence in a system or network. A security incident is specifically an event that impacts business operations and runs counter to the organization's policies or standard security practices.

---

### Question 4
**Domain 1.0** — The US government uses a three-tier classification scheme for national security data. Which tier describes information whose unauthorized disclosure could cause "exceptionally grave damage" to national security?

A) Top Secret  
B) Confidential  
C) Secret  
D) Official

<br><br><br><br>

**Correct Answer: A**
In the US national security classification scheme, Top Secret is reserved for information whose unauthorized disclosure could reasonably be expected to cause exceptionally grave damage to national security. Confidential = damage, Secret = serious damage.

---

### Question 5
**Domain 2.0** — A developer needs to encrypt data before uploading it to Amazon S3 so that plaintext data never leaves the client environment. Which approach should the developer use?

A) SSE-S3  
B) SSE-KMS with a customer-managed key  
C) Client-side encryption using the Amazon S3 Encryption Client  
D) Enable default bucket encryption with AES-256

<br><br><br><br>

**Correct Answer: C**
Client-side encryption encrypts data on the client before it is sent to S3. This ensures that plaintext data never leaves the client environment. All SSE options encrypt data after it arrives at S3.

---

### Question 6
**Domain 1.0** — A company is building its data classification model. According to the CISSP five-tier commercial classification scheme, which tier represents data that would cause the MOST damage to the company if disclosed?

A) Confidential  
B) Public  
C) Proprietary  
D) Sensitive

<br><br><br><br>

**Correct Answer: D**
In the CISSP five-tier model, Sensitive data has the most limited access, requires the highest degree of integrity, and would cause the most damage if disclosed. The tiers from least to most sensitive are: Public, Proprietary, Private, Confidential, Sensitive.

---

### Question 7
**Domain 2.0** — In envelope encryption, what is the purpose of the wrapping key?

A) It encrypts the plaintext data directly  
B) It encrypts the data key, which in turn was used to encrypt the plaintext data  
C) It generates a hash of the plaintext for integrity verification  
D) It rotates the data key on a scheduled basis

<br><br><br><br>

**Correct Answer: B**
In envelope encryption, a data key encrypts the plaintext data, and then a wrapping key encrypts (wraps) the data key. This two-layer approach means the wrapping key never directly touches the plaintext. It protects the data key that protects the data.

---

### Question 8
**Domain 3.0** — A security team receives an alert about a potentially compromised Amazon EC2 instance. Which of the following is a recommended FIRST step in the incident response process?

A) Investigate the alert to determine the scope and nature of the potential compromise  
B) Immediately terminate the instance to stop the threat  
C) Restore the instance from the most recent backup  
D) Rotate all IAM credentials in the entire AWS account

<br><br><br><br>

**Correct Answer: A**
Effective incident response begins with investigation and analysis to understand the scope and nature of the incident. Terminating the instance prematurely could destroy forensic evidence. Restoring from backup or rotating all credentials are premature without first understanding the situation.

---

### Question 9
**Domain 1.0** — AWS recommends a three-tiered data classification model as a starting point. Under this model, which classification tier requires data encryption at rest AND in transit, strict IAM policies, and data residency within the United States?

A) Unclassified data  
B) Official data  
C) Secret data and above  
D) Public data

<br><br><br><br>

**Correct Answer: C**
Under the AWS recommended model, Secret data and above requires encryption at rest and in transit, must be stored within the United States, requires strict IAM policies on each service storing the data, and must not be accessible from the internet.

---

### Question 10
**Domain 2.0** — Which of the following BEST describes how SSE-KMS differs from SSE-S3 when encrypting objects in Amazon S3?

A) SSE-KMS uses AES-128 while SSE-S3 uses AES-256  
B) SSE-KMS allows the customer to manage encryption keys through AWS KMS, providing more control and audit capabilities  
C) SSE-KMS encrypts data in transit while SSE-S3 only encrypts data at rest  
D) SSE-KMS requires the customer to upload their own key material, while SSE-S3 does not

<br><br><br><br>

**Correct Answer: B**
SSE-KMS uses customer-managed keys in AWS Key Management Service, giving customers more control over key policies, rotation, and audit trails via CloudTrail. SSE-S3 uses S3-managed keys with less customer visibility. Both use AES-256.

---

### Question 11
**Domain 3.0** — What is the primary purpose of an incident response playbook?

A) To document the organization's data classification scheme  
B) To automate the encryption of data at rest across all AWS services  
C) To provide pre-defined procedures for responding to specific types of security incidents  
D) To generate IAM policies for new AWS accounts

<br><br><br><br>

**Correct Answer: C**
Incident response playbooks are pre-defined, documented procedures that guide teams through responding to specific types of security incidents. AWS provides sample playbooks as templates that organizations can customize.

---

### Question 12
**Domain 1.0** — A data perimeter in AWS is designed to ensure that only trusted identities access trusted resources from expected networks. Which THREE elements must be considered when designing a data perimeter?

A) Principals, resources, and networks  
B) Regions, availability zones, and edge locations  
C) Users, groups, and roles  
D) Encryption keys, certificates, and tokens

<br><br><br><br>

**Correct Answer: A**
The three key elements of a data perimeter are trusted principals (IAM roles/users), trusted resources (resources owned by your accounts), and expected networks (on-premises networks, VPCs, or networks used by AWS services on your behalf).

---

### Question 13
**Domain 2.0** — A company wants to use SSE-C to encrypt objects stored in Amazon S3. Which statement about SSE-C is correct?

A) Amazon S3 manages and stores the encryption keys on the customer's behalf  
B) The customer must provide the encryption key with each request, and Amazon S3 does not store the key  
C) SSE-C only works with objects smaller than 5 GB  
D) SSE-C requires the customer to use AWS KMS to generate the keys

<br><br><br><br>

**Correct Answer: B**
With SSE-C (Server-Side Encryption with Customer-Provided Keys), the customer provides the encryption key with each PUT and GET request. Amazon S3 performs the encryption/decryption but does not store the customer's key. The customer manages the keys entirely.

---

### Question 14
**Domain 3.0** — How does cloud-based incident response differ from traditional on-premises incident response?

A) Cloud IR does not require any incident response planning  
B) Cloud IR eliminates the need for forensic investigation  
C) Cloud IR only applies to security events, not security incidents  
D) Cloud IR leverages AWS-specific services and capabilities that are not available in traditional environments

<br><br><br><br>

**Correct Answer: D**
Cloud-based incident response leverages AWS-specific services and capabilities, such as CloudTrail logs, VPC Flow Logs, GuardDuty findings, and the ability to snapshot instances, that are not available in traditional on-premises environments.

---

### Question 15
**Domain 1.0** — Which three IAM capabilities are used to establish a data perimeter in AWS?

A) Service control policies (SCPs), resource-based policies, and VPC endpoint policies  
B) IAM users, IAM groups, and IAM roles  
C) Security groups, NACLs, and route tables  
D) AWS Config rules, CloudWatch alarms, and SNS topics

<br><br><br><br>

**Correct Answer: A**
Data perimeters are established using three primary IAM capabilities: AWS Organizations service control policies (SCPs) for organization-wide guardrails, resource-based policies attached to specific resources, and VPC endpoint policies to control network access to AWS services.

---

### Question 16
**Domain 2.0** — AWS services provide HTTPS endpoints using TLS for communication with AWS APIs. Which protocol group can be used with a VPN connection to facilitate encryption of data in transit when connecting to the AWS Cloud?

A) SSH and SFTP  
B) FTP and FTPS  
C) SMTP and IMAP  
D) IPsec

<br><br><br><br>

**Correct Answer: D**
IPsec is the group of secure connection protocols used with a virtual private network (VPN) connection to facilitate encryption of data in transit when connecting to the AWS Cloud.

---

### Question 17
**Domain 3.0** — During an incident response lab, a team member receives an alert about a possibly compromised EC2 instance. Which combination of activities should the team perform? (Select the BEST answer.)

A) Effective investigation, analysis, and lessons learned  
B) Immediate instance termination, key rotation, and account closure  
C) Data migration, service scaling, and cost optimization  
D) Patch deployment, feature release, and load testing

<br><br><br><br>

**Correct Answer: A**
AWS incident response best practices emphasize effective investigation to understand the incident, analysis to determine impact and root cause, and lessons learned to improve future response capabilities. Premature actions like termination can destroy evidence.

---

### Question 18
**Domain 2.0** — A developer is using the AWS Encryption SDK to encrypt sensitive data in a development environment. Which of the following is a best practice when using the SDK?

A) Use an older version of the SDK to ensure backward compatibility  
B) Store wrapping keys in plaintext alongside the encrypted data for easy access  
C) Protect your wrapping keys using a secure key infrastructure such as AWS KMS  
D) Disable digital signatures to improve encryption performance

<br><br><br><br>

**Correct Answer: C**
The AWS Encryption SDK generates a unique data key for each plaintext message and encrypts it with wrapping keys you supply. If wrapping keys are lost or deleted, encrypted data is unrecoverable. Best practice is to protect wrapping keys using a secure infrastructure like AWS KMS.

---

### Question 19
**Domain 1.0** — A resource-based policy on a Lambda function includes the condition `"StringEquals": {"aws:PrincipalOrgId": "098765432109"}`. What does this condition enforce?

A) Only principals from the specified AWS Organization can invoke the function  
B) Only principals from a specific AWS Region can invoke the function  
C) Only principals with MFA enabled can invoke the function  
D) Only principals using a specific VPC endpoint can invoke the function

<br><br><br><br>

**Correct Answer: A**
The `aws:PrincipalOrgId` condition key restricts access to principals that belong to the specified AWS Organization. This is the primary way to implement a trusted principal data perimeter, ensuring only members of your organization can access the resource.

---

### Question 20
**Domain 2.0** — How does TLS protect data in transit between an application and Amazon RDS?

A) TLS encrypts the database storage volumes  
B) TLS encrypts data in transit between the application and the RDS database, protecting table data and queries from unauthorized access or interception  
C) TLS replaces the need for IAM authentication to the database  
D) TLS compresses data to reduce network latency

<br><br><br><br>

**Correct Answer: B**
TLS encrypts data in transit between applications and Amazon RDS databases. This protects table data and queries from unauthorized access or interception while the data is moving across the network.

---

### Question 21
**Domain 1.0** — An SCP includes a Deny statement with the condition `"StringNotEquals": {"aws:ResourceOrgID": "098765432109"}` applied to `lambda:InvokeFunction` on all resources. What is the effect of this policy?

A) It allows all principals to invoke any Lambda function  
B) It only applies to Lambda functions in the us-east-1 Region  
C) It denies all Lambda invocations regardless of organization  
D) It denies invocation of Lambda functions that do NOT belong to the specified organization

<br><br><br><br>

**Correct Answer: D**
The `StringNotEquals` condition with `aws:ResourceOrgID` means the Deny effect applies when the resource's organization ID does NOT match the specified value. This prevents principals from invoking Lambda functions outside the trusted organization, establishing a trusted resource data perimeter.

---

### Question 22
**Domain 2.0** — A company needs to encrypt data in transit between applications and AWS Lambda functions. What mechanism does AWS Lambda use to protect data in transit?

A) Lambda uses SSH tunnels for all function invocations  
B) Lambda uses IPsec VPN connections for each invocation  
C) TLS encrypts data in transit between applications or AWS services and Lambda functions by default  
D) Lambda does not support encryption of data in transit

<br><br><br><br>

**Correct Answer: C**
TLS encrypts data in transit between applications or AWS services and Lambda functions by default. This protects sensitive data such as function code, invocation payloads, and responses from unauthorized access or interception while in transit.

---

### Question 23
**Domain 3.0** — Which AWS resource provides pre-defined templates that organizations can use as a starting point for building their own incident response procedures?

A) AWS Well-Architected Tool  
B) AWS Trusted Advisor  
C) AWS Service Catalog  
D) AWS Sample Playbooks

<br><br><br><br>

**Correct Answer: D**
AWS provides sample playbooks as templates that organizations can customize for their own incident response procedures. These playbooks define step-by-step procedures for responding to specific types of security incidents.

---

### Question 24
**Domain 1.0** — A VPC endpoint policy includes the conditions `"aws:ResourceOrgID": "098765432109"` AND `"aws:SourceVpce": "vpc-654321"`. What is the combined effect?

A) Only requests from the specified VPC endpoint targeting resources in the specified organization are allowed  
B) Any principal from any organization can invoke the function through any VPC endpoint  
C) The policy only applies during business hours  
D) The policy encrypts all traffic passing through the VPC endpoint

<br><br><br><br>

**Correct Answer: A**
When both conditions are combined with `StringEquals`, both must be true simultaneously. The resource must belong to organization 098765432109 AND the request must originate from VPC endpoint vpc-654321. This creates a restrictive data perimeter combining trusted resources with expected networks.

---

### Question 25
**Domain 2.0** — When using the AWS Encryption SDK, what happens during the decryption process after the plaintext data key is used to decrypt the data?

A) The plaintext data key is stored in an encrypted S3 bucket for future use  
B) The plaintext data key is cached indefinitely in memory  
C) The plaintext data key is discarded  
D) The plaintext data key is written to a CloudWatch log

<br><br><br><br>

**Correct Answer: C**
The AWS Encryption SDK's decryption method uses the plaintext data key to decrypt the data and then discards the plaintext data key. This is a security best practice. The plaintext key exists in memory only for the duration of the decryption operation.

---

### Question 26
**Domain 3.0** — Which of the following resources is referenced in the module as a key guide for handling computer security incidents?

A) AWS Well-Architected Framework, Cost Optimization Pillar  
B) NIST Computer Security Incident Handling Guide  
C) ISO 27001 Certification Handbook  
D) OWASP Top 10 Web Application Security Risks

<br><br><br><br>

**Correct Answer: B**
The NIST Computer Security Incident Handling Guide is specifically referenced as a key resource for incident response. It provides the foundational definitions (security event vs. security incident) and frameworks used throughout the module.

---

### Question 27
**Domain 2.0** — According to the module, which of the following is NOT a best practice when using the AWS Encryption SDK?

A) Use the latest version of the SDK  
B) Leverage default values provided by the SDK  
C) Store wrapping keys in the same location as the encrypted data for convenience  
D) Use digital signatures

<br><br><br><br>

**Correct Answer: C**
Storing wrapping keys alongside encrypted data is a security anti-pattern. AWS Encryption SDK best practices include: using the latest SDK version, leveraging default values, creating encryption context key-value pairs, using digital signatures, and protecting wrapping keys with a secure infrastructure like AWS KMS.

