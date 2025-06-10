# Week 8 Questions

## Domain 1: RAG Fundamentals and Definition

### Question 1

What is the primary purpose of Retrieval Augmented Generation (RAG) in AI systems?

A) To enhance language model outputs with external knowledge  
B) To train new language models from scratch  
C) To compress large language models for efficient deployment  
D) To generate synthetic training data for machine learning  

### Question 2

Which of the following best describes how RAG improves upon traditional language model prompting?

A) It eliminates the need for prompt engineering  
B) It provides access to up-to-date and domain-specific information  
C) It allows for unlimited input token lengths  
D) It automatically fine-tunes the language model on new data  

### Question 3

In a RAG system, what is the primary source of the information used to augment the language model's knowledge?

A) The model's internal parameters  
B) A separate neural network  
C) External knowledge bases or document collections  
D) User feedback and corrections  

### Question 4

What is a key advantage of using RAG over fine-tuning a language model on domain-specific data?

A) RAG is always faster to implement  
B) RAG doesn't require any additional data storage  
C) RAG can adapt to new information without retraining  
D) RAG eliminates all hallucinations in model outputs  

### Question 5

Which of the following scenarios would benefit MOST from implementing a RAG system?

A) Answering questions about frequently updated company policies  
B) Generating creative fiction stories  
C) Performing basic arithmetic calculations  
D) Translating text between languages  

## Domain 2: RAG Components and Architecture

### Question 6

What is the primary function of the retriever component in a RAG system?

A) To generate natural language responses  
B) To store and index external knowledge  
C) To identify and extract relevant information from external sources  
D) To compress and encode input queries  

### Question 7

In the context of RAG, what is the purpose of creating embeddings?

A) To reduce the size of the external knowledge base  
B) To translate text between different languages  
C) To represent text as dense vector representations for efficient search  
D) To generate new training data for the language model  

### Question 8

What is the role of the vector store in a RAG system?

A) To generate vector graphics for visual outputs  
B) To store and index vector embeddings of the external knowledge  
C) To perform vector calculations for the language model  
D) To compress the language model's parameters  

### Question 9

Which component of a RAG system is responsible for combining the retrieved information with the original query?

A) The prompt augmenter  
B) The retriever  
C) The vector store  
D) The language model  

### Question 10

What is the purpose of chunking in the data ingestion process of a RAG system?

A) To reduce the overall size of the external knowledge base  
B) To improve the accuracy of the language model  
C) To create smaller, manageable pieces of text for efficient retrieval and embedding  
D) To eliminate redundant information in the knowledge base  

## Domain 3: RAG Implementation Challenges

### Question 11

What is a significant challenge when implementing RAG for multi-lingual applications?

A) Increased computational requirements for translation  
B) Difficulty in finding suitable language models  
C) Ensuring consistent embedding quality across languages  
D) Limited availability of vector stores for different languages  

### Question 12

Which of the following is a potential challenge when scaling a RAG system to handle very large knowledge bases?

A) Increased latency in retrieving relevant information  
B) Difficulty in generating coherent responses  
C) Limited availability of large language models  
D) Inability to update the external knowledge base  

### Question 13

What is a common challenge in maintaining the accuracy of a RAG system over time?

A) Gradual degradation of the language model's performance  
B) Keeping the external knowledge base up-to-date and relevant  
C) Increasing costs of cloud storage for vector embeddings  
D) Growing complexity of user queries  

### Question 14

Which of the following is a challenge when implementing RAG for domain-specific applications with specialized terminology?

A) Limited availability of pre-trained language models  
B) Difficulty in creating accurate embeddings for specialized terms  
C) Increased computational requirements for inference  
D) Lack of support for domain-specific data formats  

### Question 15

What is a potential challenge in ensuring the ethical use of RAG systems?

A) Preventing the retrieval of copyrighted material  
B) Maintaining user privacy when processing queries  
C) Avoiding biases present in the external knowledge sources  
D) All of the above  

## Domain 4: Amazon Bedrock Knowledge Bases

### Question 16

What is a key feature of Amazon Bedrock Knowledge Bases for implementing RAG?

A) It provides pre-trained language models  
B) It offers a fully managed solution for the RAG workflow  
C) It automatically generates training data for fine-tuning  
D) It creates custom embedding models for specific domains  

### Question 17

Which data source format is currently supported by Amazon Bedrock Knowledge Bases for advanced parsing?

A) JSON  
B) XML  
C) PDF  
D) CSV  

### Question 18

What is the default chunking strategy provided by Amazon Bedrock Knowledge Bases?

A) Fixed-size chunks of 100 tokens  
B) Variable-size chunks based on semantic meaning  
C) Chunks of about 300 tokens optimized for question-answering tasks  
D) No chunking, preserving original document structure  

### Question 19

Which API in Amazon Bedrock Knowledge Bases is used to perform the entire RAG workflow, including query embedding, similarity search, and response generation?

A) Retrieve  
B) RetrieveAndGenerate  
C) CreateKnowledgeBase  
D) InvokeModel  

### Question 20

Which embedding models are supported by Amazon Bedrock Knowledge Bases for vector creation? (Select TWO)

A) Amazon Titan Text Embeddings V2  
B) Cohere Embed  
C) OpenAI Ada  
D) Google BERT  
