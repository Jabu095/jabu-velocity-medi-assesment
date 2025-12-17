# Velocity Media - Event Aggregation Platform

A Django-based backend for aggregating public event data from Google APIs for the Johannesburg and Pretoria metropolitan areas.

## 🎯 Popular Django Packages

This project uses some of the most loved Django packages in the ecosystem:

- **django-cors-headers** - CORS support for frontend/backend communication
- **django-filter** - Declarative filtering for DRF (replaces manual queryset filtering)
- **django-extensions** - Development productivity tools (shell_plus, graph_models)
- **django-debug-toolbar** - Essential debugging tool (SQL queries, templates, performance)
- **django-ratelimit** - API protection from abuse (rate limiting)
- **django-health-check** - Health monitoring endpoints
- **pytest-django** - Modern testing framework
- **black, flake8, isort** - Code quality tools


## 📋 Assessment Overview

This project implements the Backend Developer Technical Assessment with the following components:

| Part | Component | Status |
|------|-----------|--------|
| 1 | Data Ingestion (Google Places API) | ✅ Complete |
| 2 | Data Storage (Django Models) | ✅ Complete |
| 3 | Data Sanitation (4 Rules) | ✅ Complete |
| 4 | Minimal REST API | ✅ Complete |

---

## 🏗️ Architecture Decisions

### Google Places API (New)


### Data Model Design

```
Event
├── Core Fields (Assessment Required)
│   ├── title (CharField)
│   ├── start_date (DateTimeField, nullable)
│   ├── venue_name (CharField)
│   ├── city (CharField, indexed)
│   ├── category (CharField)
│   ├── event_url (URLField)
│   ├── source (CharField)
│   └── raw_payload (JSONField)
│
├── Additional Fields
│   ├── source_id (CharField, unique) ← Duplicate prevention
│   ├── description (TextField)
│   ├── address (CharField)
│   ├── latitude/longitude (FloatField)
│   └── created_at/updated_at (DateTimeField)
│
└── Indexes
    ├── city + start_date (composite)
    ├── category
    ├── source
    └── created_at
```

**Duplicate Prevention:** The `source_id` field (unique constraint) combines the source name and external ID (e.g., `google_places:ChIJ...`). This allows:
- Upsert operations (update existing or create new)
- Multiple data sources without ID collision
- Data lineage tracking

### Sanitation Rules Implementation

| Rule | Function | Description |
|------|----------|-------------|
| 1 | `standardize_city_name()` | Maps variations (jhb, Joburg, Tshwane) to canonical names |
| 2 | `parse_date()` | Handles ISO 8601, human dates, timestamps with SA date format priority |
| 3 | `clean_text()` | Strips HTML, normalizes whitespace, unescapes entities |
| 4 | `validate_and_clean_url()` | Validates URL structure, adds https:// if missing |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Platform account with Places API enabled

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd velocity-media

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your Google API key
```

### Configuration

1. Get a Google Places API key:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project or select existing
   - Enable "Places API" (or "Places API (New)")
   - Create an API key under "Credentials"

2. Update `.env`:
   ```
   GOOGLE_PLACES_API_KEY=your_api_key_here
   SECRET_KEY=generate-a-secure-key
   DEBUG=True
   ```

### Database Setup

```bash
# Create migrations
python manage.py makemigrations events

# Apply migrations
python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser
```

### Running the Application

```bash
# Start the development server
python manage.py runserver

# Server runs at http://localhost:8000
```

---

## 🔐 Admin Console

The Django admin interface provides a user-friendly way to manage event data.

### Access
- **URL:** http://localhost:8000/admin/
- **Default credentials:** (create with `python manage.py createsuperuser`)

### Creating an Admin User

```bash
python manage.py createsuperuser
# Follow prompts to enter username, email, and password
```

### Admin Features

The Event admin interface includes:

| Feature | Description |
|---------|-------------|
| **List View** | Displays title, city, venue, category, date, source |
| **Filters** | Filter by city, source, category, created date |
| **Search** | Search by title, venue, description, address |
| **Date Hierarchy** | Navigate events by creation date |
| **Fieldsets** | Organized sections: Event Info, Location, Links, Raw Data |

### Admin Fieldsets

```
Event Information
├── title
├── description
├── category
└── start_date

Location
├── venue_name
├── city
├── address
├── latitude
└── longitude

Links & Source
├── event_url
├── source
└── source_id (read-only)

Raw Data (collapsible)
└── raw_payload (read-only)

