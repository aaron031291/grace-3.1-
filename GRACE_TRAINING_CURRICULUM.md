# Grace Training Curriculum - Structured Learning Paths

## Overview

Comprehensive curricula for Grace to progress from novice to expert in core software engineering skills. Each curriculum includes study phases, practice tasks, and assessment criteria.

---

## Curriculum Structure

Each curriculum follows this format:

1. **Skill Overview** - What Grace will learn
2. **Prerequisites** - Required foundational knowledge
3. **Study Phases** - Ordered topics to study (with learning objectives)
4. **Practice Tasks** - Hands-on exercises (increasing complexity)
5. **Assessment Criteria** - How to measure proficiency
6. **Estimated Timeline** - Practice sessions needed

---

## Curriculum 1: Python Programming

### **Skill Overview**
Master Python programming from basics to advanced concepts.

### **Target Proficiency:** INTERMEDIATE

### **Prerequisites:**
- Basic programming concepts (variables, loops, conditions)

### **Study Phases:**

#### **Phase 1: Python Basics (Novice → Beginner)**
**Topics to study:**
- Python syntax and data types
- Variables and operators
- Control flow (if/elif/else, loops)
- Functions and parameters
- Lists, tuples, and dictionaries

**Learning objectives:**
```json
{
  "topic": "Python basics",
  "learning_objectives": [
    "Understand Python syntax and indentation",
    "Learn basic data types (int, float, str, bool)",
    "Master control flow structures",
    "Write and call functions with parameters",
    "Work with lists, tuples, and dictionaries"
  ],
  "max_materials": 8
}
```

#### **Phase 2: Object-Oriented Python (Beginner → Intermediate)**
**Topics to study:**
- Classes and objects
- Inheritance and polymorphism
- Encapsulation
- Magic methods
- Class methods and static methods

**Learning objectives:**
```json
{
  "topic": "Python OOP",
  "learning_objectives": [
    "Define classes with attributes and methods",
    "Implement inheritance hierarchies",
    "Use encapsulation and access modifiers",
    "Understand magic methods (__init__, __str__, __repr__)",
    "Differentiate class methods, static methods, and instance methods"
  ],
  "max_materials": 10
}
```

#### **Phase 3: Advanced Python (Intermediate)**
**Topics to study:**
- Decorators
- Generators and iterators
- Context managers
- Error handling and exceptions
- File I/O

**Learning objectives:**
```json
{
  "topic": "Advanced Python",
  "learning_objectives": [
    "Write and use decorators",
    "Create generators with yield",
    "Implement context managers (with statement)",
    "Handle exceptions properly with try/except/finally",
    "Read and write files efficiently"
  ],
  "max_materials": 12
}
```

### **Practice Tasks:**

#### **Beginner Tasks (Complexity: 0.2-0.4)**
1. **Calculator Function**
   - Write functions for basic arithmetic (+, -, *, /)
   - Handle edge cases (division by zero)
   - Use proper parameter types

2. **List Manipulator**
   - Functions to sort, filter, and transform lists
   - Implement common list operations
   - Use list comprehensions

3. **Dictionary Manager**
   - CRUD operations for dictionaries
   - Search and filter dictionary data
   - Handle missing keys

#### **Intermediate Tasks (Complexity: 0.5-0.7)**
4. **Class-Based To-Do App**
   - Define Task class with attributes
   - Implement TodoList class
   - Add/remove/complete tasks
   - Persist to file

5. **Decorator Practice**
   - Write timing decorator
   - Create logging decorator
   - Implement caching decorator
   - Chain multiple decorators

6. **File Processor**
   - Read and parse CSV/JSON files
   - Transform data structures
   - Write processed output
   - Handle file errors

#### **Advanced Tasks (Complexity: 0.8-0.9)**
7. **Context Manager for Resources**
   - Implement custom context manager
   - Manage file/database connections
   - Proper resource cleanup

8. **Generator-Based Data Pipeline**
   - Create data processing pipeline
   - Use generators for memory efficiency
   - Handle large datasets

### **Assessment Criteria:**

| Level | Proficiency Score | Success Rate | Tasks Completed | Key Indicators |
|-------|------------------|--------------|-----------------|----------------|
| NOVICE | 0.0 - 0.5 | < 50% | 0-2 | Understanding syntax |
| BEGINNER | 0.5 - 1.0 | 50-70% | 3-5 | Can write simple programs |
| INTERMEDIATE | 1.0 - 2.0 | 70-85% | 6-10 | Uses OOP, handles errors |
| ADVANCED | 2.0 - 3.0 | 85-95% | 11-20 | Advanced features, patterns |
| EXPERT | 3.0+ | 95%+ | 20+ | Teaches others, optimizes |

