# Build Your Own

A non-AI resume studio for user-authored content. This is independent of the
Review and AI Creator workflows; it makes no OpenAI, Gemini, MCP, or LangGraph calls.

## User flow

Open BUILD YOUR OWN in the workspace sidebar. Enter personal details, then use
the section tabs to add experience, education, projects, and labeled skill groups.
Add individual achievement points to each experience/project. All edits appear
immediately in the editing preview. Entries and points can be removed with undo.
Achievement points and coursework use a WYSIWYG bold and italic editor. Select
text and press B or I (or use Ctrl/Cmd+B and Ctrl/Cmd+I); formatting appears
inside the editor and instant preview immediately. Internally, the draft keeps
portable formatting markers so the compiled PDF, LaTeX, and editable Word export
all preserve the same emphasis. Bold important metrics, results, technologies,
or short phrases rather than entire bullets.
The browser saves the draft locally, including across reloads and workspace changes.
On shared devices, use Clear draft when finished. Drafts are not synced to accounts.

Send to review compiles the current draft into a temporary PDF, switches to the
Review Resume workspace, and submits that exact PDF to the existing multimodal
review workflow. Existing review job context and instructions are preserved.
The handoff uses no-store caching and its isolated workspace is removed afterward.

The exact Harshibar LaTeX preview compiles automatically 700 milliseconds after
editing pauses. In-flight previews are cancelled when newer edits arrive, and the
instant preview remains visible until the newest PDF is ready. The preview supports
page navigation and expansion without downloading; use the Expand button or click
the resume page itself. Prepare downloads creates PDF, LaTeX, and editable Word
artifacts from the current snapshot. Further edits hide outdated download links
until regenerated.

Add section creates named custom sections with entries and points. Drag handles
reorder sections, entries, and points; keyboard arrow keys also work. Ordering
persists with the draft and applies to every export. The preview's bottom-right
corner resizes the panel; double-click resets its size.

Word exports use Times New Roman and explicit single line spacing on both styles
and paragraphs for Google Docs import compatibility. Minimum point-based line
heights expanded during Google Docs conversion. Docker
includes Liberation Serif as a metric-compatible rendering font; this avoids
the wider DejaVu Serif substitution seen when Palatino is unavailable. The PDF
and editing preview retain their Palatino styling. Word remains editable and
can paginate differently after changes or when fonts are substituted elsewhere.

## Architecture

React ResumeBuilder component -> bounded BuilderDraft schema -> manual content
adapter -> shared LaTeX renderer/template -> isolated temporary workspace ->
restricted pdflatex compiler -> PNG preview or existing artifact store/download API.

The instant HTML preview follows the template's hierarchy and section order, but
is explicitly an editing approximation. The compiled PDF is the authority for
pagination, spacing, and final appearance. PDF rendering uses raw PNG responses,
not base64. Preview workspaces are removed after responding; exports are saved
before cleanup. Debouncing and request cancellation prevent older responses from
replacing the current preview or launching a build for every keystroke.

Limits: 12 entries per section, six points per experience/project, 700 characters
per point, 40 skills per group. Export requires completed core fields. User text
is escaped by the shared renderer; formatting accepts only **bold**,
*italic*, and ***bold italic*** markers. Arbitrary HTML and LaTeX are never
executed.

## Next phase

The separate draft contract can support section ordering, additional education
details, contact links, draft import/export, or authenticated
storage later without coupling the editor to AI generation. Review integration
can be offered explicitly later; manual content should never be silently rewritten.
