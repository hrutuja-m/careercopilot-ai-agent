"""Convenience entry point: `python run.py` from inside backend/.

Why this exists: frontend/index.html has CONFIG.API_BASE hardcoded to
http://localhost:8002, but the plain command `uvicorn main:app --reload`
starts on port 8000 by default. Nothing in the code enforces the two stay
in sync, so it's easy to start the backend on the "wrong" port and have the
whole app silently look broken (the frontend's offline banner) even though
the server is running fine. Run this instead of guessing the port flag.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
