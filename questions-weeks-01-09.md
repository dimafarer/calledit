# DF (Developer Fundamentals) – Weeks 1–9 Comprehensive Question Set

---

**1. What is the primary purpose of programming?**

A) Designing hardware components  
B) Creating visual artwork  
C) Managing network connections  
D) Giving precise instructions to a computer to perform specific tasks

<br><br><br><br>

**Correct Answer: D**
**Explanation:** Programming is the process of giving precise instructions to a computer to perform specific tasks, similar to writing a detailed recipe for a cook to follow step by step.

---

**2. What does the AWS SDK for Python (Boto3) allow developers to do?**

A) Programmatically interact with AWS services through a simplified interface  
B) Design graphical user interfaces for AWS  
C) Create hardware configurations for servers  
D) Write CSS stylesheets for web applications

<br><br><br><br>

**Correct Answer: A**
**Explanation:** AWS SDK for Python (Boto3) is the official AWS software development kit for Python that enables programmatic interaction with AWS services through a simplified interface, acting like a remote control for AWS in Python.

---

**3. When should a developer use a `while` loop instead of a `for` loop in Python?**

A) When iterating over a dictionary  
B) When the developer does not know in advance how many times the loop should run  
C) When the developer knows the exact number of iterations  
D) When accessing elements of a list by index

<br><br><br><br>

**Correct Answer: B**
**Explanation:** A while loop is ideal when you don't know in advance how many iterations are needed. It repeats a block of code as long as a condition remains true, such as prompting a user for input until they provide valid data.

---

**4. What is the primary purpose of error handling in Python?**

A) Prevent all errors from occurring  
B) Make programs run faster  
C) Manage errors gracefully without crashing the program  
D) Delete error messages entirely

<br><br><br><br>

**Correct Answer: C**
**Explanation:** Error handling allows programs to manage unexpected situations gracefully. Using try-except blocks, developers can catch exceptions and respond appropriately instead of letting the program crash.

---

**5. In Git, what is a commit?**

A) A snapshot of your work at a specific point in time  
B) A request to merge two branches  
C) A connection to a remote server  
D) A command to delete a branch

<br><br><br><br>

**Correct Answer: A**
**Explanation:** A commit in Git creates a snapshot of your work that can be compared with previous versions. It records the state of all tracked files at that moment, allowing you to track changes over time.

---

**6. In object-oriented programming, what is a class?**

A) A specific instance of an object  
B) A built-in Python function  
C) A type of loop structure  
D) A blueprint or template for creating objects with defined attributes and methods

<br><br><br><br>

**Correct Answer: D**
**Explanation:** A class is a user-defined data type that acts as a blueprint for individual objects, attributes, and methods. It defines the structure and behavior that all instances created from it will share.

---

**7. What happens when you use bracket notation to access a key that does not exist in a Python dictionary?**

A) Python returns None automatically  
B) The dictionary creates the key with a default value  
C) A KeyError is raised and the program halts unless the error is caught  
D) Python prints a warning but continues

<br><br><br><br>

**Correct Answer: C**
**Explanation:** When using bracket notation to look up a key that doesn't exist, Python raises a KeyError which crashes the program unless caught. The get() method is a safer alternative that returns None or a default value instead.

---

**8. In Amazon S3, what are the three essential components of an object?**

A) Name, size, and location  
B) Content, metadata, and a unique identifier (key)  
C) Bucket, region, and version  
D) Header, body, and footer

<br><br><br><br>

**Correct Answer: B**
**Explanation:** Each object in Amazon S3 contains three components: the content (actual file data), metadata (information about the object), and a unique identifier (object key) that allows it to be located and retrieved.

---

**9. In Python, what data types can a variable store? (Select the most complete answer)**

A) Strings, integers, floats, and Booleans among others  
B) Only numbers and text  
C) Only integers and strings  
D) Only Booleans and floats

<br><br><br><br>

