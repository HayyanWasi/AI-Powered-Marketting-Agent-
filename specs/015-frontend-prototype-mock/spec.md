# Feature Specification: Frontend Prototype (Mocked Data)

**Feature Branch**: `015-frontend-prototype-mock`
**Created**: 2026-07-19
**Status**: Draft
**Input**: Responsive Next.js frontend providing an AI-first workspace where users create marketing campaigns through natural conversation. The frontend focuses on prompt-driven interaction, visual campaign generation, company profile management, conversation history, and seamless integration with backend AI services.

## User Scenarios & Testing

### User Story 1 — AI Campaign Workspace (Priority: P1)

As a marketer, I want to describe my campaign in natural language so that the AI can generate a complete marketing campaign without requiring me to fill out complex forms.

**Why this priority**: The prompt workspace is the core interaction model. Users must be able to initiate campaign generation immediately.

**Independent Test**: Load the landing page, verify it opens directly to the prompt workspace, enter text, submit, and verify the canvas opens and displays the generation animation and campaign.

**Acceptance Scenarios**:
- **Given** a user navigates to the application, **When** the app loads, **Then** the landing page opens directly into the prompt workspace.
- **Given** the user is in the workspace, **When** they type a campaign request and submit the prompt, **Then** the canvas opens automatically.
- **Given** the prompt is submitted, **When** the canvas opens, **Then** the AI generation animation begins.
- **Given** the animation completes, **When** the mock processing is done, **Then** the generated campaign appears inside the canvas.

---

### User Story 2 — Conversation History (Priority: P1)

As a marketer, I want every campaign conversation to be saved so I can continue working later.

**Why this priority**: State preservation allows users to manage multiple distinct campaigns without losing progress.

**Independent Test**: Create multiple campaigns via prompts, verify they appear in the sidebar, click a previous conversation, and verify the canvas and prompt history are restored.

**Acceptance Scenarios**:
- **Given** the user clicks "+ New Chat", **When** the action completes, **Then** a fresh conversation workspace is created and the canvas clears.
- **Given** the user has submitted prompts previously, **When** they view the sidebar, **Then** previous conversations appear in the recent list.
- **Given** the user selects a previous conversation from the sidebar, **When** the selection is made, **Then** the entire canvas and prompt history are restored for that specific campaign.

---

### User Story 3 — Company Profile (Priority: P1)

As a marketer, I want to maintain company information once so that every future campaign automatically uses my brand information.

**Why this priority**: Eliminates repetitive data entry and anchors the mock generation process with contextual business data.

**Independent Test**: Navigate to the Company Profile via the sidebar, edit details, save, create a new campaign, and verify the updated profile context persists.

**Acceptance Scenarios**:
- **Given** the user is on the Company Profile view, **When** they enter information, **Then** they can create and save their company profile.
- **Given** a company profile exists, **When** the user modifies the data, **Then** the profile updates successfully.
- **Given** a company profile exists, **When** the user selects delete, **Then** the profile is removed.
- **Given** an active company profile exists, **When** a user generates a campaign, **Then** the profile is automatically used for campaign generation context.
- **Given** the prompt workspace is loaded, **When** viewed by the user, **Then** the active company profile is displayed above the prompt input so the user always knows which company the AI is using.

---

### User Story 4 — Campaign Canvas (Priority: P1)

As a marketer, I want generated campaign assets to appear inside a visual canvas so I can review and compare results.

**Why this priority**: The visual output is the immediate value delivered to the user. It must be structured for easy review.

**Independent Test**: Submit a prompt, wait for generation, and verify that images, captions, and copy are rendered distinctly within the canvas layout.

**Acceptance Scenarios**:
- **Given** a campaign has been generated, **When** the user views the canvas, **Then** generated images appear in the canvas.
- **Given** images are displayed, **When** the user reviews the assets, **Then** generated captions appear with their corresponding images.
- **Given** the output exceeds the viewport, **When** the user interacts with the canvas, **Then** they can scroll through all generated results.

---

### User Story 5 — AI Generation Animation (Priority: P2)

As a marketer, I want to see visual progress while AI builds my campaign so I know work is happening.

**Why this priority**: Generation takes time. Visual feedback prevents user abandonment and sets expectations for the AI workflow.

**Independent Test**: Submit a prompt and observe the canvas immediately showing sequential agent stages before displaying the final output.

**Acceptance Scenarios**:
- **Given** the user submits a prompt, **When** processing begins, **Then** the canvas opens immediately and the workflow animation starts.
- **Given** the animation is running, **When** mock execution proceeds, **Then** agent stages appear one by one.
- **Given** all mock stages complete, **When** the sequence ends, **Then** the animation finishes and the campaign is displayed.

---

### User Story 6 — Refine Campaign (Priority: P2)

As a marketer, I want to refine and iterate on my campaign using follow-up prompts so I can adjust specific elements like tone, formatting, or imagery without starting over.

