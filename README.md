# Personal AI Calendar

Dockerized full-stack calendar app with a FastAPI backend, React frontend, and PostgreSQL database.

## Project structure

```text
root/
├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── index.html
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## Services

- `backend`: FastAPI API with JWT auth, Google OAuth, chat parsing, and Google Calendar sync
- `frontend`: React app with login, register, dashboard, chat UI, task list, and calendar view
- `db`: PostgreSQL 15 with a persistent Docker volume

## Docker run

1. Copy `.env.example` to `.env`.
2. Fill in your Google OAuth credentials and secret key.
3. Start everything:

```bash
docker-compose up --build
```

## Local URLs

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8000](http://localhost:8000)
- PostgreSQL: `localhost:5432`

## Local development without Docker

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

- `DATABASE_URL=postgresql://postgres:postgres@db:5432/calendar_app`
- `SECRET_KEY=supersecret`
- `ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `JWT_ALGORITHM=HS256`
- `GOOGLE_CLIENT_ID=your_client_id`
- `GOOGLE_CLIENT_SECRET=your_secret`
- `GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback`
- `GOOGLE_OAUTH_SCOPE=openid email profile https://www.googleapis.com/auth/calendar`
- `FRONTEND_SUCCESS_URL=http://localhost:5173/dashboard`
- `BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- `VITE_API_URL=http://localhost:8000`

## Deployment

### Render

- Deploy PostgreSQL using Render Postgres.
- Deploy the backend as a web service from `backend/`.
- Set environment variables from `.env.example`, replacing local values with Render service values.
- Deploy the frontend as a static site from `frontend/`.
- Set `VITE_API_URL` to the public backend URL before the frontend build.
- Update `FRONTEND_SUCCESS_URL`, `BACKEND_CORS_ORIGINS`, and `GOOGLE_REDIRECT_URI` to your public domains.

### Railway

- Create a PostgreSQL service in Railway.
- Deploy the backend from `backend/` as a web service.
- Deploy the frontend from `frontend/` or publish the built static assets separately.
- Configure all secrets in Railway variables.
- Point `DATABASE_URL` to Railway Postgres and update public callback/CORS URLs.

## Production improvements included

- Backend Docker image runs with `gunicorn` plus `uvicorn` workers
- Frontend Docker image builds static assets and serves them with `serve`
- FastAPI CORS is enabled through environment-configurable origins
- Environment-driven URLs are ready for local and hosted deployments

## GitHub Actions

The optional CI workflow in `.github/workflows/docker.yml` builds both Docker images on pushes to `main` and on pull requests.
