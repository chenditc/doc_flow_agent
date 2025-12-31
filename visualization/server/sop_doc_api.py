"""
SOP Document Management API module for the visualization server.
Provides CRUD operations and search for SOP documents.
"""

import sys
import os
import re
import hashlib
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Header
from datetime import datetime

# Add the parent directory to the path to import sop_document
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sop_document import SOPDocumentLoader, SOPDocument
import yaml

logger = logging.getLogger(__name__)

# Directory configuration
SOP_DOCS_DIR = PROJECT_ROOT / "sop_docs"

# Cache for directory tree
_TREE_CACHE: Dict[str, Any] = {
    "data": None,
    "signature": None,
    "timestamp": None
}

# Valid tool IDs (extracted from existing docs and tools)
VALID_TOOL_IDS = {
    "LLM",
    "PYTHON_EXECUTOR", 
    "CLI",
    "USER",
    "WEB_USER_COMMUNICATE",
    "WEB_RESULT_DELIVERY",
    "TEMPLATE"
}

# Pydantic models for request/response

class TreeNode(BaseModel):
    """Directory tree node"""
    name: str
    path: str
    type: str  # "dir" or "file"
    doc: bool = False
    children: Optional[List['TreeNode']] = None

# Enable forward references
TreeNode.model_rebuild()


class SopDocMeta(BaseModel):
    """SOP document metadata (YAML front matter)"""
    doc_id: Optional[str] = None
    description: str
    aliases: List[str] = Field(default_factory=list)
    tool: Dict[str, Any]
    input_json_path: Optional[Dict[str, str]] = None
    output_json_path: Optional[str] = None
    input_description: Optional[Dict[str, str]] = None
    output_description: Optional[str] = None
    result_validation_rule: Optional[str] = None

    @field_validator('tool')
    @classmethod
    def validate_tool(cls, v):
        if 'tool_id' not in v:
            raise ValueError("tool must contain 'tool_id' field")
        return v


class SopDocResponse(BaseModel):
    """Full SOP document response"""
    path: str
    raw_filename: str
    meta: SopDocMeta
    sections: Dict[str, str]
    body_markdown: str
    hash: str


class SopDocUpdateRequest(BaseModel):
    """Request to create or update a SOP document"""
    meta: SopDocMeta
    body_markdown: str


class ValidationIssue(BaseModel):
    """Validation issue for a SOP document"""
    field: str
    severity: str  # "error" or "warning"
    message: str


class ValidationResponse(BaseModel):
    """Validation result for a SOP document"""
    valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)


class SearchMatch(BaseModel):
    """Single search match in a file"""
    line: int
    preview: str
    kind: str  # "yaml" or "body"


class SearchResult(BaseModel):
    """Search result for a single document"""
    path: str
    matches: List[SearchMatch]
    score: int


class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    results: List[SearchResult]
    total: int


class SopDocMetaSummary(BaseModel):
    """Lightweight metadata summary for building client-side indices"""
    path: str  # path without .md extension
    raw_filename: str  # filename with .md extension
    doc_id: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)


class RawSopDocResponse(BaseModel):
    """Raw SOP document content (entire file)"""
    path: str
    raw_filename: str
    content: str


class CopyRequest(BaseModel):
    """Request to copy a SOP document"""
    source_path: str
    target_path: str
    override_doc_id: bool = True


# Helper functions

