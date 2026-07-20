# API Contracts: Database & Storage Setup

This directory contains the API contracts for the database and storage feature.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/company` | Create company profile |
| GET | `/api/company/{id}` | Get company profile |
| PUT | `/api/company/{id}` | Update company profile |
| DELETE | `/api/company/{id}` | Delete company profile |
| POST | `/api/company/{id}/brand-images` | Upload brand images |

## Data Flow

1. User creates company profile via `POST /api/company`
2. User uploads brand images via `POST /api/company/{id}/brand-images`
3. Other services read profile via `GET /api/company/{id}`
4. User updates profile via `PUT /api/company/{id}`
5. User deletes profile via `DELETE /api/company/{id}`
