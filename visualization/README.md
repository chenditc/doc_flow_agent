# Doc Flow Visualization System

A comprehensive web-based visualization system for monitoring and analyzing doc flow execution traces in real-time.

## Current Design (Phases 1-6 ✅ COMPLETED)

The visualization system is fully operational with the following architecture:

### **System Architecture**
- **Backend**: FastAPI server with REST API endpoints (`visualization/server/`)
- **Frontend**: Modular vanilla JavaScript SPA (`visualization/frontend/`)
- **Data Source**: JSON trace files in `traces/` directory
- **Testing**: Comprehensive test suite with backend, component, and integration tests
- **Real-time Monitoring**: File watcher with SSE streaming for live trace updates

### **Core Features**
- **Real-time Trace Selection**: Auto-loads latest trace on page load with manual override
- **Interactive Timeline**: Linear timeline view of task executions with status indicators
- **Detailed Phase Analysis**: Click any task to see phase-by-phase execution breakdown
- **Live Monitoring**: Real-time updates with auto-scroll and visual indicators
- **Comprehensive Error Handling**: Graceful handling of missing data and edge cases
- **Full Test Coverage**: 24+ passing tests covering API, components, and integration scenarios

### **User Interface Components**
1. **Trace Selector**: Dropdown with latest traces first, auto-selection of most recent
2. **Timeline View**: Task execution timeline with visual status indicators
3. **Task Details Modal**: Detailed breakdown showing:
   - Task metadata (ID, description, duration, status)
   - Phase execution details (SOP resolution, task creation, execution, context updates)
   - Expandable JSON data for debugging
   - Keyboard navigation (ESC to close)

### **API Endpoints**
- `GET /health` - Health check
- `GET /traces` - List all available traces  
- `GET /traces/latest` - Get most recent trace ID
- `GET /traces/{id}` - Get specific trace data
- `GET /traces/{id}/stream` - Real-time SSE stream for trace updates
- `GET /` - Serve frontend SPA

### **File Structure**
```
visualization/
├── server/           # FastAPI backend
├── frontend/         # Modular JavaScript frontend
├── tests/            # Comprehensive test suite
└── README.md         # This file
```

---

## Development Roadmap (Phases 7-10)

The following phases focus on enhanced phase information display to help users understand execution flow and diagnose issues.

### Phase 7: Enhanced SOP Resolution Phase Display
**Goal**: Show detailed SOP document selection process for debugging

**SOP Resolution Phase Information Display** (when collapsed):
- Show selected SOP document name and description
- Display confidence indicator if multiple candidates existed
- Color-code by selection method (exact match, fuzzy match, fallback)

**SOP Resolution Phase Information Display** (when expanded):
- **Candidate Documents Section**:
  - List all candidate SOP documents considered
  - Show match score/confidence for each candidate
  - Highlight why each was selected or rejected
- **LLM Validation Section** (if used):
  - Display the validation prompt sent to LLM
  - Show LLM's response and reasoning  
  - Highlight the final selected document
- **Selected Document Details**:
  - Full document content and parameters
  - Input/output JSON path mappings
  - Tool configuration and parameters

**Implementation**:
- Extend `task-details.js` component with SOP resolution viewer
- Add expandable sections for candidate analysis
- Create visual diff/comparison for candidate documents
- Format LLM prompts and responses in readable format

**User Benefit**: Users can understand why specific SOPs were chosen and debug SOP selection issues

---

### Phase 8: Enhanced Task Execution Phase Display
**Goal**: Show detailed tool execution and output information

**Task Execution Phase Information Display** (when collapsed):
- Show tool type (LLM, CLI, User Communication) with icon
- Display execution duration and status
- Preview first line of output or error message

**Task Execution Phase Information Display** (when expanded):
- **Input Resolution Section**:
  - Show input field mappings and resolved values
  - Display context extraction process
  - Highlight any missing or invalid inputs
- **Tool Execution Section**:
  - For LLM tools: Show prompt, model info, token usage, response
  - For CLI tools: Show command, working directory, stdout/stderr
  - For User Communication: Show message sent and user response