**Correct Answer: A**
**Explanation:** Python variables can store multiple data types including strings (text), integers (whole numbers), floats (decimal numbers), and Booleans (True/False). Python is dynamically typed, so variables can hold any data type.

---

**10. What is the primary limitation of in-memory storage for application data?**

A) It can only store numeric data  
B) It requires an internet connection  
C) It is slower than file-based storage  
D) All data is lost when the program ends or the computer restarts

<br><br><br><br>

**Correct Answer: D**
**Explanation:** In-memory storage (RAM) is temporary — when a program ends or the computer restarts, all stored data is lost. This lack of data persistence makes it unsuitable for applications that need to retain information between sessions.

---

**11. What is the index of the first element in a Python list?**

A) 1  
B) 0  
C) -1  
D) None

<br><br><br><br>

**Correct Answer: B**
**Explanation:** Python uses zero-based indexing, meaning the first element of a list has an index of 0, the second has index 1, and so on. You can also use negative indexing where -1 refers to the last element.

---

**12. When using Python's `open()` function, which mode adds new data to an existing file without deleting its current contents?**

A) Write mode ("w")  
B) Read mode ("r")  
C) Append mode ("a")  
D) Create mode ("x")

<br><br><br><br>

**Correct Answer: C**
**Explanation:** Append mode ("a") adds new data to the end of an existing file without erasing old entries. Write mode ("w") would overwrite the entire file, and read mode ("r") only reads content.

---

**13. What is the primary purpose of branches in Git?**

A) To allow developers to work on code in parallel without affecting the main version  
B) To permanently delete old code  
C) To compress repository size  
D) To encrypt source code files

<br><br><br><br>

**Correct Answer: A**
**Explanation:** Branches in Git are independent lines of development that let you work on features or fixes in parallel to the main codebase. This allows multiple developers to work simultaneously without interfering with each other's changes.

---

**14. In Python OOP, what is the purpose of the `__init__` method?**

A) To delete an object from memory  
B) To import external libraries  
C) To define class-level constants  
D) To initialize instance attributes when a new object is created

<br><br><br><br>

**Correct Answer: D**
**Explanation:** The __init__ method (constructor) runs automatically whenever a new instance of a class is created. It uses the 'self' parameter to bind attributes to the specific instance, allowing each object to have unique attribute values.

---

**15. What is a key benefit of using functions in Python?**

A) Functions make code run faster automatically  
B) Code organization and reusability — write once, use many times  
C) Functions eliminate all bugs  
D) Functions replace the need for variables

<br><br><br><br>

**Correct Answer: B**
**Explanation:** Functions allow developers to organize code into reusable blocks. Instead of duplicating code, you define a function once and call it whenever needed, making code cleaner, more maintainable, and less error-prone.

---

**16. What is Amazon Textract used for?**

A) Translating text between languages  
B) Generating images from text prompts  
C) Automatically extracting text and data from scanned documents  
D) Storing files in the cloud

<br><br><br><br>

**Correct Answer: C**
**Explanation:** Amazon Textract is an AWS service that automatically extracts text, handwriting, and data from scanned documents. It goes beyond simple OCR by identifying the contents of fields in forms and information stored in tables.

---

**17. Why is Python commonly used for AI and machine learning applications?**

A) It has a simple syntax and extensive libraries for data processing and AI  
B) It is the fastest programming language available  
C) It was specifically designed only for AI  
D) It can only run on cloud servers

<br><br><br><br>

**Correct Answer: A**
**Explanation:** Python is popular for AI/ML because of its readable syntax, extensive ecosystem of libraries (like NumPy, pandas, scikit-learn), and strong community support. It enables rapid development and prototyping of AI applications.

---

**18. In a Python dictionary, what must be true about all keys?**

A) Keys must always be integers  
B) Each key must be unique within the dictionary  
C) Keys must be sorted alphabetically  
D) Keys can be duplicated if values differ

<br><br><br><br>

