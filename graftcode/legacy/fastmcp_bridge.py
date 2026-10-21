#!/usr/bin/env python3
"""
LEGACY, superseded by the Graftcode Gateway's built-in MCP endpoint.

This hand-written FastMCP bridge was the first way this project exposed the
receiver to Claude. It is kept only as a "before" comparison. The Gateway now
serves the same methods as MCP tools at http://localhost:8081/mcp with no extra
process. See the README ("Use it from Claude or Cursor").
"""

import sys
import json
from dataclasses import asdict
from pathlib import Path

# Add receiver module to path (relative to this file, so the repo is portable)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "receiver"))
from article_receiver.service import ArticlePipelineService

try:
    from fastmcp import FastMCP
except ImportError:
    sys.exit("fastmcp is required for the MCP bridge: pip install fastmcp")

mcp = FastMCP("wayzyy-graftcode-pipeline")


def _dump(result) -> str:
    """Receiver methods already return JSON strings; pass them through."""
    return result if isinstance(result, str) else json.dumps(asdict(result))

service = ArticlePipelineService()

@mcp.tool()
def get_pipeline_status() -> str:
    """Returns real-time pipeline status, model providers, and queue counts."""
    return _dump(service.get_pipeline_status())

@mcp.tool()
def list_pending_topics() -> str:
    """Retrieves pending topics in the review queue with metadata and source counts."""
    return _dump(service.list_pending_topics())

@mcp.tool()
def get_topic_sources(topic: str) -> str:
    """Retrieves verified sources, headlines, and platform URLs for a specific topic."""
    return _dump(service.get_topic_sources(topic))

@mcp.tool()
def write_article(topic: str, skip_research: bool = False, extra_research: str = "") -> str:
    """Executes the full generation pipeline for an article."""
    return _dump(service.write_article(topic, skip_research, extra_research))

@mcp.tool()
def list_drafts() -> str:
    """Lists all generated drafts with file size, modified date, and word count."""
    return _dump(service.list_drafts())

@mcp.tool()
def get_draft(filename: str) -> str:
    """Returns the raw markdown content of a draft."""
    return _dump(service.get_draft(filename))

@mcp.tool()
def run_style_check(filename: str) -> str:
    """Audits a draft against Wayzyy's 40-point brand style guide."""
    return _dump(service.run_style_check(filename))

@mcp.tool()
def save_draft(filename: str, content: str) -> str:
    """Saves updated markdown content back to a draft file."""
    return _dump(service.save_draft(filename, content))

@mcp.tool()
def run_scanner() -> str:
    """Runs the trend scanner and reports the pending-topic count (skipped in demo mode)."""
    return _dump(service.run_scanner())

@mcp.tool()
def suggest_next_article() -> str:
    """Suggests the highest priority topic based on search volume and seasonal relevance."""
    return _dump(service.suggest_next_article())

@mcp.tool()
def push_to_github(filename: str) -> str:
    """Stages publication branch and creates pull request on GitHub."""
    return _dump(service.push_to_github(filename))

if __name__ == "__main__":
    mcp.run()
