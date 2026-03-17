# DI1 – Developer Intermediate 1
## Multi-Week Review – 20 Question Set

---

**Question 1**
Which technology is responsible for defining the **content and structure** of a webpage?

A. CSS  
B. JavaScript  
C. Python  
D. HTML  

<br><br><br><br>

**Correct Answer: D**
HTML (HyperText Markup Language) is the foundational language used to define the content and structure of a webpage. CSS handles presentation and JavaScript handles behavior.

---

**Question 2**
In a three-tier web application architecture, where is the **business logic** processed?

A. Presentation tier  
B. Application tier  
C. Data tier  
D. Network tier  

<br><br><br><br>

**Correct Answer: B**
The application tier (also called the logic tier) processes the business logic of the application. The presentation tier handles the UI, and the data tier manages data storage.

---

**Question 3**
Which CSS selector syntax is used to apply styles to a **class** of HTML elements?

A. #className  
B. *className  
C. @className  
D. .className  

<br><br><br><br>

**Correct Answer: D**
CSS class selectors begin with a dot (.) followed by the class name. The `#` symbol is used for ID selectors.

---

**Question 4**
What is the purpose of the **Document Object Model (DOM)** in a web browser?

A. It compiles JavaScript into machine code for faster execution  
B. It stores CSS stylesheets in memory for reuse  
C. It is an in-memory representation of the HTML document that allows programmatic access and modification of elements  
D. It manages HTTP requests between the browser and the web server  

<br><br><br><br>

**Correct Answer: C**
The DOM is an in-memory tree representation of an HTML document. JavaScript uses the DOM API to access and manipulate elements, attributes, and text nodes in the document.

---

**Question 5**
In Django's **Model-View-Template (MVT)** pattern, what is the primary role of the **View**?

A. To define the database schema and field types  
B. To store static HTML files for rendering  
C. To manage URL routing and redirect requests  
D. To implement the application logic, access models, and return HTTP responses  

<br><br><br><br>

**Correct Answer: D**
In Django's MVT pattern, the View contains the business logic. It accesses models to retrieve data, renders templates, and returns HTTP responses to the client.

---

**Question 6**
Which Django command is used to **apply prepared migrations** to the database?

A. makemigrations  
B. migrate  
C. syncdb  
D. loaddata  

<br><br><br><br>

**Correct Answer: B**
The `migrate` command applies prepared migrations to the database schema. The `makemigrations` command analyzes models and prepares the migration files, but does not apply them.

---

**Question 7**
What type of relationship is defined between a **Pet** and its **VaccinationCard** in the Django models example from DI1?

A. ForeignKey (many-to-one)  
B. ManyToManyField  
C. OneToOneField  
D. GenericRelation  

<br><br><br><br>

**Correct Answer: C**
The Pet model uses a `OneToOneField` to relate to the VaccinationCard model, meaning each pet has exactly one vaccination card and vice versa.

---

**Question 8**
In Django templates, which tag is used to **inherit** from a parent template?

A. {% include %}  
B. {% import %}  
C. {% block %}  
D. {% extends %}  

<br><br><br><br>

**Correct Answer: D**
The `{% extends %}` tag is used in a child template to inherit the structure of a parent (base) template. The `{% block %}` tag defines overridable sections within templates.

---

**Question 9**
Which AWS service allows you to **deploy and manage web applications** without worrying about the underlying infrastructure?

A. AWS Lambda  
B. Amazon EC2  
C. AWS Elastic Beanstalk  
D. Amazon ECS  

<br><br><br><br>

**Correct Answer: C**
AWS Elastic Beanstalk is a Platform-as-a-Service (PaaS) that handles deployment, scaling, and infrastructure management automatically, allowing developers to focus on writing code.

---

**Question 10**
What is the purpose of the **Boto3 `resource()` interface** in the AWS SDK for Python?

A. It provides a low-level, direct mapping to AWS service APIs  
B. It is used exclusively for Amazon S3 operations  
C. It provides an object-oriented, higher-level abstraction for interacting with AWS services  
D. It replaces the need for IAM roles when accessing AWS services  

<br><br><br><br>

**Correct Answer: C**
The Boto3 `resource()` interface provides a higher-level, object-oriented abstraction over AWS services. The `client()` interface provides the lower-level API access.

---

**Question 11**
In the **API Gateway integration pattern**, what is the primary function of Amazon API Gateway?

A. To store and retrieve data from DynamoDB tables  
B. To act as a proxy between external requestors and backend microservices, providing a single endpoint  
C. To compile and deploy Lambda functions automatically  
D. To monitor and log application performance metrics  

<br><br><br><br>

