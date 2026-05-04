from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import base64
import os
import uuid
import json

# Local import
try:
    from config import FB_APP_ID, FB_APP_SECRET, REDIRECT_URI, FB_USER_ACCESS_TOKEN
except ImportError:
    from .config import FB_APP_ID, FB_APP_SECRET, REDIRECT_URI, FB_USER_ACCESS_TOKEN

app = FastAPI(title="Facebook Poster Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel

class PostRequest(BaseModel):
    image_base64: str
    caption: str = ""

# Temporary storage for image and caption during OAuth flow
sessions = {}

@app.post("/prepare_post")
async def prepare_post(req: PostRequest):
    """Step 1: Save image/caption and generate a state for OAuth."""
    image_base64 = req.image_base64
    caption = req.caption
    
    print(f">>> [DEBUG] Received prepare_post. Image length: {len(image_base64)}")
    state = str(uuid.uuid4())
    
    # Store the data
    sessions[state] = {
        "image": image_base64,
        "caption": caption
    }
    
    # If we have a permanent token, we can skip the redirect and fetch pages now
    if FB_USER_ACCESS_TOKEN and len(FB_USER_ACCESS_TOKEN) > 10:
        async with httpx.AsyncClient() as client:
            try:
                pages_resp = await client.get(
                    "https://graph.facebook.com/v18.0/me/accounts",
                    params={"access_token": FB_USER_ACCESS_TOKEN}
                )
                pages_data = pages_resp.json()
                
                # Store page tokens in session
                sessions[state]["pages"] = pages_data.get("data", [])
                sessions[state]["user_token"] = FB_USER_ACCESS_TOKEN
                
                print(f">>> [DEBUG] Direct mode active. Fetched {len(sessions[state]['pages'])} pages.")
                return {"fb_session": state}
            except Exception as e:
                print(f">>> [ERROR] Failed to fetch pages with permanent token: {e}")
                # Fallback to OAuth if direct fetch fails? No, let's just return error for now.
                raise HTTPException(status_code=400, detail=f"Failed to fetch pages with permanent token: {e}")

    # Redirect URL for Facebook Login (Fallback if no permanent token)
    login_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth?"
        f"client_id={FB_APP_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"state={state}&"
        f"scope=public_profile,pages_manage_posts,pages_read_engagement"
    )
    
    return {"login_url": login_url}

@app.get("/callback")
async def callback(code: str, state: str):
    """Step 2: Facebook redirects here with a code."""
    if state not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session or session expired.")
    
    # We don't pop yet, because we need the data for the next step
    data = sessions[state]
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": FB_APP_ID,
                "redirect_uri": REDIRECT_URI,
                "client_secret": FB_APP_SECRET,
                "code": code,
            }
        )
        token_data = token_resp.json()
        
        if "access_token" not in token_data:
            return JSONResponse(status_code=400, content={"error": "Failed to get access token", "details": token_data})
        
        access_token = token_data["access_token"]
        
        # --- Step 3: Get User's Facebook Pages ---
        pages_resp = await client.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"access_token": access_token}
        )
        pages_data = pages_resp.json()
        
        # Store page tokens in session
        sessions[state]["pages"] = pages_data.get("data", [])
        sessions[state]["user_token"] = access_token
        
        # Redirect back to frontend for page selection
        return RedirectResponse(url=f"http://localhost:8080/index.html?fb_session={state}")

@app.get("/get_pages")
async def get_pages(fb_session: str):
    """Fetch the list of pages for selection (no tokens returned)."""
    if fb_session not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    pages = sessions[fb_session].get("pages", [])
    return [{"id": p["id"], "name": p["name"]} for p in pages]

class MultiPostRequest(BaseModel):
    fb_session: str
    page_ids: list[str]

@app.post("/post_multi")
async def post_multi(req: MultiPostRequest):
    """Post the image to multiple selected pages."""
    if req.fb_session not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session_data = sessions.pop(req.fb_session)
    image_data = session_data["image"]
    caption = session_data["caption"]
    all_pages = session_data["pages"]
    print(f">>> [DEBUG] post_multi - Received Page IDs: {req.page_ids}")
    
    # Map page_ids to tokens
    target_pages = [p for p in all_pages if str(p.get("id")) in [str(pid) for pid in req.page_ids]]
    print(f">>> [DEBUG] post_multi - Matched Target Pages: {[p['name'] for p in target_pages]}")
    
    if not target_pages:
        # Fallback to user profile if no pages selected
        if not req.page_ids:
            print(">>> [DEBUG] post_multi - No pages selected, falling back to profile")
            target_pages = [{"id": "me", "access_token": session_data["user_token"], "name": "My Profile"}]
        else:
            print(f">>> [DEBUG] post_multi - Requested IDs {req.page_ids} not found in session pages")
            raise HTTPException(status_code=400, detail="No valid pages found for selection.")

    # --- Upload Image to Facebook Pages ---
    if "," in image_data:
        header, encoded = image_data.split(",", 1)
    else:
        encoded = image_data
    
    img_bytes = base64.b64decode(encoded)
    
    results = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for page in target_pages:
            try:
                print(f">>> [DEBUG] post_multi - Posting to {page['name']} ({page['id']})...")
                post_resp = await client.post(
                    f"https://graph.facebook.com/v18.0/{page['id']}/photos",
                    params={
                        "access_token": page['access_token'],
                        "caption": caption
                    },
                    files={"source": ("image.png", img_bytes, "image/png")}
                )
                res_data = post_resp.json()
                print(f">>> [DEBUG] post_multi - Result for {page['name']}: {res_data}")
                results.append({"page": page["name"], "status": "success" if "id" in res_data else "error", "details": res_data})
            except Exception as e:
                print(f">>> [DEBUG] post_multi - Exception for {page['name']}: {e}")
                results.append({"page": page["name"], "status": "error", "details": str(e)})
    
    print(f">>> [DEBUG] post_multi - Final Results sent to browser: {results}")
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8101)
