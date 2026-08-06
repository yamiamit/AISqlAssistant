# Deployment

Three free-tier services, deployed independently: **Neon** (app database), **Render** (backend API), **Vercel** (frontend).

## 1. Neon — app database

1. Create a project at [neon.tech](https://neon.tech).
2. Copy the connection string shown in the dashboard (starts `postgresql://...?sslmode=require`) — this becomes `APP_DATABASE_URL`. The app creates its own tables on startup (`Base.metadata.create_all`), so no manual migration step is needed.
3. Optionally create a **second** Neon project (or database) loaded with `database/schema.sql` + `database/seed_data.sql` to use as a demo target database — see `database/README.md`.

## 2. Render — backend

1. Push this repo to GitHub.
2. In Render, "New +" → "Blueprint", point it at the repo. It will detect `backend/render.yaml` automatically (or create a Web Service manually with root directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
3. Set these environment variables on the service:

   | Variable | Value |
   |---|---|
   | `APP_DATABASE_URL` | Neon connection string from step 1 |
   | `JWT_SECRET_KEY` | Render can auto-generate this (see `render.yaml`) |
   | `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
   | `OPENAI_API_KEY` | Your OpenAI key |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
   | `CORS_ORIGINS` | Your Vercel URL, e.g. `https://ai-sql-assistant.vercel.app` |
   | `SQL_STATEMENT_TIMEOUT_MS` | `10000` |
   | `SQL_DEFAULT_ROW_LIMIT` | `500` |

4. Deploy. Confirm `GET https://<your-service>.onrender.com/api/health` returns `{"status": "ok"}`.

## 3. Vercel — frontend

1. Import the repo in Vercel, set **root directory** to `frontend`.
2. It auto-detects Vite (`vercel.json` adds the SPA rewrite so client-side routes like `/app/chat/5` work on refresh).
3. Set the environment variable:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | Your Render URL, e.g. `https://ai-sql-assistant-api.onrender.com` |

4. Deploy. Once live, go back to Render and double-check `CORS_ORIGINS` matches the exact Vercel URL (including `https://`, no trailing slash).

## Notes

- Render's free tier spins down after inactivity — the first request after idling will be slow (~30-60s cold start). This is a known trade-off of free hosting, not an app bug.
- The encryption key and JWT secret must stay stable across deploys — regenerating either one invalidates existing sessions and stored database credentials, respectively.
- Neither Vercel nor Render needs Docker — both build directly from source using their native Python/Node buildpacks.
