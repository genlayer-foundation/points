# API Reference

This document provides a comprehensive reference for the GenLayer Points API.

## Base URL

```
Production: https://api.points.genlayer.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

The API uses Sign-In With Ethereum (SIWE) for authentication with session-based cookies.

### Authentication Endpoints

#### Get Nonce

```http
GET /api/auth/nonce/
```

Returns a nonce for SIWE message signing.

**Response:**
```json
{
  "nonce": "abc123xyz..."
}
```

#### Login

```http
POST /api/auth/login/
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "domain wants you to sign in...",
  "signature": "0x...",
  "referral_code": "ABC12345"  // optional
}
```

**Response:**
```json
{
  "authenticated": true,
  "address": "0x123...",
  "user_id": 1,
  "created": false,
  "referral_code": "XYZ98765",
  "referred_by": null
}
```

#### Verify Authentication

```http
GET /api/auth/verify/
```

**Response:**
```json
{
  "authenticated": true,
  "address": "0x123...",
  "user_id": 1
}
```

#### Logout

```http
POST /api/auth/logout/
```

**Response:**
```json
{
  "message": "Logged out successfully."
}
```

---

## Users

### Get Current User

```http
GET /api/v1/users/me/
```

Requires authentication.

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "address": "0x123...",
  "description": "Bio text",
  "profile_image_url": "https://...",
  "banner_image_url": "https://...",
  "website": "https://example.com",
  "twitter_handle": "johndoe",
  "discord_handle": "johndoe#1234",
  "github_username": "johndoe",
  "referral_code": "ABC12345"
}
```

### Update Profile

```http
PATCH /api/v1/users/me/
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "New Name",
  "description": "Updated bio",
  "twitter_handle": "newhandle"
}
```

### Get User by Address

```http
GET /api/v1/users/by-address/{address}/
```

**Response:** Same as current user object

### Get User Highlights

```http
GET /api/v1/users/by-address/{address}/highlights/
```

**Query Parameters:**
- `limit` (default: 5) - Number of highlights to return

---

## Contributions

### List Contributions

```http
GET /api/v1/contributions/
```

**Query Parameters:**
- `page` (default: 1)
- `page_size` (default: 10)
- `user_address` - Filter by user
- `category` - Filter by category slug
- `group_consecutive` (default: false) - Group same-type contributions

**Response:**
```json
{
  "count": 100,
  "next": "http://.../contributions/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 1,
      "user_details": {...},
      "contribution_type": 1,
      "contribution_type_name": "Blog Post",
      "points": 50,
      "frozen_global_points": 100,
      "multiplier_at_creation": "2.00",
      "contribution_date": "2024-01-15T10:30:00Z",
      "notes": "Published article about...",
      "evidence_items": [...],
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Get Contribution Highlights

```http
GET /api/v1/contributions/highlights/
```

**Query Parameters:**
- `limit` (default: 10)
- `category` - Filter by category slug
- `waitlist_only` (default: false)

---

## Contribution Types

### List Contribution Types

```http
GET /api/v1/contribution-types/
```

**Query Parameters:**
- `category` - Filter by category slug
- `is_submittable` - Filter by submittable status

**Response:**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "name": "Blog Post",
      "slug": "blog-post",
      "description": "Write articles about GenLayer",
      "category": "builder",
      "min_points": 10,
      "max_points": 100,
      "current_multiplier": 2.0,
      "is_submittable": true,
      "examples": ["Tutorial", "Review"]
    }
  ]
}
```

### Get Type Statistics

```http
GET /api/v1/contribution-types/statistics/
```

**Query Parameters:**
- `category` - Filter by category slug

### Get Top Contributors for Type

```http
GET /api/v1/contribution-types/{id}/top_contributors/
```

Returns top 10 contributors for a specific contribution type.

---

## User Submissions

Endpoints for managing user-submitted contributions.

### List My Submissions

```http
GET /api/v1/submissions/my/
```

Requires authentication.

**Query Parameters:**
- `state` - Filter by state (pending, accepted, rejected, more_info_needed)
- `page` (default: 1)
- `page_size` (default: 20)

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid...",
      "contribution_type": 1,
      "contribution_type_name": "Blog Post",
      "contribution_date": "2024-01-15",
      "notes": "My submission notes",
      "state": "pending",
      "state_display": "Pending Review",
      "staff_reply": "",
      "evidence_items": [...],
      "can_edit": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Submission

```http
POST /api/v1/submissions/
Content-Type: application/json
```

**Request Body:**
```json
{
  "contribution_type": 1,
  "contribution_date": "2024-01-15",
  "notes": "Description of my contribution",
  "recaptcha": "recaptcha-token",
  "mission": 1  // optional
}
```

### Update Submission

```http
PATCH /api/v1/submissions/{id}/
Content-Type: application/json
```

Only allowed when state is `pending` or `more_info_needed`.

**Request Body:**
```json
{
  "notes": "Updated description",
  "evidence_items": [
    {"description": "Link to work", "url": "https://..."}
  ]
}
```

### Cancel Submission

```http
DELETE /api/v1/submissions/{id}/
```

Soft deletes by marking as rejected.

### Add Evidence

```http
POST /api/v1/submissions/{id}/add-evidence/
Content-Type: application/json
```

**Request Body:**
```json
{
  "description": "Additional proof",
  "url": "https://example.com/proof"
}
```

---

## Leaderboard

### Get Leaderboard

```http
GET /api/v1/leaderboard/
```

**Query Parameters:**
- `type` - Leaderboard type (global, validator, builder, etc.)
- `page` (default: 1)
- `page_size` (default: 50)
- `order` (default: asc) - Rank order

**Response:**
```json
{
  "count": 1000,
  "results": [
    {
      "rank": 1,
      "user": {...},
      "total_points": 5000,
      "contribution_count": 25
    }
  ]
}
```

### Get Stats

```http
GET /api/v1/leaderboard/stats/
```

**Query Parameters:**
- `type` - Filter by leaderboard type

**Response:**
```json
{
  "participant_count": 1500,
  "contribution_count": 10000,
  "total_points": 500000
}
```

### Get Trending Contributors

```http
GET /api/v1/leaderboard/trending/
```

**Query Parameters:**
- `limit` (default: 10)

---

## Missions

### List Missions

```http
GET /api/v1/missions/
```

**Query Parameters:**
- `contribution_type` - Filter by contribution type ID
- `active` (default: false) - Only show active missions

### Get Mission

```http
GET /api/v1/missions/{id}/
```

---

## Error Responses

### 400 Bad Request

```json
{
  "error": "Validation failed",
  "details": {
    "field_name": ["Error message"]
  }
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "error": "You do not have permission to perform this action."
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error

```json
{
  "error": "An unexpected error occurred."
}
```

---

## Rate Limiting

API endpoints may be rate limited. When rate limited, you'll receive:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

---

## Pagination

List endpoints return paginated responses:

```json
{
  "count": 100,
  "next": "http://api/v1/resource/?page=2",
  "previous": null,
  "results": [...]
}
```

Use `page` and `page_size` query parameters to navigate.