- **Output Processing Section**:
  - Display raw tool output
  - Show JSON path extraction process if used
  - Preview how output was stored in context
  - Highlight any output parsing errors

**Implementation**:
- Create specialized viewers for each tool type in `task-details.js`
- Add syntax highlighting for code outputs and JSON
- Implement collapsible sections for large outputs  
- Add copy-to-clipboard functionality for debugging

**User Benefit**: Users can debug tool execution failures and understand data flow

---

### Phase 9: Enhanced Task Creation Phase Display
**Goal**: Show task construction and input mapping details

**Task Creation Phase Information Display** (when collapsed):
- Show task description and assigned SOP document
- Display input mapping summary (X inputs resolved)
- Indicate any input resolution warnings or errors

**Task Creation Phase Information Display** (when expanded):
- **SOP Document Configuration**:
  - Display the loaded SOP document structure
  - Show tool parameters and configuration
  - Highlight custom parameter overrides
- **Input Field Resolution**:
  - List all required input fields from SOP
  - Show JSON path resolution for each field
  - Display resolved values with type information
  - Highlight failed or missing input resolutions
- **Output Path Generation**:
  - Show generated output JSON paths
  - Display path prefix logic and collision avoidance
  - Preview where outputs will be stored in context

**Implementation**:
- Add input field mapping visualizer to `task-details.js`
- Create JSON path resolution tracer
- Add validation indicators for input/output paths
- Format complex JSON paths in human-readable way

**User Benefit**: Users can debug task creation failures and understand data binding

---

### Phase 10: Enhanced Context Updates & System Performance
**Goal**: Show context evolution and optimize for long-running traces

**Context Update Phase Information Display** (when collapsed):
- Show number of context keys updated/removed
- Display context size change (+X KB)
- Indicate any context cleanup operations

**Context Update Phase Information Display** (when expanded):
- **Context Changes Visualization**:
  - Side-by-side diff of context before/after
  - Highlight added, modified, and removed keys
  - Show data type changes and value transformations
- **Memory Management**:
  - Display temporary key cleanup operations
  - Show context size optimization steps
  - Highlight any data serialization issues

**Performance Enhancements**:
- Implement virtual scrolling for timeline (handle thousands of tasks)
- Add timeline windowing with "jump to latest" button
- Implement lazy loading for task details (load on click)
- Add search and filtering capabilities:
  - Filter by phase status (failed, completed, in-progress)
  - Search by task description or error messages
  - Filter by execution duration (slow tasks)
  - Filter by specific tools or SOP documents

**Implementation**:
- Add context diff viewer using diff algorithms
- Implement virtual scrolling in `timeline.js` 
- Add search/filter controls to main interface
- Optimize data loading and caching strategies
- Add performance metrics dashboard

**User Benefit**: Handle production-scale traces with hundreds of tasks while providing powerful debugging capabilities

---

## Implementation Guidelines

### Data Structure Understanding
Each trace contains task executions with these key phases:
1. **sop_resolution**: Document selection with candidates and LLM validation
2. **task_creation**: Task construction with input mapping
3. **task_execution**: Tool execution with detailed I/O
4. **context_update**: Context modifications and cleanup
5. **new_task_generation**: Follow-up task creation

### User-Centered Design Principles
When designing phase information displays, consider:
- **Collapsed View**: Show only essential info users need to quickly assess status
- **Expanded View**: Provide comprehensive debugging information
- **Error-First Design**: Highlight failures and issues prominently  
- **Data Flow Visualization**: Help users understand how data flows between phases
- **Copy-Paste Friendly**: Make debugging info easy to extract and share

### Technical Implementation Notes
- Keep frontend modular with feature-specific components
- Use progressive enhancement (basic functionality works, advanced features enhance)
- Implement efficient data structures for large traces
- Add comprehensive error handling and user feedback
- Follow existing test patterns for new features

### Migration Strategy
- Phase 6: Foundational real-time infrastructure
- Phases 7-9: Enhanced phase displays (can be developed in parallel)  
- Phase 10: Performance optimization and system scaling

This roadmap transforms the visualization from a static trace viewer into a powerful real-time debugging and monitoring tool for doc flow execution.