**Why this priority**: AI generation is iterative. Users must be able to continue the conversation to hone the final output.

**Independent Test**: Generate an initial campaign, submit a follow-up prompt (e.g., "make it more premium"), and verify new outputs are added to the existing workspace without wiping prior context.

**Acceptance Scenarios**:
- **Given** a generated campaign is displayed, **When** the user submits a follow-up prompt, **Then** generation continues using the active campaign context.
- **Given** the AI finishes generating the refinement, **When** the results are displayed, **Then** each new generation is appended to the existing workspace instead of replacing it.
- **Given** generation is complete, **When** the user interacts with the workspace, **Then** the canvas remains editable and previous generated assets remain visible.

---

### Edge Cases

- **Rapid Submissions**: Submitting a prompt while an animation is already running is blocked; the input/submit button is disabled until generation completes.
- **Empty History**: If no previous conversations exist, the sidebar history section displays an empty state ("No recent conversations").
- **Mobile Navigation**: On viewports under 768px, the sidebar collapses. A hamburger menu or bottom tab bar exposes access to New Chat, History, and Profile without obstructing the prompt workspace.
- **Long conversations**:
When conversations exceed the viewport, prompt history and canvas remain independently scrollable.

- Prompt submitted while no company profile exists. The frontend should continue generation using only the prompt and display that no company profile is currently active.

## Requirements

### Functional Requirements

- **FR-001**: Landing page MUST open directly into the AI prompt workspace.
- **FR-002**: User MUST be able to create campaigns using natural language.
- **FR-003**: The first submitted prompt MUST create a new conversation. Subsequent prompts MUST continue the active conversation until the user starts a new chat.
- **FR-004**: Conversation history MUST appear in the sidebar.
- **FR-005**: Selecting a conversation MUST restore the previous canvas.
- **FR-006**: The active Company Profile MUST automatically be supplied to campaign generation requests.
- **FR-007**: Generated campaigns MUST appear inside a canvas.
- **FR-008**: Canvas MUST support multiple generated images.
- **FR-009**: AI generation MUST display progress animation.
- **FR-010**: The frontend MUST use mock service implementations during development. during development.
- **FR-011**: Mock services MUST strictly mirror backend contracts.
- **FR-012**: Frontend MUST be responsive.
- **FR-013**: Frontend MUST support light and dark glassmorphism themes.
- **FR-014**: The application MUST provide a persistent sidebar containing: 
        - + New Chat,
        - Recent Conversations
        - Company Profile
        - Account
        - Settings
- **FR-015**: The canvas MUST remain visible while users continue prompting.
- **FR-016**:
Follow-up prompts MUST append new campaign concepts to the existing canvas instead of replacing previous results.
- **FR-017**:
The prompt input and submit button MUST be disabled while generation is in progress.

### Constraints

- UI must be fully responsive across desktop, tablet, and mobile.
- Built with Next.js + React.
- Use glassmorphism design.
- The frontend MUST communicate exclusively through API service interfaces. Components must never directly access mocked data sources. 
- Mock services must strictly mirror backend contracts.
- UI components MUST depend only on service interfaces.
- Service implementations may be swapped between mock and production APIs without modifying UI components.

### UI Workspace

- **Workspace State**: Represents the current mode of the application: Idle
,Generating
,Awaiting Prompt
,active
- **Conversation**: Represents one complete campaign workspace including: user prompts, generated campaign concepts, selected concept, generated assets, and canvas state.
- **Prompt**: Keep Prompt as only user messages.
Include:
- prompts
- campaign concepts

- **Canvas**: 
Represents the infinite visual workspace where generated campaign assets accumulate during the conversation.
- **Campaign Concept**: Contains generated images, headlines, captions, CTA, marketing copy, and generation metadata.
- **Company Profile**: Persistent company information reused across campaigns.
- **Mock API Service**: Development-only service returning fake backend data matching production API contracts.

## Dependencies and Assumptions

- **No backend dependency**: The prototype uses mocked data exclusively. All services are self-contained and require no network calls.
- **Mock service interface parity**: Mock services implement the exact interface contracts that real API services will use.
- **Session-only data persistence**: Mock data is generated fresh on each page load and is not persisted across browser sessions.
- **Mobile-first approach**: Responsive design starts from the smallest viewport.
- **No authentication**: The prototype operates without any login barrier. All views are accessible immediately.
- **React with existing stack**: The prototype uses the React framework and build tooling already established in the project.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The initial prompt workspace loads within 2 seconds.
- **SC-002**: The generation animation begins within 500 ms of prompt submission.
- **SC-003**: Generated mock campaign renders within 2 seconds of animation completion.
- **SC-004**: Conversation switching restores previous workspace in under 500 ms.
- **SC-005**: Replacing mock service implementations with API service implementations requires no changes to UI components.
- **SC-006**: Users can continue an existing conversation without losing previously generated assets.