# AI Marketing Automation System — Technical Design Document

**Version:** 1.0  
**Status:** In Progress (Reviewing Agents 1 & 2)

---

## Agent 1: Organization Knowledge Base — Technical Implementation

### 1. Database & Vector Store Strategy
To maintain a clean infrastructure and stay cost-efficient, we will use **Supabase** as our single unified storage backend. Supabase provides PostgreSQL for structured data and supports the **pgvector** extension for vector/RAG storage. This eliminates the need to pay for or maintain a separate database (like Pinecone/Qdrant).

#### Relational Tables (PostgreSQL)

```sql
-- Events Table
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name VARCHAR(255) NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    venue VARCHAR(255) NOT NULL,
    registration_link TEXT NOT NULL,
    ticket_price VARCHAR(50) DEFAULT 'Free',
    sponsors JSONB DEFAULT '[]'::jsonb,
    agenda JSONB DEFAULT '[]'::jsonb,
    target_platforms VARCHAR(50)[] NOT NULL DEFAULT '{}', -- e.g., {'LinkedIn', 'Twitter'}
    run_ads BOOLEAN NOT NULL DEFAULT FALSE, -- cost-saving toggle
    campaign_status VARCHAR(50) DEFAULT 'Draft',
    post_schedule_status VARCHAR(50) DEFAULT 'Idle',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Guest Queue (Linked to Events)
CREATE TABLE event_guests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    guest_name VARCHAR(255) NOT NULL,
    linkedin_url TEXT,
    twitter_url TEXT,
    enrichment_status VARCHAR(50) DEFAULT 'Pending'
);
```

#### Vector Table (pgvector)

```sql
-- RAG Chunk Store for Long-Term Org Data
CREATE TABLE org_knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    metadata JSONB, -- stores source (PDF page number, section name)
    embedding VECTOR(1536) -- 1536 is standard size for OpenAI embeddings
);
```

---

### 2. PDF Processing & Ingestion Pipeline
When the user uploads a `Company_Profile.pdf` through the UI:

