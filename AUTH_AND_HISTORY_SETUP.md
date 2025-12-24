# Authentication and History API Setup

This document describes the authentication and history API implementation.

## Overview

The system now includes:
- User authentication with JWT tokens (access + refresh)
- Protected routes requiring authentication
- History API for viewing invoice validation history
- User-scoped data (users can only see their own invoices)

## Backend Changes

### New Dependencies

Added to `backend/audos_console/requirements.txt`:
- `bcrypt==4.1.2` - Password hashing
- `PyJWT==2.8.0` - JWT token generation/verification

### Database Models

1. **User Model** (`backend/audos_console/db/auth_models.py`):
   - `id`, `email` (unique), `username` (optional, unique), `password_hash`, `created_at`
   - Password hashing with bcrypt
   - JWT token generation (access + refresh tokens)

2. **InvoiceResult Model** (updated):
   - Added `user_id` column (foreign key to users table)
   - All invoices are now associated with a user

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
  - Body: `{ "email": "...", "password": "...", "username": "..." (optional) }`
  - Returns: `{ "user": {...}, "access_token": "...", "refresh_token": "..." }`

- `POST /api/auth/login` - Login
  - Body: `{ "email": "...", "password": "..." }`
  - Returns: `{ "user": {...}, "access_token": "...", "refresh_token": "..." }`

- `POST /api/auth/refresh` - Refresh access token
  - Body: `{ "refresh_token": "..." }`
  - Returns: `{ "access_token": "..." }`

### History API Endpoints

- `GET /api/history` - Get invoice history (requires auth)
  - Query params: `status`, `batch_id`, `invoice_number`, `start_date`, `end_date`, `page`, `per_page`
  - Returns paginated list of invoices for authenticated user

- `GET /api/history/:id` - Get specific invoice detail (requires auth)
  - Returns invoice details (scoped to authenticated user)

### Protected Routes

The following routes now require authentication:
- `/validate-invoices` - Batch invoice validation
- `/manual-invoice/validate` - Manual invoice validation
- `/api/history` - History API endpoints

### Auth Middleware

`backend/audos_console/shared/auth_middleware.py`:
- `@require_auth` decorator - Requires valid JWT token
- `@optional_auth` decorator - Works with or without auth
- Sets `request.current_user_id` and `request.current_user_email` on authenticated requests

### Batch Runner Updates

- `run_batch()` now requires `user_id` parameter
- All invoices inserted via `insert_invoice()` include `user_id`

## Frontend Changes

### New Files

1. **Auth Utilities** (`src/lib/auth.ts`):
   - Token storage/retrieval from localStorage
   - `getAuthHeader()` helper for API calls

2. **Auth API** (`src/lib/authApi.ts`):
   - `register()`, `login()`, `refreshAccessToken()`, `logout()`

3. **Auth Context** (`src/contexts/AuthContext.tsx`):
   - React context for auth state
   - `useAuth()` hook

4. **Login Page** (`src/pages/LoginPage.tsx`):
   - Login/Register UI

5. **Protected Route** (`src/components/ProtectedRoute.tsx`):
   - Wrapper component that redirects to login if not authenticated

6. **History API** (`src/lib/historyApi.ts`):
   - `getHistory()`, `getInvoiceDetail()`

### Updated Files

1. **App.tsx**:
   - Wrapped with `AuthProvider`
   - Added `/login` route
   - Protected routes with `ProtectedRoute` component

2. **HistoryPage.tsx**:
   - Fetches real data from `/api/history`
   - Filters by status, date range
   - Pagination support

3. **TopBar.tsx**:
   - Shows user email
   - Logout button

4. **BulkInvoiceValidationPage.tsx**:
   - Includes auth header in API calls

5. **ManualInvoiceForm.tsx**:
   - Includes auth header in API calls

## Environment Variables

Required environment variables:

```bash
# JWT Configuration
JWT_SECRET=<strong-secret-key>  # Required for JWT signing
ACCESS_TOKEN_EXPIRES=3600        # Optional, default 1 hour
REFRESH_TOKEN_EXPIRES=604800     # Optional, default 7 days

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname  # Required for production

# Flask
SECRET_KEY=<secret-key>  # Required for Flask sessions
```

## Database Migration

Run migrations to create tables:

```bash
cd backend/audos_console
python -m db.migrations
```

This will:
1. Create `users` table
2. Create `invoice_results` table (if not exists)
3. Add `user_id` column to `invoice_results` (if not exists)

## Testing

Run tests:

```bash
# Auth tests
cd backend/lookup_service
PYTHONPATH=.:../audos_console SECRET_KEY=test JWT_SECRET=test-secret DATABASE_URL=sqlite:///:memory: python -m unittest tests.test_auth -v

# History API tests
PYTHONPATH=.:../audos_console SECRET_KEY=test JWT_SECRET=test-secret DATABASE_URL=sqlite:///:memory: python -m unittest tests.test_history_api -v
```

## Usage

### User Registration/Login

1. Navigate to `/login`
2. Register a new account or login
3. Tokens are stored in localStorage
4. All API calls automatically include auth header

### Viewing History

1. Navigate to `/history`
2. Use filters (status, date range)
3. Click "View PDF" to download invoice PDFs

### API Usage

All protected endpoints require `Authorization: Bearer <access_token>` header.

Example:
```javascript
fetch('/api/history', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
})
```

## Backward Compatibility

The old `VALIDATION_API_TOKEN` authentication is deprecated but may still work for backward compatibility. New implementations should use JWT authentication.

## Security Notes

- Passwords are hashed with bcrypt
- JWT tokens use HS256 algorithm
- Access tokens are short-lived (default 1 hour)
- Refresh tokens are longer-lived (default 7 days)
- All database queries are scoped to authenticated user
- CORS should be configured appropriately in production