### **Estimated Timeline:**
- **Beginner level**: 5-8 practice sessions
- **Intermediate level**: 10-15 practice sessions
- **Total**: ~15-23 sessions

---

## Curriculum 2: REST API Design

### **Skill Overview**
Design and build production-ready RESTful APIs.

### **Target Proficiency:** INTERMEDIATE

### **Prerequisites:**
- Python programming (Intermediate)
- Basic HTTP knowledge
- Understanding of client-server architecture

### **Study Phases:**

#### **Phase 1: REST Fundamentals (Novice → Beginner)**
**Topics to study:**
- HTTP protocol basics
- RESTful principles and constraints
- HTTP methods (GET, POST, PUT, DELETE, PATCH)
- HTTP status codes
- URL design and routing

**Learning objectives:**
```json
{
  "topic": "REST API fundamentals",
  "learning_objectives": [
    "Understand REST architectural constraints",
    "Learn proper HTTP method usage",
    "Master HTTP status codes (2xx, 4xx, 5xx)",
    "Design clean URL structures",
    "Understand stateless communication"
  ],
  "max_materials": 10
}
```

#### **Phase 2: API Implementation (Beginner → Intermediate)**
**Topics to study:**
- FastAPI/Flask framework
- Request/response handling
- Data validation and serialization
- Error handling and status codes
- API documentation (OpenAPI/Swagger)

**Learning objectives:**
```json
{
  "topic": "API implementation",
  "learning_objectives": [
    "Build APIs with FastAPI or Flask",
    "Validate input data with Pydantic",
    "Return proper status codes and error messages",
    "Serialize/deserialize JSON",
    "Generate API documentation automatically"
  ],
  "max_materials": 12
}
```

#### **Phase 3: Authentication & Security (Intermediate)**
**Topics to study:**
- Authentication methods (JWT, OAuth)
- Authorization and permissions
- API keys and tokens
- CORS and security headers
- Rate limiting

**Learning objectives:**
```json
{
  "topic": "API security",
  "learning_objectives": [
    "Implement JWT authentication",
    "Understand OAuth 2.0 flows",
    "Handle API keys securely",
    "Configure CORS properly",
    "Implement rate limiting and throttling"
  ],
  "max_materials": 10
}
```

#### **Phase 4: Advanced Patterns (Intermediate → Advanced)**
**Topics to study:**
- Pagination and filtering
- API versioning strategies
- Caching strategies
- Asynchronous operations
- Webhooks and callbacks

**Learning objectives:**
```json
{
  "topic": "Advanced API patterns",
  "learning_objectives": [
    "Implement pagination for large datasets",
    "Version APIs properly (URL vs header)",
    "Add caching with Redis",
    "Handle async operations with background tasks",
    "Implement webhook systems"
  ],
  "max_materials": 8
}
```

### **Practice Tasks:**

#### **Beginner Tasks (Complexity: 0.3-0.5)**
1. **Simple CRUD API**
   - User management endpoints (create, read, update, delete)
   - Proper HTTP methods and status codes
   - In-memory data storage

2. **Todo API**
   - CRUD operations for tasks
   - Filter by status (completed/pending)
   - Basic validation

3. **Blog Post API**
   - Create/read/update/delete posts
   - List all posts
   - Get single post by ID

#### **Intermediate Tasks (Complexity: 0.6-0.8)**
4. **Authenticated API**
   - User registration and login
   - JWT token generation
   - Protected endpoints
   - Token refresh

5. **Paginated API**
   - Large dataset handling
   - Offset/limit pagination
   - Cursor-based pagination
   - Metadata in responses

6. **E-commerce API**
   - Products, orders, customers
   - Complex relationships
   - Transaction handling
   - Error recovery

#### **Advanced Tasks (Complexity: 0.8-1.0)**
7. **Versioned API**
   - v1 and v2 endpoints
   - Backward compatibility
   - Deprecation warnings
   - Migration strategy

8. **Async Webhook System**
   - Background task processing
   - Webhook delivery
   - Retry logic
   - Delivery status tracking

### **Assessment Criteria:**

| Level | Proficiency Score | Success Rate | Tasks Completed | Key Indicators |
|-------|------------------|--------------|-----------------|----------------|
| NOVICE | 0.0 - 0.5 | < 50% | 0-2 | Basic HTTP understanding |
| BEGINNER | 0.5 - 1.0 | 50-70% | 3-4 | Simple CRUD APIs |
| INTERMEDIATE | 1.0 - 2.0 | 70-85% | 5-7 | Auth, validation, docs |
| ADVANCED | 2.0 - 3.0 | 85-95% | 8-12 | Versioning, webhooks, caching |
| EXPERT | 3.0+ | 95%+ | 12+ | Production-ready, scalable |

