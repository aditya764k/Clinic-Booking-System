# Module 2: Authentication & Role-Based Access Control (RBAC)

This document provides a comprehensive summary of the architecture, logic, and concepts implemented in Module 2 for the Clinic Booking System backend.

---

## 1. Overview & Core Concepts

The Authentication module is built around **Stateless JWTs (JSON Web Tokens)** stored exclusively in **HttpOnly Cookies**. This represents a modern, highly secure approach to web authentication.

### Why HttpOnly Cookies?
Traditionally, Single Page Applications (React/Vue) store JWTs in `localStorage` and attach them to the `Authorization: Bearer <token>` header for every request. However, `localStorage` is accessible via JavaScript, making the application highly vulnerable to **Cross-Site Scripting (XSS)** attacks. 

By using `HttpOnly` cookies, the browser stores the token and automatically attaches it to outgoing requests to the backend. JavaScript running in the browser **cannot** read or steal this cookie, effectively mitigating XSS risks for session hijacking.

---

## 2. Approaches Used

### A. Dual Token System (Access + Refresh)
We implemented a two-token architecture:
- **Access Token:** Short-lived (e.g., 60 minutes). Used for immediate authentication. Contains user identity (`sub`) and `role` claims.
- **Refresh Token:** Long-lived (e.g., 7 days). Used *only* at the `/auth/refresh` endpoint to silently issue a new access token when the old one expires, preventing the user from having to log in constantly.

### B. Auto-Login on Registration
When a user registers (`POST /auth/register`), they don't just get a `201 Created` response. The backend immediately issues the `access_token` and `refresh_token` cookies. This improves UX by allowing the frontend to route the user directly to the dashboard without requiring a separate, immediate login request.

### C. Dependency Injection for RBAC
We heavily leveraged FastAPI's Dependency Injection system to create a clean, reusable authorization layer.
- `get_current_user`: A dependency that reads the cookie, decodes the JWT, fetches the user from the DB, and returns the User object. It serves as the **single source of truth** for identity. No endpoint decodes tokens manually.
- `require_role(*roles)`: A dependency factory (a function that returns a dependency). It wraps `get_current_user` and adds a validation step to ensure the user's role is in the allowed list, returning a `403 Forbidden` if not.

### D. Polymorphic Profile Creation
During registration, the backend checks the requested `role`. In a single atomic database transaction, it creates the base `User` row and the corresponding profile row (`PatientProfile` or `DoctorProfile`). If either insert fails, the transaction rolls back, preventing orphaned records.

---

## 3. Endpoints Logic

| Endpoint | Logic |
|---|---|
| `POST /auth/register` | Checks email uniqueness. Hashes password. Creates `User` and linked `Patient/DoctorProfile`. Auto-sets cookies. Returns user info. |
| `POST /auth/login` | Uses constant-time password verification to prevent timing attacks. Sets new cookies. |
| `POST /auth/refresh` | Reads `refresh_token` cookie. Validates it. Issues a new `access_token` cookie. |
| `POST /auth/logout` | Sets both cookies' `max_age` to 0, instructing the browser to delete them. |
| `GET /auth/whoami` | Protected by `get_current_user`. Returns the currently logged-in user's data. Used by frontend on page load to restore session state. |
| `GET /auth/google/login` | Returns a `302 Redirect` to Google's OAuth consent screen. |
| `GET /auth/google/callback` | Google redirects here with a code. Backend exchanges code for Google user info. If email exists, it links the account. If new, it provisions a `PatientProfile`. Sets cookies and redirects to frontend. |

---

## 4. Important Points & Security Measures

1. **No Tokens in JSON Body:** The JWTs are never returned in the API JSON responses. They only exist in the `Set-Cookie` HTTP headers.
2. **CORS Configuration:** To allow the React dev server (`localhost:3000`) to send cookies to the backend (`localhost:8000`), CORS is explicitly configured with `allow_credentials=True` and a specific `FRONTEND_ORIGIN` (wildcard `*` is not allowed when credentials are true).
3. **Constant-Time Verification:** In `POST /auth/login`, if a user provides an email that does not exist, the backend still runs the heavy bcrypt hashing algorithm against a dummy hash. This ensures that login requests take the same amount of time whether the email exists or not, preventing attackers from guessing registered emails based on server response times.
4. **Strict Token Typing:** The JWT payload includes a `type` claim (`access` or `refresh`). The `get_current_user` dependency enforces `type=="access"`, preventing a malicious user from using a stolen refresh token to access protected endpoints.
5. **Testing Without Docker:** We configured the test suite to spin up an in-memory SQLite database. This makes tests extremely fast and allows CI/CD pipelines to run them without needing a PostgreSQL container.

---

## 5. Things to Remember (For Future Modules)

### Securing Endpoints
When building future modules (Appointments, Invoices, etc.), you do not need to write auth logic. Simply use the dependencies:

```python
from app.core.dependencies import get_current_user, require_role

# For an endpoint ANY logged-in user can hit:
@router.get("/my-data")
def my_data(user: User = Depends(get_current_user)):
    ...

# For an endpoint ONLY Doctors can hit:
@router.post("/prescribe")
def prescribe(user: User = Depends(require_role("doctor"))):
    ...

# For an endpoint Doctors OR Receptionists can hit:
@router.patch("/status")
def update_status(user: User = Depends(require_role("doctor", "receptionist"))):
    ...
```

### Writing Tests
When writing tests for future modules, you do not need to manually register and login users. Use the `authenticated_client` fixture provided in `tests/conftest.py`:

```python
def test_create_appointment(authenticated_client):
    # This automatically registers a patient and attaches the cookies to the client!
    client = authenticated_client(role="patient") 
    response = client.post("/appointments", json={...})
    assert response.status_code == 201
```

### Frontend Integration
When you build the React frontend:
- Ensure your HTTP client (Axios or Fetch) is configured to send credentials. In Axios, set `axios.defaults.withCredentials = true;`.
- Never use AJAX to call `/auth/google/login`. Always use an HTML link (`<a href="...">`) or `window.location.href = ...` because OAuth requires full page redirects.