1. **Text Extraction:** Python library `pypdf` extracts raw text from the document page-by-page.
2. **Chunking:** `RecursiveCharacterTextSplitter` from LangChain splits the text:
   - Chunk Size: `800` characters
   - Chunk Overlap: `100` characters (ensures text doesn't lose context between splits)
3. **Vector Embeddings:** The system calls OpenAI’s `text-embedding-3-small` (highly cost-efficient, $0.02 per 1M tokens) or uses a free offline model like `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) to generate vector embeddings.
4. **Storage:** The text chunk and its vector coordinates are saved to the `org_knowledge_chunks` table in Supabase.

---

### 3. Event Creation UI (No-Code/Low-Code interface)
We will build a simple, clean form using **Streamlit** (an open-source Python framework that is completely free to run and host). 
- It will feature simple input fields for Event Name, Venue, Date, Registration Link, and a dynamic input list for Sponsor details and Guest LinkedIn URLs.
- The Form will directly insert rows into the Supabase database.

---

## Agent 2: Guest Research Agent — Technical Implementation

### 1. Data Retrieval Method (Scraper-Free & Key-Free API)
Instead of building dynamic browser automation which frequently breaks due to bot-detection, we will use a **Search Engine API Query** pattern to fetch public index data.

#### Search Execution (Python code concept)
We will use the free python library `duckduckgo-search` to query DuckDuckGo API (which does not require a registration key and has no cost).

```python
from duckduckgo_search import DDGS

def fetch_snippets(query: str, max_results: int = 5):
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
        return [
            {
                "title": r["title"],
                "snippet": r["body"],
                "url": r["href"]
            }
            for r in results
        ]
```

---

### 2. Iterative Search Logic (Two-Step Search)

#### Step 1: Discovery Query
The agent generates a query focused on the guest’s primary LinkedIn index:
`query = f"site:linkedin.com/in/ \"{guest_name}\""`
- This retrieves the public snippet stored on search engines. It bypasses LinkedIn's login screen entirely because the request is sent to DuckDuckGo, not LinkedIn.

#### Step 2: Dynamic Query Expansion
An LLM (e.g., Google Gemini 1.5 Flash via free developer key, or OpenAI GPT-4o-mini) parses the discovery snippets and extracts keywords (e.g., "AI Teacher", "NED University", "Founder of Company X"). It then automatically triggers follow-up queries:
- Query A: `f"\"{guest_name}\" \"achievement\" OR \"award\""`
- Query B: `f"\"{guest_name}\" \"quote\" OR \"interview\""`
- Query C: `f"\"{guest_name}\" speech OR YouTube"`

---

### 3. Synthesis & Fact Verification
All retrieved text snippets from the searches are combined into a single text block. We pass this block to the LLM with a strict JSON format prompt:

```json
{
  "name": "Guest Name",
  "current_designation": "Current Role (extracted chronologically)",
  "company": "Company Name",
  "bio": "Comprehensive biography",
  "achievements": ["Achievement 1", "Achievement 2"],
  "speaking_topics": ["Topic 1", "Topic 2"],
  "famous_quotes": ["Quote 1", "Quote 2"]
}
```

#### Hallucination Guardrails:
The LLM is prompted with a strict constraint: **"You are a factual auditor. Do not output any claim unless it is mentioned in at least two separate search snippets."**

---

### 4. Media/Image Retrieval
- To extract high-quality headshots or stage photos of the guest, we run a free image search query using the DuckDuckGo Image API: `ddgs.images(f"\"{guest_name}\" professional portrait")`.
- The top 3 clean image URLs are stored in the database.

---

## Agent 4: Marketing Strategy Agent — Technical Implementation

### 1. Database Schema
We will create a structured table to store the generated strategy brief, allowing simple edits and status changes via the UI.

```sql
CREATE TABLE campaign_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    core_positioning_hook TEXT NOT NULL,
    messaging_pillars JSONB NOT NULL, -- array of pillars with angles and descriptions
    objection_handles JSONB NOT NULL, -- key-value pairs matching objections to arguments
    cta_hierarchy JSONB NOT NULL, -- phase-specific action targets
    approval_status VARCHAR(50) DEFAULT 'Pending_Review', -- Pending_Review, Approved
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2. Context Aggregation & Prompt Ingestion
When the Strategy Agent is triggered, a backend Python function aggregates data from both Supabase (DB) and pgvector (RAG):

```python
# 1. Fetch Event Details from SQL DB
event_details = db.fetch_event(event_id)

# 2. Fetch Guest Profiles from SQL DB
guest_profiles = db.fetch_event_guests(event_id)

# 3. Retrieve Brand Tone & Guidelines from pgvector (RAG)
brand_guidelines = vector_store.similarity_search("brand voice tone guidelines mission", k=3)
```

---

### 3. Structured Output & Prompt Strategy
We send these aggregated contexts into the LLM (Gemini 1.5 Flash) using a structured output model (such as Pydantic) to guarantee clean JSON formatting.

#### System Prompt Blueprint:
```
You are an expert Chief Marketing Officer. Your task is to design a high-converting Strategy Brief for an event.

Use the specific marketing/copywriting frameworks selected by the user:
[USER DEFINED FRAMEWORKS GO HERE - e.g., PAS, AIDA, StoryBrand, etc.]

Apply these frameworks to design the Messaging Pillars, map tone intensity, and handle target audience objections.

Context:
- Brand voice guidelines: {brand_guidelines}
- Event details: {event_details}
- Speaker Profile: {guest_profiles}

Output structure MUST strictly conform to the following JSON schema:
{
  "core_positioning_hook": "string",
  "messaging_pillars": [
    {"pillar_name": "string", "angle": "string", "description": "string"}
  ],
  "objection_handles": {
    "objection": "counter_argument"
  },
  "cta_hierarchy": {
    "phase_1_awareness": "string",
    "phase_3_conversion": "string"
  }
}
```

---

### 4. Human-in-the-Loop UI Integration
Using **Streamlit**, the strategy is rendered in text boxes:
- Streamlit fetches the row where `event_id = X` and `approval_status = 'Pending_Review'`.
- The user can edit the fields directly in Streamlit text inputs.
- When the user clicks the "Approve Strategy" button:
  - The UI runs an `UPDATE campaign_strategies SET approval_status = 'Approved', core_positioning_hook = [user_edited_value] WHERE event_id = X`.
  - This status change acts as the trigger for the **Campaign Planner Agent** to begin its execution.

---

## Agent 5: Campaign Planner Agent — Technical Implementation

### 1. Database Schema (Campaign Schedule)
This table stores the daily campaign blueprints and links them to the finalized content formats.

```sql
CREATE TABLE campaign_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    campaign_date DATE NOT NULL,
    campaign_phase VARCHAR(50) NOT NULL, -- e.g., Awareness, Authority, Urgency
    daily_theme TEXT NOT NULL,           -- e.g., "Guest Achievement Spotlight"
    allocated_platform VARCHAR(50) NOT NULL, -- e.g., LinkedIn, Instagram
    format_type VARCHAR(50) NOT NULL,        -- e.g., Feed Post, Story, Ad
    raw_copy_id UUID,                     -- references the generated text draft
    published_status VARCHAR(50) DEFAULT 'Draft' -- Draft, Scheduled, Published
);
```

---

### 2. Campaign Blueprinting (Filtering & Planning)
The Python function reads the selected platforms and campaign parameters to construct the blueprint.

```python
# 1. Fetch event parameters
event_data = db.query("SELECT target_platforms, run_ads, event_date FROM events WHERE id = ?", event_id)
target_platforms = event_data['target_platforms']
run_ads = event_data['run_ads']

# 2. If 'run_ads' is False, skip generating ad components entirely to save tokens and costs.
```

---

### 3. Structured Blueprint Generation (JSON Schema)
The agent outputs a JSON blueprint that maps themes to dates, strictly matching the active platforms array.

#### System Prompt Instruction:
```
Generate a daily Campaign Blueprint for the event starting from {days_before} up to the event date.
Strictly filter all outputs to include ONLY the following platforms: {target_platforms}
If run_ads is False, do NOT generate any ad templates.

Output JSON Format:
[
  {
    "date": "YYYY-MM-DD",
    "phase": "Authority",
    "theme": "Guest speaking topic breakdown",
    "platform": "LinkedIn",
    "suggested_format": "Feed Post"
  }
]
```

### 4. Database Storage & Grid Mapping
The generated JSON blueprint is parsed, and empty calendar slots are created directly in the `campaign_schedules` table with the status `'Pending_Generation'`.

The Generation Agent (Agent 7) queries this table to know exactly what format and platform it is writing for:

```python
# Fetch planned slots that need content
pending_slots = db.query("SELECT * FROM campaign_schedules WHERE published_status = 'Pending_Generation'")

# Fetch planned slots that need content
pending_slots = db.query("SELECT * FROM campaign_schedules WHERE published_status = 'Pending_Generation'")

# For each slot, trigger the Content Generator with platform-specific instructions (e.g. max 280 chars if platform is Twitter).
```

---

## Agent 7: Content Generation Agent — Technical Implementation

### 1. Database Schema (Content Drafts)
Stores the generated text variants linked to the campaign schedules.

```sql
CREATE TABLE content_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES campaign_schedules(id) ON DELETE CASCADE,
    variant_a_story TEXT NOT NULL,
    variant_b_value TEXT NOT NULL,
    variant_c_question TEXT NOT NULL,
    selected_variant VARCHAR(1) DEFAULT NULL, -- 'A', 'B', or 'C' (set by human reviewer)
    image_prompt TEXT NOT NULL,               -- prompt for image generation agent
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2. Dynamic Trend Retrieval & Context Injection
Before sending a prompt to the LLM, the system retrieves trending keywords to enrich the writing:

```python
from duckduckgo_search import DDGS

def get_trends(theme: str) -> str:
    # 1. Search for current hot topics related to the event theme
    query = f"{theme} trending topics 2026"
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=3)
        # 2. Join the snippets to pass as context
        return " | ".join([r["body"] for r in results])