### **Estimated Timeline:**
- **Beginner level**: 6-10 practice sessions
- **Intermediate level**: 10-15 practice sessions
- **Total**: ~16-25 sessions

---

## Curriculum 3: Database Design & SQL

### **Skill Overview**
Design efficient database schemas and write optimized SQL queries.

### **Target Proficiency:** INTERMEDIATE

### **Prerequisites:**
- Basic programming knowledge
- Understanding of data structures

### **Study Phases:**

#### **Phase 1: SQL Basics (Novice → Beginner)**
**Topics:**
- Relational database concepts
- SQL syntax (SELECT, INSERT, UPDATE, DELETE)
- WHERE clauses and filtering
- Sorting and limiting results
- Basic joins (INNER JOIN)

**Learning objectives:**
```json
{
  "topic": "SQL basics",
  "learning_objectives": [
    "Understand relational database structure",
    "Write SELECT queries with filtering",
    "Use INSERT, UPDATE, DELETE",
    "Sort and limit query results",
    "Perform simple INNER JOINs"
  ],
  "max_materials": 10
}
```

#### **Phase 2: Database Design (Beginner → Intermediate)**
**Topics:**
- Normalization (1NF, 2NF, 3NF)
- Primary and foreign keys
- Indexes and performance
- Constraints (UNIQUE, NOT NULL, CHECK)
- Relationships (one-to-many, many-to-many)

**Learning objectives:**
```json
{
  "topic": "Database design",
  "learning_objectives": [
    "Normalize database schemas to 3NF",
    "Define primary and foreign keys properly",
    "Create indexes for query optimization",
    "Apply constraints for data integrity",
    "Model complex relationships"
  ],
  "max_materials": 12
}
```

#### **Phase 3: Advanced SQL (Intermediate)**
**Topics:**
- Complex JOINs (LEFT, RIGHT, FULL, CROSS)
- Subqueries and CTEs
- Aggregate functions and GROUP BY
- Window functions
- Transactions and ACID properties

**Learning objectives:**
```json
{
  "topic": "Advanced SQL",
  "learning_objectives": [
    "Use all JOIN types appropriately",
    "Write subqueries and CTEs",
    "Aggregate data with GROUP BY and HAVING",
    "Apply window functions (ROW_NUMBER, RANK, etc.)",
    "Manage transactions with COMMIT/ROLLBACK"
  ],
  "max_materials": 10
}
```

### **Practice Tasks:**

#### **Beginner Tasks (Complexity: 0.3-0.5)**
1. **Library Database**
   - Schema: books, authors, borrowers
   - Basic CRUD queries
   - Simple JOINs

2. **School Database**
   - Students, courses, enrollments
   - INSERT student data
   - Query course rosters

3. **Employee Database**
   - Employees, departments
   - Filter by department
   - Update salaries

#### **Intermediate Tasks (Complexity: 0.6-0.8)**
4. **E-commerce Schema**
   - Products, orders, customers, order_items
   - Normalized to 3NF
   - Complex queries with multiple JOINs

5. **Blog Platform**
   - Users, posts, comments, tags
   - Many-to-many relationships
   - Aggregation queries

6. **Analytics Queries**
   - Sales data analysis
   - Window functions for rankings
   - Time-series aggregations

### **Assessment Criteria:**

| Level | Proficiency Score | Success Rate | Tasks Completed | Key Indicators |
|-------|------------------|--------------|-----------------|----------------|
| BEGINNER | 0.5 - 1.0 | 50-70% | 3-4 | Basic queries, simple JOINs |
| INTERMEDIATE | 1.0 - 2.0 | 70-85% | 5-7 | Normalized schemas, complex queries |
| ADVANCED | 2.0 - 3.0 | 85-95% | 8-12 | Window functions, optimization |

---

## Curriculum 4: Backend Development (Full Stack)

### **Skill Overview**
Build complete backend systems with APIs, databases, authentication, and deployment.

### **Target Proficiency:** ADVANCED

### **Prerequisites:**
- Python programming (Intermediate)
- REST API design (Intermediate)
- Database design (Intermediate)

### **Study Phases:**

#### **Phase 1: Backend Architecture (Intermediate → Advanced)**
**Topics:**
- MVC/MVT patterns
- Service layer architecture
- Dependency injection
- Configuration management
- Environment variables