**Correct Answer: B**
API Gateway functions as a proxy that takes incoming requests and redirects them to the appropriate internal microservice endpoint, providing a single URL for client applications.

---

**Question 12**
Which HTTP method would you use to **retrieve a list of customers** from a REST API endpoint?

A. POST  
B. DELETE  
C. PUT  
D. GET  

<br><br><br><br>

**Correct Answer: D**
The GET method is used to retrieve data from a server. In the DI1 lab, the `[GET] /ListCustomers` endpoint invokes a Lambda function to scan a DynamoDB table.

---

**Question 13**
What does the **`{% block content %}`** tag do in a Django base template?

A. It imports external CSS and JavaScript files into the template  
B. It defines a named section that child templates can override with their own content  
C. It loops through a queryset and renders each item  
D. It conditionally displays content based on user authentication status  

<br><br><br><br>

**Correct Answer: B**
The `{% block %}` tag defines a named, overridable section in a base template. Child templates that extend the base can replace the content of these blocks with their own HTML.

---

**Question 14**
In AWS Step Functions, which state type allows you to **process multiple items in parallel** using a dynamic number of iterations?

A. Choice state  
B. Wait state  
C. Task state  
D. Map state  

<br><br><br><br>

**Correct Answer: D**
The Map state in AWS Step Functions enables dynamic parallelism, allowing Lambda to process each item in a collection in parallel — for example, processing each item in a customer's order simultaneously.

---

**Question 15**
Which of the following correctly describes how **JavaScript is integrated** into an HTML document using best practices?

A. JavaScript must always be written inline within HTML tags using the `onclick` attribute  
B. JavaScript code should be written in a separate `.js` file and referenced in the HTML document using the `<script>` element  
C. JavaScript is automatically included in all HTML documents without any additional configuration  
D. JavaScript must be placed inside the `<style>` tag in the HTML `<head>` section  

<br><br><br><br>

**Correct Answer: B**
Best practice is to write JavaScript in a separate external file and reference it using the `<script>` element. This separates concerns and makes the code easier to maintain.

---

**Question 16**
In the context of AWS Step Functions, what is the purpose of a **Retry statement**?

A. To permanently stop a state machine execution when an error occurs  
B. To send a notification to an administrator when a step fails  
C. To automatically attempt a failed step again after an error  
D. To branch the workflow to a different state based on input conditions  

<br><br><br><br>

**Correct Answer: C**
A Retry statement in Step Functions allows the workflow to automatically re-attempt a failed step. A Catch statement handles errors by routing to an alternative step.

---

**Question 17**
Which Django generic view class would you use to **display a list of objects** from a model?

A. DetailView  
B. CreateView  
C. UpdateView  
D. ListView  

<br><br><br><br>

**Correct Answer: D**
`ListView` is the Django generic view class used to display a list of objects from a model. `DetailView` shows a single object, `CreateView` provides a form to create one, and `UpdateView` allows editing.

---

**Question 18**
What is the structure of an **AWS API Gateway invoke URL**?

A. `https://{lambda_arn}.execute-api.{region}.amazonaws.com/{stage_name}/`  
B. `https://{restapi_id}.execute-api.{region}.amazonaws.com/{stage_name}/`  
C. `https://{region}.execute-api.{restapi_id}.amazonaws.com/{stage_name}/`  
D. `https://{stage_name}.execute-api.{region}.amazonaws.com/{restapi_id}/`  

<br><br><br><br>

**Correct Answer: B**
The correct API Gateway invoke URL format is: `https://{restapi_id}.execute-api.{region}.amazonaws.com/{stage_name}/` — where `restapi_id` is the API identifier, `region` is the AWS Region, and `stage_name` is the deployment stage.

---

**Question 19**
In Django, what is the role of the **`urls.py`** file at the application level?

A. It defines the database models and their field types  
B. It stores the HTML templates used for rendering views  
C. It maps application-specific URL patterns to their corresponding view functions  
D. It configures middleware and installed applications for the Django project  

<br><br><br><br>

**Correct Answer: C**
The application-level `urls.py` maps URL patterns to view functions within that specific application, building on the project-level URL mappings defined in the project's `urls.py`.

---

**Question 20**
Which AWS service is used to **route events from AWS services** (such as an S3 file upload) to consumer applications like Lambda functions?

A. Amazon SQS  
B. Amazon SNS  
C. Amazon EventBridge  
D. AWS Step Functions  

<br><br><br><br>

**Correct Answer: C**
Amazon EventBridge routes events from AWS services to consumer applications. For example, when an MP3 file is uploaded to S3, a PUT event can trigger a Lambda function via EventBridge.

---