```

---

### 3. Structured Generation (Pydantic Output Model)
We pass the theme context, brand tone, guest bio, and trend snippets to Gemini 1.5 Flash. We enforce a structured JSON schema containing the 3 copy variants.

#### System Prompt Blueprint:
```
You are an expert Copywriter. Your task is to write a post for the platform: {platform} (Format: {format_type}).

Core Instructions:
1. Adopt the Tone Profile for this platform:
   - LinkedIn: Professional & Insightful (use line-breaks for mobile).
   - Instagram: Casual, Friendly & Engaging (use emojis and hashtags).
   - Twitter/X: Punchy & Bold (strictly under 280 characters).
2. Integrate these current trends if they naturally fit: {trend_snippets}
3. Factual constraint: Use only details verified in Guest Profile: {guest_profile}

Generate exactly three variants of the post:
- Variant A: A story-driven hook about the guest or organization.
- Variant B: A direct-value bullet list of what attendees will gain.
- Variant C: An interactive question hook driving discussion.

Also generate a highly creative image prompt ("image_prompt") that represents this post.
```

#### JSON Output Schema:
```json
{
  "variant_a_story": "string",
  "variant_b_value": "string",
  "variant_c_question": "string",
  "image_prompt": "string"
}
```

---

### 4. Human Approval Interface
* In **Streamlit**, the reviewer sees all three variants rendered side-by-side.
* Radio buttons allow the user to select the best option ('A', 'B', or 'C') and make inline edits if needed.
* Saving updates the `selected_variant`, locks the copy, and updates the `published_status` in `campaign_schedules` to `'Pending_Publish'`.

---

## Agent 8: Asset Generation Agent — Technical Implementation

### 1. Database Schema Updates (Handling Optional Uploads)
We modify our schema to support optional URLs for user-uploaded custom assets (custom guest photos and custom base background banners).

```sql
-- Update event_guests to allow manual photo uploads
ALTER TABLE event_guests ADD COLUMN custom_guest_photo_url TEXT DEFAULT NULL;