**Correct Answer: B**
**Explanation:** Dictionary keys must be unique — you cannot have two keys with the same name. Keys are also case-sensitive, so 'age' and 'Age' are considered different keys. Common key types include strings and numbers.

---

**19. What is Amazon Rekognition used for in the DF curriculum?**

A) Converting speech to text  
B) Managing database records  
C) Deploying web applications  
D) AI-powered image analysis to detect objects and labels in images

<br><br><br><br>

**Correct Answer: D**
**Explanation:** Amazon Rekognition is an AWS AI service for computer vision and image analysis. In the DF curriculum, it's used to detect food items in images as part of building an AI-powered pet food recipe generator.

---

**20. What type of database is Amazon DynamoDB?**

A) A relational SQL database  
B) A file-based storage system  
C) A fully managed NoSQL database service  
D) An in-memory cache service

<br><br><br><br>

**Correct Answer: C**
**Explanation:** Amazon DynamoDB is a fully managed NoSQL database service provided by AWS. Unlike relational databases that use tables with fixed schemas, DynamoDB uses flexible key-value and document data models.

---

**21. What does the temperature inference parameter control in Amazon Bedrock?**

A) The randomness or creativity of the generated output  
B) The speed of the API response  
C) The maximum length of the output  
D) The language of the response

<br><br><br><br>

**Correct Answer: A**
**Explanation:** Temperature is set between 0 and 1. A higher temperature makes output more diverse and unpredictable (creative), while a lower temperature makes it more focused and predictable (deterministic).

---

**22. What are the key Git commands for synchronizing with a remote repository?**

A) `git save` and `git load`  
B) `git upload` and `git download`  
C) `git push` to upload changes and `git pull` to download and merge changes  
D) `git send` and `git receive`

<br><br><br><br>

**Correct Answer: C**
**Explanation:** git push uploads your local commits to the remote repository, while git pull downloads remote changes and merges them into your local branch. git fetch downloads without merging. Regular pushing and pulling keeps repositories synchronized.

---

**23. What is the difference between a class attribute and an instance attribute in Python?**

A) Class attributes are private; instance attributes are public  
B) Class attributes are faster; instance attributes are slower  
C) There is no difference between them  
D) Class attributes are shared across all instances; instance attributes are unique to each object

<br><br><br><br>

**Correct Answer: D**
**Explanation:** Class attributes are defined in the class body and shared by all instances (like 'wheels = 2' for all bikes). Instance attributes are set in __init__ and are unique to each object (like different frame sizes for different bikes).

---

**24. What AWS service is used in the DF Week 4 curriculum for language translation?**

A) Amazon Polly  
B) Amazon Translate  
C) Amazon Comprehend  
D) Amazon Lex

<br><br><br><br>

**Correct Answer: B**
**Explanation:** Amazon Translate is the AWS service used in Week 4 to send data and receive translations in a chosen language. Students build an application integrating Amazon Translate with Amazon Bedrock to process and display translated information.

---

**25. What happens when you upload a file with the same name to a versioned Amazon S3 bucket?**

A) The old file is permanently deleted  
B) The upload is rejected with an error  
C) Both files are merged into one  
D) Amazon S3 creates a new version while preserving the previous version

<br><br><br><br>

**Correct Answer: D**
**Explanation:** With versioning enabled, Amazon S3 generates a new version of the object while preserving previous versions. This provides data protection and change history, though it may increase storage costs over time.

---

**26. What is an Integrated Development Environment (IDE)?**

A) A software application that provides tools for writing, testing, and debugging code in one place  
B) A type of programming language  
C) A cloud storage service  
D) A web browser extension

<br><br><br><br>

**Correct Answer: A**
**Explanation:** An IDE combines essential development tools — code editor, debugger, terminal, and more — into a single application. This makes coding more efficient by providing everything developers need in one workspace.

---

**27. How does the `with open()` statement benefit file handling in Python?**