def sanitize_path_component(path: str) -> str:
    """Sanitize a path to prevent traversal attacks"""
    # Remove any leading/trailing whitespace
    path = path.strip()
    
    # Remove leading/trailing slashes
    path = path.strip('/')
    
    # Split into components and validate each
    components = path.split('/')
    clean_components = []
    
    for component in components:
        # Reject empty components
        if not component:
            continue
        
        # Reject parent directory references
        if component in ('.', '..'):
            raise ValueError(f"Invalid path component: {component}")
        
        # Reject components starting with dot (hidden files)
        if component.startswith('.'):
            raise ValueError(f"Hidden files not allowed: {component}")
        
        # Allow only safe characters: alphanumeric, underscore, hyphen
        # For the last component (filename), also allow .md extension
        if not re.match(r'^[A-Za-z0-9_-]+(?:\.md)?$', component):
            raise ValueError(f"Invalid characters in path component: {component}")
        
        clean_components.append(component)
    
    return '/'.join(clean_components)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_doc_file_path(doc_path: str) -> Path:
    """Get the full file path for a document path"""
    # Sanitize the path
    clean_path = sanitize_path_component(doc_path)
    
    # Ensure .md extension
    if not clean_path.endswith('.md'):
        clean_path += '.md'
    
    # Build full path
    full_path = SOP_DOCS_DIR / clean_path
    
    # Verify it's within sop_docs directory (security check)
    try:
        full_path.resolve().relative_to(SOP_DOCS_DIR.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {doc_path}")
    
    return full_path


def build_directory_tree() -> List[TreeNode]:
    """Build directory tree structure recursively"""
    
    def scan_directory(directory: Path, relative_base: Path) -> List[TreeNode]:
        """Recursively scan directory"""
        nodes = []
        
        if not directory.exists():
            return nodes
        
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            logger.warning(f"Permission denied reading directory: {directory}")
            return nodes
        
        for item in items:
            # Skip hidden files and __pycache__
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            
            try:
                rel_path = item.relative_to(relative_base)
                rel_path_str = str(rel_path)
                
                if item.is_dir():
                    children = scan_directory(item, relative_base)
                    nodes.append(TreeNode(
                        name=item.name,
                        path=rel_path_str,
                        type="dir",
                        doc=False,
                        children=children if children else None
                    ))
                elif item.is_file() and item.suffix == '.md':
                    # Remove .md extension from path for display
                    display_path = rel_path_str[:-3] if rel_path_str.endswith('.md') else rel_path_str
                    nodes.append(TreeNode(
                        name=item.name,
                        path=display_path,
                        type="file",
                        doc=True
                    ))
            except OSError as e:
                logger.error(f"Error processing {item}: {e}")
                continue
        
        return nodes
    
    return scan_directory(SOP_DOCS_DIR, SOP_DOCS_DIR)


def get_tree_signature() -> str:
    """Get a signature of the directory tree for cache invalidation"""
    signature_parts = []
    
    for root, dirs, files in os.walk(SOP_DOCS_DIR):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in sorted(files):
            if file.endswith('.md') and not file.startswith('.'):
                file_path = Path(root) / file
                try:
                    stat = file_path.stat()
                    signature_parts.append(f"{file_path}:{stat.st_mtime}:{stat.st_size}")
                except OSError:
                    pass
    
    return hashlib.md5(''.join(signature_parts).encode()).hexdigest()


def invalidate_tree_cache():
    """Invalidate the directory tree cache"""
    global _TREE_CACHE
    _TREE_CACHE = {
        "data": None,
        "signature": None,
        "timestamp": None
    }


def load_sop_document_full(doc_path: str) -> SopDocResponse:
    """Load a SOP document with full details"""
    file_path = get_doc_file_path(doc_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {doc_path}")
    
    # Remove .md extension from doc_path for loader
    loader_path = doc_path[:-3] if doc_path.endswith('.md') else doc_path
    
    # Load using SOPDocumentLoader
    loader = SOPDocumentLoader(str(SOP_DOCS_DIR))
    sop_doc = loader.load_sop_document(loader_path)
    
    # Compute hash
    file_hash = compute_file_hash(file_path)
    
    # Build response
    return SopDocResponse(
        path=loader_path,
        raw_filename=file_path.name,
        meta=SopDocMeta(
            doc_id=sop_doc.doc_id,
            description=sop_doc.description,
            aliases=sop_doc.aliases,
            tool=sop_doc.tool,
            input_json_path=sop_doc.input_json_path,
            output_json_path=sop_doc.output_json_path,
            input_description=sop_doc.input_description,
            output_description=sop_doc.output_description,
            result_validation_rule=sop_doc.result_validation_rule
        ),
        sections=sop_doc.parameters,
        body_markdown=sop_doc.body,
        hash=file_hash
    )


def validate_sop_document(meta: SopDocMeta, body_markdown: str) -> ValidationResponse:
    """Validate a SOP document structure"""
    issues = []
    warnings = []
    
    # Check tool_id
    tool_id = meta.tool.get('tool_id')
    if not tool_id:
        issues.append(ValidationIssue(
            field="tool.tool_id",
            severity="error",
            message="tool_id is required"
        ))
    elif tool_id not in VALID_TOOL_IDS:
        issues.append(ValidationIssue(
            field="tool.tool_id",
            severity="error",
            message=f"Invalid tool_id '{tool_id}'. Valid options: {', '.join(sorted(VALID_TOOL_IDS))}"
        ))
    
    # Check description
    if not meta.description or not meta.description.strip():
        issues.append(ValidationIssue(
            field="description",
            severity="error",
            message="description is required and cannot be empty"
        ))
    
    # Parse sections from body
    section_pattern = r'^## (.+?)\n'
    sections = re.findall(section_pattern, body_markdown, re.MULTILINE)
    section_set = set(sections)
    
    # Check for duplicate sections
    if len(sections) != len(section_set):
        duplicates = [s for s in section_set if sections.count(s) > 1]
        issues.append(ValidationIssue(
            field="body_markdown",
            severity="error",
            message=f"Duplicate section names found: {', '.join(duplicates)}"
        ))
    
    # Check tool parameters references
    if 'parameters' in meta.tool:
        params = meta.tool['parameters']
        if isinstance(params, dict):
            for key, value in params.items():
                if isinstance(value, str) and value.startswith('{parameters.') and value.endswith('}'):
                    # Extract section name
                    section_ref = value[1:-1]  # Remove { }
                    if section_ref not in sections:
                        issues.append(ValidationIssue(
                            field=f"tool.parameters.{key}",
                            severity="error",
                            message=f"Referenced section '{section_ref}' not found in document body"
                        ))
    
    # Check JSON path format
    if meta.input_json_path:
        for key, path in meta.input_json_path.items():
            if not path.startswith('$.'):
                warnings.append(ValidationIssue(
                    field=f"input_json_path.{key}",
                    severity="warning",
                    message=f"JSON path should start with '$.' but got: {path}"
                ))
    
    if meta.output_json_path and not meta.output_json_path.startswith('$.'):
        warnings.append(ValidationIssue(
            field="output_json_path",
            severity="warning",
            message=f"JSON path should start with '$.' but got: {meta.output_json_path}"
        ))
    
    # Check aliases type
    if meta.aliases and not isinstance(meta.aliases, list):
        issues.append(ValidationIssue(
            field="aliases",
            severity="error",
            message="aliases must be a list"
        ))
    
    valid = len(issues) == 0
    
    return ValidationResponse(
        valid=valid,
        issues=issues,
        warnings=warnings
    )


def reconstruct_yaml_frontmatter(meta: SopDocMeta) -> str:
    """Reconstruct YAML front matter from metadata with canonical field order"""
    # Build ordered dictionary
    yaml_dict = {}
    
    # Add fields in canonical order
    if meta.doc_id:
        yaml_dict['doc_id'] = meta.doc_id
    
    yaml_dict['description'] = meta.description
    
    if meta.aliases:
        yaml_dict['aliases'] = meta.aliases
    
    yaml_dict['tool'] = meta.tool
    
    if meta.input_json_path:
        yaml_dict['input_json_path'] = meta.input_json_path
    
    if meta.output_json_path:
        yaml_dict['output_json_path'] = meta.output_json_path
    
    if meta.input_description:
        yaml_dict['input_description'] = meta.input_description
    
    if meta.output_description:
        yaml_dict['output_description'] = meta.output_description
    
    if meta.result_validation_rule:
        yaml_dict['result_validation_rule'] = meta.result_validation_rule
    
    # Convert to YAML
    yaml_content = yaml.safe_dump(
        yaml_dict,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False
    )
    
    return f"---\n{yaml_content}---"


def write_sop_document(file_path: Path, meta: SopDocMeta, body_markdown: str):
    """Write SOP document to file atomically"""
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Reconstruct YAML front matter
    yaml_frontmatter = reconstruct_yaml_frontmatter(meta)
    
    # Build full content
    full_content = f"{yaml_frontmatter}\n{body_markdown}"
    
    # Atomic write: write to temp file then rename
    temp_path = file_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # Rename (atomic on POSIX systems)
        temp_path.replace(file_path)
        
        logger.info(f"Successfully wrote document: {file_path}")
    except (IOError, OSError) as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise e


def search_documents_ripgrep(query: str) -> List[SearchResult]:
    """Search documents using ripgrep"""
    try:
        # Run ripgrep with JSON output
        result = subprocess.run(
            ['rg', '--json', '-i', '--', query, str(SOP_DOCS_DIR)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Parse ripgrep JSON output
        results_by_file = {}
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            try:
                data = eval(line)  # ripgrep JSON is actually Python dict format
                
                if data.get('type') == 'match':
                    file_path = data['data']['path']['text']
                    line_number = data['data']['line_number']
                    line_text = data['data']['lines']['text'].strip()
                    
                    # Convert to relative path
                    rel_path = Path(file_path).relative_to(SOP_DOCS_DIR)
                    rel_path_str = str(rel_path)
                    
                    # Remove .md extension
                    if rel_path_str.endswith('.md'):
                        rel_path_str = rel_path_str[:-3]
                    
                    if rel_path_str not in results_by_file:
                        results_by_file[rel_path_str] = []
                    
                    # Determine match kind (rough heuristic)
                    kind = "body"
                    if line_number <= 20:  # Assume YAML is in first 20 lines
                        kind = "yaml"
                    
                    results_by_file[rel_path_str].append(SearchMatch(
                        line=line_number,
                        preview=line_text[:200],  # Limit preview length
                        kind=kind
                    ))
            except (SyntaxError, KeyError, IndexError) as e:
                logger.debug(f"Error parsing ripgrep line: {e}")
                continue
        
        # Convert to SearchResult objects
        search_results = []
        query_lower = query.lower()
        for path, matches in results_by_file.items():
            # Check if query matches the path itself
            if query_lower in path.lower():
                # Add a special match for path
                path_match = SearchMatch(
                    line=0,
                    preview=f"Path match: {path}",
                    kind="path"
                )
                matches = [path_match] + matches
            
            # Limit matches per file
            matches = matches[:10]
            search_results.append(SearchResult(
                path=path,
                matches=matches,
                score=len(matches)
            ))
        
        # Sort by score (descending)
        search_results.sort(key=lambda x: x.score, reverse=True)
        
        return search_results
    
    except FileNotFoundError:
        # ripgrep not found, fall back to Python search
        logger.warning("ripgrep not found, falling back to Python search")
        return search_documents_python(query)
    except subprocess.TimeoutExpired:
        logger.warning("ripgrep search timed out, falling back to Python search")
        return search_documents_python(query)
    except Exception as e:
        logger.error(f"An unexpected error occurred with ripgrep: {e}")
        return search_documents_python(query)


def search_documents_python(query: str) -> List[SearchResult]:
    """Search documents using Python (fallback)"""
    query_lower = query.lower()
    results_by_file = {}
    
    for root, dirs, files in os.walk(SOP_DOCS_DIR):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if not file.endswith('.md') or file.startswith('.'):
                continue
            
            file_path = Path(root) / file
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Get relative path
                rel_path = file_path.relative_to(SOP_DOCS_DIR)
                rel_path_str = str(rel_path)
                
                # Remove .md extension
                if rel_path_str.endswith('.md'):
                    rel_path_str = rel_path_str[:-3]
                
                matches = []
                in_yaml = False
                yaml_ended = False
                
                for i, line in enumerate(lines, 1):
                    if line.strip() == '---':
                        if not in_yaml and i == 1:
                            in_yaml = True
                        elif in_yaml:
                            in_yaml = False
                            yaml_ended = True
                    
                    if query_lower in line.lower():
                        kind = "yaml" if (in_yaml or not yaml_ended) else "body"
                        matches.append(SearchMatch(
                            line=i,
                            preview=line.strip()[:200],
                            kind=kind
                        ))
                        
                        # Limit matches per file
                        if len(matches) >= 10:
                            break
                
                if matches:
                    results_by_file[rel_path_str] = matches
            
            except (IOError, OSError) as e:
                logger.debug(f"Error searching file {file_path}: {e}")
                continue
    
    # Also check for path matches
    for root, dirs, files in os.walk(SOP_DOCS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if not file.endswith('.md') or file.startswith('.'):
                continue
            
            file_path = Path(root) / file
            rel_path = file_path.relative_to(SOP_DOCS_DIR)
            rel_path_str = str(rel_path)
            
            if rel_path_str.endswith('.md'):
                rel_path_str = rel_path_str[:-3]
            
            # Check if query matches the path
            if query_lower in rel_path_str.lower():
                if rel_path_str not in results_by_file:
                    results_by_file[rel_path_str] = []
                
                # Add path match at the beginning
                path_match = SearchMatch(
                    line=0,
                    preview=f"Path match: {rel_path_str}",
                    kind="path"
                )
                results_by_file[rel_path_str].insert(0, path_match)
    
    # Convert to SearchResult objects
    search_results = []
    for path, matches in results_by_file.items():
        search_results.append(SearchResult(
            path=path,
            matches=matches,
            score=len(matches)
        ))
    
    # Sort by score (descending)
    search_results.sort(key=lambda x: x.score, reverse=True)
    
    return search_results


# Create router
router = APIRouter(prefix="/api/sop-docs", tags=["sop-docs"])


@router.get("/tree", response_model=List[TreeNode])
async def get_tree(refresh: bool = False):
    """
    Get the directory tree of SOP documents.
    
    Args:
        refresh: Force refresh the cache
    
    Returns:
        List of tree nodes representing the directory structure
    """
    global _TREE_CACHE
    
    try:
        # Check cache
        current_signature = get_tree_signature()
        
        if not refresh and _TREE_CACHE["data"] is not None:
            if _TREE_CACHE["signature"] == current_signature:
                logger.info("Returning cached tree")
                return _TREE_CACHE["data"]
        
        # Build tree
        logger.info("Building directory tree")
        tree = build_directory_tree()
        
        # Update cache
        _TREE_CACHE = {
            "data": tree,
            "signature": current_signature,
            "timestamp": datetime.now()
        }
        
        return tree
    
    except OSError as e:
        logger.error(f"Error building tree: {e}")
        raise HTTPException(status_code=500, detail=f"Error building directory tree: {str(e)}")


@router.get("/doc/{doc_path:path}", response_model=SopDocResponse)
async def get_document(doc_path: str):
    """
    Get a specific SOP document by path.
    
    Args:
        doc_path: Path to the document (without .md extension)
    
    Returns:
        Full document with metadata, sections, and content
    """
    try:
        return load_sop_document_full(doc_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (IOError, OSError) as e:
        logger.error(f"Error loading document {doc_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading document: {str(e)}")


@router.post("/validate", response_model=ValidationResponse)
async def validate_document(request: SopDocUpdateRequest):
    """
    Validate a SOP document without saving.
    
    Args:
        request: Document metadata and body
    
    Returns:
        Validation result with issues and warnings
    """
    try:
        return validate_sop_document(request.meta, request.body_markdown)
    except Exception as e:
        logger.error(f"Unexpected error validating document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during validation.")


@router.get("/meta/all", response_model=List[SopDocMetaSummary])
async def list_all_metadata():
    """Return lightweight metadata (doc_id, aliases, description, path, filename) for all SOP docs.

    This is optimized for frontend features like reference highlighting without loading full bodies.
    """
    summaries: List[SopDocMetaSummary] = []
    if not SOP_DOCS_DIR.exists():
        return summaries

    loader = SOPDocumentLoader(str(SOP_DOCS_DIR))

    # Recursively gather doc_ids (paths without .md) similar to loader usage elsewhere
    doc_ids: List[str] = []
    for root, dirs, files in os.walk(SOP_DOCS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.startswith('.') or not file.endswith('.md'):
                continue
            file_path = Path(root) / file
            rel_path = file_path.relative_to(SOP_DOCS_DIR)
            rel_path_no_ext = str(rel_path)[:-3]
            doc_ids.append(rel_path_no_ext)

    for doc_id in doc_ids:
        try:
            sop_doc = loader.load_sop_document(doc_id)
            # raw filename derived from last component
            raw_filename = f"{Path(doc_id).name}.md"
            summaries.append(SopDocMetaSummary(
                path=doc_id,
                raw_filename=raw_filename,
                doc_id=sop_doc.doc_id,
                description=sop_doc.description,
                aliases=sop_doc.aliases or []
            ))
        except Exception as e:
            logger.warning(f"Failed to load SOP doc {doc_id}: {e}")
            continue

    return summaries


@router.get("/raw/{doc_path:path}", response_model=RawSopDocResponse)
async def get_raw_document(doc_path: str):
    """Return full raw content of a SOP document, including YAML front matter and body."""
    try:
        file_path = get_doc_file_path(doc_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        rel = doc_path[:-3] if doc_path.endswith('.md') else doc_path
        return RawSopDocResponse(path=rel, raw_filename=file_path.name, content=content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (IOError, OSError) as e:
        logger.error(f"Error reading raw document {doc_path}: {e}")
        raise HTTPException(status_code=500, detail="Error reading document")


@router.post("/create", response_model=SopDocResponse)
async def create_document(doc_path: str, request: SopDocUpdateRequest):
    """
    Create a new SOP document.
    
    Args:
        doc_path: Path for the new document (without .md extension)
        request: Document metadata and body
    
    Returns:
        Created document details
    """
    try:
        # Get file path
        file_path = get_doc_file_path(doc_path)
        
        # Check if file already exists
        if file_path.exists():
            raise HTTPException(status_code=409, detail=f"Document already exists: {doc_path}")
        
        # Validate document
        validation = validate_sop_document(request.meta, request.body_markdown)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Document validation failed",
                    "issues": [issue.dict() for issue in validation.issues]
                }
            )
        
        # Write document
        write_sop_document(file_path, request.meta, request.body_markdown)
        
        # Invalidate cache
        invalidate_tree_cache()
        
        # Return created document
        return load_sop_document_full(doc_path)
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (IOError, OSError) as e:
        logger.error(f"Error creating document {doc_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating document: {str(e)}")


@router.put("/doc/{doc_path:path}", response_model=SopDocResponse)
async def update_document(
    doc_path: str,
    request: SopDocUpdateRequest,
    if_match: Optional[str] = Header(None)
):
    """
    Update an existing SOP document.
    
    Args:
        doc_path: Path to the document (without .md extension)
        request: Updated document metadata and body
        if_match: Expected file hash for optimistic locking
    
    Returns:
        Updated document details
    """
    try:
        # Get file path
        file_path = get_doc_file_path(doc_path)
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")
        
        # Check hash if provided (optimistic locking)
        if if_match:
            current_hash = compute_file_hash(file_path)
            if current_hash != if_match:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Document has been modified by another process",
                        "current_hash": current_hash
                    }
                )
        
        # Validate document
        validation = validate_sop_document(request.meta, request.body_markdown)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Document validation failed",
                    "issues": [issue.dict() for issue in validation.issues]
                }
            )
        
        # Write document
        write_sop_document(file_path, request.meta, request.body_markdown)
        
        # Invalidate cache
        invalidate_tree_cache()
        
        # Return updated document
        return load_sop_document_full(doc_path)
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (IOError, OSError) as e:
        logger.error(f"Error updating document {doc_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")


@router.post("/copy", response_model=SopDocResponse)
async def copy_document(request: CopyRequest):
    """
    Copy a SOP document to a new location.
    
    Args:
        request: Source and target paths, and whether to override doc_id
    
    Returns:
        Copied document details
    """
    try:
        # Get file paths
        source_path = get_doc_file_path(request.source_path)
        target_path = get_doc_file_path(request.target_path)
        
        # Check source exists
        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"Source document not found: {request.source_path}")
        
        # Check target doesn't exist
        if target_path.exists():
            raise HTTPException(status_code=409, detail=f"Target document already exists: {request.target_path}")
        
        # Load source document
        source_doc = load_sop_document_full(request.source_path)
        
        # Copy metadata
        new_meta = source_doc.meta.copy()
        
        # Override doc_id if requested
        if request.override_doc_id:
            # Remove .md extension from target path for doc_id
            target_doc_id = request.target_path[:-3] if request.target_path.endswith('.md') else request.target_path
            new_meta.doc_id = target_doc_id
        
        # Write to new location
        write_sop_document(target_path, new_meta, source_doc.body_markdown)
        
        # Invalidate cache
        invalidate_tree_cache()
        
        # Return copied document
        return load_sop_document_full(request.target_path)
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (IOError, OSError) as e:
        logger.error(f"Error copying document: {e}")
        raise HTTPException(status_code=500, detail=f"Error copying document: {str(e)}")


@router.get("/search", response_model=SearchResponse)
async def search_documents(q: str):
    """
    Search SOP documents for a keyword.
    
    Args:
        q: Search query
    
    Returns:
        Search results with matches
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        # Search using ripgrep (with Python fallback)
        results = search_documents_ripgrep(q.strip())
        
        return SearchResponse(
            query=q,
            results=results,
            total=len(results)
        )
    except Exception as e:
        logger.error(f"Unexpected error during search for '{q}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during search.")


@router.delete("/doc/{doc_path:path}")
async def delete_document(doc_path: str):
    """
    Delete a SOP document.
    
    Args:
        doc_path: Path to the document (without .md extension)
    
    Returns:
        Success message
    """
    try:
        # Get file path
        file_path = get_doc_file_path(doc_path)
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")
        
        # Delete file
        file_path.unlink()
        
        # Invalidate cache
        invalidate_tree_cache()
        
        logger.info(f"Deleted document: {doc_path}")
        
        return {"success": True, "message": f"Document deleted: {doc_path}"}
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (IOError, OSError) as e:
        logger.error(f"Error deleting document {doc_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
