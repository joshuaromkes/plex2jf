Core Design Principles
Tech Stack 
GitHub - Ravenc.... · GitHub

Frontend: React.js with TypeScript
Backend: .NET (C#)
Build tooling: Webpack/Babel with PostCSS
State management: Redux-based store architecture
Visual Design

Dark-first theme — Deep slate/blacks as the default, not an afterthought
Clean, information-dense layout — No wasted space, but not cramped
Consistent color coding — Status indicators use predictable colors (green = good/active, red = missing/problem, blue = monitored, gray = unmonitored)
Layout Structure
Persistent Left Sidebar Navigation

Collapsible sections (Movies/Series, Activity, Wanted, Calendar, Settings, System)
Active state highlighting
Icon + label for each section
Top Action Bar

Primary search input (prominent, always accessible)
View mode toggles: Poster | List/Overview | Table 
What would you ...selfhosted +1
Filter/sort controls
"Add New" primary action button
Key UI Patterns
Multiple View Modes 
What would you ...selfhosted +1

Poster View: Grid of artwork thumbnails with hover states showing key metadata (title, year, quality, monitored status)
Overview/List View: Compact rows with poster thumbnail + key details
Table View: Dense data grid with sortable columns, inline toggles (e.g., monitored checkbox directly in row)
Content Organization

Main library view shows all content with at-a-glance status (downloaded, missing, monitored)
"Activity" section shows queue/progress of current operations
"Wanted" section for missing content
"Discover" for browsing and adding new content
Modal-Heavy Interaction

Clicking an item opens a modal with full details, not a new page
Settings use tabbed modals or dedicated settings pages with sidebar sub-navigation
Forms use in-modal validation with save/cancel actions
Search & Filter

Real-time search as you type
Advanced filters (by quality profile, status, path, tags)
Persistent filter state
Component Conventions
Rounded corners on cards/posters (subtle, not excessive)
Hover effects reveal secondary actions
Progress bars for downloads/imports
Badge/pill components for quality labels, status tags
Toggle switches for boolean settings (not checkboxes)
Dropdown selects for enums (quality profiles, root folders)
Responsive Considerations
Desktop-first but functional on tablet
Sidebar collapses to hamburger on narrow screens
Poster grid reflows based on viewport
This design prioritizes functional density — power users can see and do a lot without digging through menus, while the visual hierarchy prevents overwhelming new users.