-- Update campaign_schedules to allow manual base banner uploads per post/date
ALTER TABLE campaign_schedules ADD COLUMN custom_base_banner_url TEXT DEFAULT NULL;
ALTER TABLE campaign_schedules ADD COLUMN final_image_url TEXT DEFAULT NULL;
```

---

### 2. Pollinations.ai API Call (Free AI Art)
If the system needs to generate an abstract or conceptual background for a post (Mode A), it calls the Pollinations.ai image generator. This API is completely free and requires no keys:

```python
import urllib.parse
import requests

def generate_free_art(prompt: str, width: int = 1080, height: int = 1080) -> bytes:
    # 1. Encode prompt for URL safety
    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/p/{safe_prompt}?width={width}&height={height}&nologo=true"
    
    # 2. Fetch the generated image bytes
    response = requests.get(url)
    if response.status_code == 200:
        return response.content  # Returns raw PNG/JPEG image data
    raise Exception("Image generation failed")
```

---

### 3. Image Overlay and Text Rendering (Python Pillow Library)
This script demonstrates how Python's open-source `Pillow` library handles text rendering and automatic logo positioning locally for **$0 cost**.

```python
from PIL import Image, ImageDraw, ImageFont
import io

def generate_banner(background_bytes: bytes, guest_photo_bytes: bytes, event_title: str, date_text: str, org_logo_bytes: bytes) -> bytes:
    # 1. Load background image (could be custom banner upload OR Pollinations art)
    background = Image.open(io.BytesIO(background_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(background)
    
    # 2. Overlay Org Logo at exact coordinates (top-left)
    logo = Image.open(io.BytesIO(org_logo_bytes)).convert("RGBA")
    logo.thumbnail((150, 150)) # Resize logo
    background.paste(logo, (50, 50), logo) # Coordinates (50, 50)
    
    # 3. If Mode B (Guest Photo Override) is active, overlay guest headshot
    if guest_photo_bytes:
        guest_img = Image.open(io.BytesIO(guest_photo_bytes)).convert("RGBA")
        guest_img.thumbnail((300, 300))
        # Paste guest photo in the center/designated circle coordinates
        background.paste(guest_img, (390, 300), guest_img)
        
    # 4. Render Event Details (Text overlay)
    font_title = ImageFont.load_default() # Replace with custom ttf font files for brand alignment
    draw.text((50, 800), event_title, fill="white", font=font_title)
    draw.text((50, 900), date_text, fill="yellow", font=font_title)
    
    # 5. Export final composite image as bytes to store in Supabase Storage
    output = io.BytesIO()
    background.save(output, format="PNG")
    return output.getvalue()
```

---

* Rendered PNG assets are saved to Supabase Storage buckets.
* The public URL is generated and saved to `campaign_schedules.final_image_url`.
* This URL is passed directly to the Scheduler API (Buffer) to publish.

---

## Agent 9: Scheduler, Publisher & Tracking Agent — Technical Implementation

### 1. Database Schema Updates (Tracking & Lifecycle)
We expand the schema to track publication state, Buffer update IDs, and post engagement metrics.

```sql
-- Track Buffer identification and metrics
ALTER TABLE campaign_schedules ADD COLUMN buffer_update_id VARCHAR(255) DEFAULT NULL;
ALTER TABLE campaign_schedules ADD COLUMN metrics_impressions INTEGER DEFAULT 0;
ALTER TABLE campaign_schedules ADD COLUMN metrics_clicks INTEGER DEFAULT 0;
ALTER TABLE campaign_schedules ADD COLUMN metrics_interactions INTEGER DEFAULT 0; -- Likes + Comments + Shares
```

---

### 2. The Feedback Loop Logic (Regenerate with Comments)
When the user clicks "Needs Fix" in the Streamlit UI and writes a comment, the backend triggers the **Content Generation Agent** again, appending the user's critique to the prompt history:

```python
def regenerate_with_feedback(post_id: str, user_comment: str):
    # 1. Fetch the original draft copy and prompt parameters
    original_draft = db.query("SELECT * FROM content_drafts WHERE id = ?", post_id)
    
    # 2. Construct the feedback prompt for Gemini/LLM
    feedback_prompt = f"""
    The user reviewed your original post and requested adjustments.
    
    Original Copy: {original_draft['selected_copy_text']}
    User's Feedback/Instructions: {user_comment}
    
    Regenerate the post. Keep the brand tone and platform constraints, but make the changes requested by the user.
    """
    
    # 3. Call the LLM to get the updated copy and update the database status to 'Pending_Review'
    updated_copy = call_gemini(feedback_prompt)
    db.query("UPDATE content_drafts SET variant_a_story = ?, is_approved = FALSE WHERE id = ?", updated_copy, post_id)
    db.query("UPDATE campaign_schedules SET published_status = 'Pending_Review' WHERE raw_copy_id = ?", post_id)
```

---

### 3. Buffer API Integration (Scheduling Payload)
When a post status changes to `Scheduled`, the system sends a POST request to Buffer's API to add the post to the queue.

```python
import requests

def schedule_via_buffer(profile_id: str, access_token: str, post_text: str, image_url: str, scheduled_time: str):
    url = "https://api.bufferapp.com/1/updates/create.json"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "profile_ids[]": [profile_id],
        "text": post_text,
        "media[photo]": image_url,
        "scheduled_at": scheduled_time, # ISO timestamp (e.g., '2026-07-25T09:00:00Z')
        "shorten": "false"
    }
    
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json() # Returns Buffer update ID payload
    raise Exception(f"Buffer API Error: {response.text}")
```

---

### 4. Post-Publishing Metrics Sync (Analytics Tracking)
A periodic background worker syncs the metrics from Buffer's updates interactions endpoint for published posts:

```python
def sync_post_metrics(buffer_update_id: str, access_token: str, schedule_id: str):
    # Call Buffer's interactions endpoint for the given post/update ID
    url = f"https://api.bufferapp.com/1/updates/{buffer_update_id}/interactions.json"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        
        # Parse metrics safely
        clicks = data.get("clicks", 0)
        likes = data.get("likes", 0) + data.get("favorites", 0)
        comments = data.get("comments", 0)
        impressions = data.get("impressions", 0) or data.get("reach", 0) or 0
        
        # Update PostgreSQL database
        db.query(
            """
            UPDATE campaign_schedules 
            SET metrics_impressions = ?, metrics_clicks = ?, metrics_interactions = ? 
            WHERE id = ?
            """,
            impressions, clicks, (likes + comments), schedule_id
        )
```

---

## Agent Orchestration: LangGraph State Machine

We will use **LangGraph** (Python) to define the state, node workflows, and state transitions of our agent network. LangGraph is ideal here because it natively supports state management, cyclic loops (feedback loops), and human-in-the-loop interrupts.

### 1. LangGraph State Definition
The graph state will keep track of the active event, the generated strategy, the calendar grid, and the approval status.

```python
from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    event_id: str
    target_platforms: List[str]
    run_ads: bool
    guest_profiles: List[Dict[str, Any]]
    strategy_brief: Dict[str, Any]
    campaign_grid: List[Dict[str, Any]]
    generation_status: str  # e.g., "Pending_Strategy", "Pending_Calendar", "Approved"
    error_log: List[str]
```

---

### 2. Node & Workflow Graph
The orchestration logic connects our agents as nodes in a graph:

```python
from langgraph.graph import StateGraph, END

# Initialize the State Graph
workflow = StateGraph(AgentState)

# Define Node Operations
def research_node(state: AgentState):
    # Triggers Agent 2 to enrich guest profiles using search snippets
    return {"guest_profiles": run_guest_research(state["event_id"])}

def strategy_node(state: AgentState):
    # Triggers Agent 4 to generate the Campaign Strategy Brief
    return {"strategy_brief": generate_marketing_strategy(state)}

def planner_node(state: AgentState):
    # Triggers Agent 5 to generate the empty Campaign Blueprint slots grid
    return {"campaign_grid": create_campaign_slots(state)}

def generation_node(state: AgentState):
    # Triggers Agent 7 & 8 to generate copy variants and overlay images
    generate_content_and_assets(state)
    return {}

# Register Nodes to Graph
workflow.add_node("research", research_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("planner", planner_node)
workflow.add_node("generation", generation_node)

# Define Edges and Conditional Logic
workflow.set_entry_point("research")
workflow.add_edge("research", "strategy")

# Human-in-the-Loop Interrupt after strategy and planner runs
# The state pauses here to wait for Streamlit UI approval updates.
workflow.add_edge("strategy", "planner")
workflow.add_edge("planner", "generation")
workflow.add_edge("generation", END)

# Compile Graph
app = workflow.compile()
```

---

### Summary of Suggested Free/Low-Cost Technical Stack

| Component | Technical Choice | Cost |
|-----------|------------------|------|
| **Agent Orchestration** | **LangGraph** (Python) | $0 (Open-source framework) |
| **Database & Vector Store** | Supabase (PostgreSQL + pgvector) | $0 (Free Tier covers up to 500MB) |
| **Search Engine API** | `duckduckgo-search` Python library | $0 (Unlimited, No API key required) |
| **Embeddings Generator** | OpenAI `text-embedding-3-small` | ~$0.0001 (Fraction of a cent per document) |
| **Core Reasoning / parsing**| Google Gemini 1.5 Flash API | $0 (Free Developer Tier) |
| **Frontend Form / Review UI** | Streamlit (Python UI) | $0 (Open-source) |
| **Image Generation API** | Pollinations.ai API | $0 (Open-source, no key required) |
| **Image Manipulation Lib** | Pillow (PIL) & html2image (Python) | $0 (Open-source) |
| **Publishing & Tracking API**| Buffer API | $0 (Free Tier covers 3 channels & 10 posts) |




