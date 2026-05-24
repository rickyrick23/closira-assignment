Closira Backend Pipeline

A lightweight REST API and asynchronous worker simulating Closira’s core customer enquiry-handling workflow. Built with Python, FastAPI, and SQLite.

--- Quick Setup ---

This project is designed for zero-friction setup. No external infrastructure (like Redis, RabbitMQ, or Docker) is required to run the prototype.

Prerequisites

* Python 3.9+

Installation & Execution

1. Clone the repository and navigate to the backend folder:
git clone (https://github.com/rickyrick23/closira-assignment)
cd closira-assignment/backend
2. Create and activate a virtual environment:
On macOS/Linux:
python -m venv venv
source venv/bin/activate

On Windows:
python -m venv venv
venv\Scripts\activate

3. Install the dependencies:
pip install -r requirements.txt
4. Run the local development server:
uvicorn main:app --reload

--- Testing the API ---

Interactive Documentation (Swagger UI): 
Once the server is running, navigate to [http://127.0.0.1:8000/docs] to view all endpoints, expected schemas, and test them directly in the browser.

HTTP Client: A test.http file is included in the root directory containing sample payloads for all 5 required endpoints. This can be run directly using the REST Client extension in VS Code.

--- Architectural Decisions & Engineering Ownership ---

To satisfy the evaluation criteria for system design and engineering ownership, here is the rationale behind the technical choices made for this prototype:

1. Database: SQLite vs. PostgreSQL
Decision: SQLite with SQLAlchemy ORM.

Rationale: The primary goal of this assignment is to evaluate backend fundamentals and API design. SQLite provides a zero-configuration experience, allowing reviewers to clone and run the app immediately without provisioning a local database server.
Scalability Path: Because the data layer uses SQLAlchemy models, migrating to a production PostgreSQL environment simply requires updating the SQLALCHEMY_DATABASE_URL string and running standard Alembic migrations.

2. Async Processing: FastAPI BackgroundTasks vs. Celery
Decision: FastAPI BackgroundTasks.
Rationale: Introducing Celery requires a message broker (Redis/RabbitMQ) and running a separate worker process. For a local prototype, this introduces unnecessary setup friction. FastAPI's built-in BackgroundTasks executes in the same event loop but asynchronously after the HTTP response is returned, perfectly simulating the non-blocking behavior of the POST /enquiry endpoint.
Trade-off: In a real production environment handling high-volume Closira webhooks (WhatsApp/Email), Celery + Redis is the superior choice. If the FastAPI application crashes in this prototype, pending in-memory background tasks are lost. Celery guarantees task persistence and handles automatic retries for failed SOP matching.

3. Schema Design: Event-Sourced History
Instead of simply updating a single mutable status string on an Enquiries table, I implemented an append-only HistoryEvent table with a foreign key back to the main enquiry.
Rationale: This accurately reflects how production CRMs and ticketing systems operate. It naturally builds the audit trail required for the GET /enquiry/[id]/history endpoint, stores contextual metadata (like why an escalation happened) using a JSON column, and prevents data loss.

--- Known Limitations ---

Given the scope of the assignment, the following features were intentionally omitted:

1. Authentication: Endpoints are unprotected. A production system would require JWTs or API keys with tenant-isolation (ensuring Business A cannot see Business B's enquiries).
2. AI Integration: The SOP matching uses hardcoded keyword logic (as requested) rather than an LLM call.
3. Pagination: The /history endpoint currently returns all events. In production, this would be paginated using cursor or offset-based limits.