#### **Phase 2: Testing & Quality (Advanced)**
**Topics:**
- Unit testing with pytest
- Integration testing
- Test fixtures and mocking
- Test coverage
- CI/CD pipelines

#### **Phase 3: Deployment & Operations (Advanced)**
**Topics:**
- Docker containers
- Environment setup
- Logging and monitoring
- Error tracking
- Performance optimization

### **Practice Tasks:**

#### **Advanced Tasks (Complexity: 0.7-0.9)**
1. **Complete Blog Platform Backend**
   - Users, posts, comments, likes
   - JWT authentication
   - PostgreSQL database
   - Comprehensive tests (>80% coverage)
   - Docker deployment

2. **Task Management API**
   - Teams, projects, tasks
   - Role-based access control
   - Real-time updates
   - Background job processing

3. **E-commerce Backend**
   - Products, cart, orders, payments
   - Inventory management
   - Email notifications
   - Admin dashboard API

### **Assessment Criteria:**

| Level | Proficiency Score | Success Rate | Key Indicators |
|-------|------------------|--------------|----------------|
| ADVANCED | 2.0 - 3.0 | 85-95% | Complete systems, tests, deployment |
| EXPERT | 3.0+ | 95%+ | Production-ready, scalable, monitored |

---

## Curriculum 5: Testing & TDD

### **Skill Overview**
Master testing strategies and test-driven development.

### **Target Proficiency:** INTERMEDIATE

### **Study Phases:**

#### **Phase 1: Testing Fundamentals**
**Topics:**
- Unit vs integration vs E2E testing
- Test structure (Arrange-Act-Assert)
- Test fixtures and setup/teardown
- Assertions and expectations
- Test coverage metrics

#### **Phase 2: Advanced Testing**
**Topics:**
- Mocking and patching
- Test doubles (stubs, mocks, spies)
- Parameterized tests
- Testing async code
- Property-based testing

#### **Phase 3: TDD Practices**
**Topics:**
- Red-Green-Refactor cycle
- Writing tests first
- Refactoring with test safety
- Test organization
- Continuous testing

### **Practice Tasks:**

1. **String Utilities with TDD**
   - Write tests first
   - Implement functions
   - Refactor with confidence

2. **Calculator with Full Coverage**
   - Unit tests for all operations
   - Edge case testing
   - >95% coverage

3. **API Testing Suite**
   - Test all endpoints
   - Mock external services
   - Integration tests

---

## Skill Progression Summary

### **Recommended Learning Sequence:**

```
1. Python Programming (Beginner → Intermediate)
   ↓
2. Database Design & SQL (Beginner → Intermediate)
   ↓
3. REST API Design (Beginner → Intermediate)
   ↓
4. Testing & TDD (Beginner → Intermediate)
   ↓
5. Backend Development (Intermediate → Advanced)
```

### **Total Practice Sessions:**
- **To Intermediate across all skills**: ~60-80 sessions
- **To Advanced in backend**: ~100+ sessions
- **To Expert proficiency**: ~150+ sessions

---

## Using the Curricula

### **1. Select a curriculum:**
```bash
POST /training/curriculum
{
  "skill_name": "Python programming",
  "target_proficiency": "intermediate"
}
```

### **2. Study each phase:**
```bash
POST /training/study
{
  "topic": "Python basics",
  "learning_objectives": ["Understand syntax", "Learn data types", ...]
}
```

### **3. Practice tasks in order:**
```bash
POST /training/practice
{
  "skill_name": "Python programming",
  "task_description": "Calculator Function",
  "complexity": 0.3
}
```

### **4. Track progress:**
```bash
GET /training/skills/Python%20programming
GET /training/analytics/progress
```

### **5. Advance when ready:**
- **Proficiency score** > threshold for current level
- **Success rate** > 70%
- **Operational confidence** > 0.75

---

## Curriculum Metrics

Track effectiveness:

1. **Completion Rate**
   - % of students completing each phase
   - Average time to proficiency

2. **Success Rate**
   - Task completion success by phase
   - First-attempt success rate

3. **Knowledge Retention**
   - Trust scores over time
   - Operational confidence decay

4. **Gap Identification**
   - Common failure points
   - Topics needing reinforcement

---

## Summary

These curricula provide structured learning paths from novice to expert in core software engineering skills. Each curriculum:

✅ **Structured phases** - Logical topic progression
✅ **Clear objectives** - Specific learning goals
✅ **Practice tasks** - Hands-on skill building
✅ **Assessment criteria** - Measurable proficiency
✅ **Integration ready** - Works with Grace's active learning system

**Grace can now systematically build expertise through deliberate practice guided by these curricula!**