Timestamps (collapsible)
├── created_at (read-only)
└── updated_at (read-only)
```

---

## 🌐 Frontend Application

The application includes a complete frontend interface with JWT authentication.

### Features

- **User Authentication**
  - User registration with email validation
  - Secure login with JWT tokens
  - Automatic token refresh
  - Protected routes requiring authentication

- **Dashboard**
  - View all events in a responsive grid
  - Filter by city (Johannesburg/Pretoria)
  - Filter by category
  - Search events by keyword
  - Pagination support
  - Real-time statistics

- **Event Details**
  - Detailed event information
  - Venue information
  - Location data
  - External links

### Frontend Routes

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/` | Home/Dashboard | ✅ Yes |
| `/login/` | Login page | ❌ No |
| `/register/` | Registration page | ❌ No |
| `/dashboard/` | Events dashboard | ✅ Yes |
| `/events/<id>/` | Event detail page | ✅ Yes |

### Accessing the Frontend

1. Start the server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to http://localhost:8000

3. Register a new account or login with existing credentials

4. Browse events on the dashboard

### JWT Token Management

The frontend automatically:
- Stores JWT tokens in localStorage
- Adds `Authorization: Bearer <token>` header to API requests
- Refreshes access tokens when they expire
- Redirects to login if authentication fails

### Frontend Files

```
templates/
├── base.html              # Base template
└── events/
    ├── login.html         # Login page
    ├── register.html      # Registration page
    ├── dashboard.html     # Events dashboard
    └── event_detail.html  # Event detail page

static/
├── css/
│   └── style.css          # Main stylesheet
└── js/
    ├── auth.js            # Authentication utilities
    └── api.js             # API client with JWT
```

---

## 📡 API Endpoints

### Authentication Endpoints

```
POST /api/auth/register/   - Register new user
POST /api/auth/login/       - Login user (returns JWT tokens)
POST /api/auth/refresh/     - Refresh access token
POST /api/auth/token/      - Alternative JWT token endpoint
POST /api/auth/token/refresh/ - Alternative refresh endpoint
```

**Note:** All event endpoints require JWT authentication.


## 🔄 Data Ingestion

### Management Command

```bash
# Fetch from all cities
python manage.py ingest_events

# Fetch from specific city
python manage.py ingest_events --city Johannesburg

# Limit results
python manage.py ingest_events --max-results 100

# Preview without saving
python manage.py ingest_events --dry-run

# Verbose output
python manage.py ingest_events --verbose
```

### Example Output
```
Fetching event venues from Google Places API...
Found 50 venues in Johannesburg
Found 45 venues in Pretoria
Fetched 95 venues from API
==================================================
INGESTION COMPLETE
==================================================
  Created: 85
  Updated: 10
  Skipped: 0
  Total processed: 95
```

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test events

# Run with verbosity
python manage.py test events -v 2

# Run specific test class
python manage.py test events.tests.SanitationTests
```

### Test Coverage

- **Sanitation Tests:** City normalization, date parsing, text cleaning, URL validation
- **Model Tests:** Event creation, duplicate prevention, auto-normalization
- **API Tests:** List, filter, detail, stats endpoints, pagination

---

## 📁 Project Structure

```
velocity-media/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
│
├── velocity_media/           # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Configuration
│   ├── urls.py              # Root URL config
│   └── wsgi.py
│
└── events/                   # Events application
    ├── __init__.py
    ├── apps.py
    ├── models.py            # Event model
    ├── admin.py             # Admin interface
    ├── views.py             # API views
    ├── urls.py              # API routes
    ├── serializers.py       # DRF serializers
    ├── sanitation.py        # Data cleaning utilities
    ├── tests.py             # Test suite
    │
    ├── services/            # External API integrations
    │   ├── __init__.py
    │   └── google_places.py # Google Places API service
    │
    └── management/
        └── commands/
            └── ingest_events.py  # Data ingestion command
```

---

## 🔧 Technical Details

### Dependencies

| Package | Purpose |
|---------|---------|
| Django 5.x | Web framework |
| djangorestframework | REST API |
| google-api-python-client | Google API client |
| python-dotenv | Environment variables |
| python-dateutil | Date parsing |
| validators | URL validation |
| requests | HTTP client |

### Database

- **Engine:** SQLite (as per assessment requirements)
- **Location:** `db.sqlite3` in project root

### Time Zone

- Configured for `Africa/Johannesburg`
- All dates stored as UTC, converted on display

---

## 🚧 Future Improvements

If this were a production system, consider:

1. **Event Data Sources**
   - Integrate Eventbrite API for actual events
   - Add Google Calendar public events
   - Implement Ticketmaster API

2. **Infrastructure**
   - Switch to PostgreSQL for production
   - Add Redis for caching
   - Implement Celery for background ingestion

3. **Features**
   - Add authentication/authorization
   - Implement rate limiting
   - Add webhook notifications for new events

4. **Monitoring**
   - Add structured logging
   - Implement health checks
   - Add APM integration

---

## 📝 License

This project was created as part of a technical assessment.

---

## 👤 Author

Created for Velocity Media Backend Developer Assessment by Jabulani Madzivadondo