A) It makes the code run faster  
B) It prevents files from being modified  
C) It automatically closes the file after operations are complete  
D) It allows multiple files to be opened simultaneously

<br><br><br><br>

**Correct Answer: C**
**Explanation:** The 'with' statement is a context manager that automatically handles cleanup. When the code block inside 'with' finishes, Python automatically closes the file — no need to call .close() manually.

---

**28. Which Python library is used to interact with Amazon DynamoDB programmatically?**

A) Django ORM  
B) Boto3 (AWS SDK for Python)  
C) SQLAlchemy  
D) PyMongo

<br><br><br><br>

**Correct Answer: B**
**Explanation:** Boto3 is the AWS SDK for Python that provides methods to create tables, add items, query data, and perform other DynamoDB operations programmatically. It handles authentication and API calls to AWS services.

---

**29. What is the key difference between centralized and distributed version control systems?**

A) Centralized systems are newer than distributed systems  
B) Distributed systems require an internet connection at all times  
C) Centralized systems support branching but distributed systems do not  
D) Distributed systems give each developer a full local copy of the repository; centralized systems use a single server

<br><br><br><br>

**Correct Answer: D**
**Explanation:** In centralized version control, there's one server with the complete history. In distributed systems like Git, every developer has a full local copy of the repository including its complete history, enabling offline work and faster operations.

---

**30. What does the `range(3)` function generate in Python?**

A) The sequence of numbers 0, 1, 2  
B) The sequence 1, 2, 3  
C) The sequence 0, 1, 2, 3  
D) The single number 3

<br><br><br><br>

**Correct Answer: A**
**Explanation:** range(3) generates numbers starting at 0 and stopping before 3, producing the sequence 0, 1, 2. The range() function is commonly used with for loops to create counting loops that iterate a specific number of times.

---

## Answer Key

| Q# | Answer | Domain/Week |
|-----|--------|-------------|
| 1 | D | Week 1 – Programming Overview |
| 2 | A | Week 3 – AWS SDK & Bedrock |
| 3 | B | Week 2 – Control Flow |
| 4 | C | Week 5 – Error Handling |
| 5 | A | Week 7 – Git Fundamentals |
| 6 | D | Week 6 – OOP |
| 7 | C | Week 4 – Dictionaries |
| 8 | B | Week 9 – Amazon S3 |
| 9 | A | Week 1 – Variables & Data Types |
| 10 | D | Week 8 – Databases |
| 11 | B | Week 3 – Python Lists |
| 12 | C | Week 5 – File Operations |
| 13 | A | Week 7 – Git Branches |
| 14 | D | Week 6 – OOP Constructors |
| 15 | B | Week 4 – Python Functions |
| 16 | C | Week 9 – Amazon Textract |
| 17 | A | Week 1 – Introduction to Python |
| 18 | B | Week 2 – Python Dictionaries |
| 19 | D | Week 5 – Amazon Rekognition |
| 20 | C | Week 8 – Amazon DynamoDB |
| 21 | A | Week 3 – Amazon Bedrock |
| 22 | C | Week 7 – Remote Collaboration |
| 23 | D | Week 6 – OOP Attributes |
| 24 | B | Week 4 – Amazon Translate |
| 25 | D | Week 9 – S3 Versioning |
| 26 | A | Week 1 – IDE Setup |
| 27 | C | Week 5 – File Handling Best Practices |
| 28 | B | Week 8 – Python with DynamoDB |
| 29 | D | Week 7 – Version Control Systems |
| 30 | A | Week 2 – For Loops & Range |

## Answer Distribution

- **A:** Questions 2, 5, 9, 13, 17, 21, 26, 30 (8 questions)
- **B:** Questions 3, 8, 11, 15, 18, 24, 28 (7 questions)
- **C:** Questions 4, 7, 12, 16, 20, 22, 27 (7 questions)
- **D:** Questions 1, 6, 10, 14, 19, 23, 25, 29 (8 questions)

✅ No letter repeats 3 times in a row.
