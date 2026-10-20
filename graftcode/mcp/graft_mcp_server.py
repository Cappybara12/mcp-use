#!/usr/bin/env python3
"""
Wayzyy Autonomous Content Engine — Graftcode MCP Bridge for Claude Desktop / Cursor
Exposes the Graftcode Receiver methods as standardized MCP tools.
"""

import sys
import json
from pathlib import Path

# Add receiver module to path
sys.path.insert(0, "/Users/akshay/graft/receiver")
from article_receiver.service import ArticlePipelineService

try:
    from fastmcp import FastMCP
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastmcp"])
    from fastmcp import FastMCP

mcp = FastMCP("wayzyy-graftcode-pipeline")
service = ArticlePipelineService()

@mcp.tool()
def get_pipeline_status() -> str:
    """Returns real-time pipeline status, model providers, and queue counts."""
    return service.get_pipeline_status()

@mcp.tool()
def list_pending_topics() -> str:
    """Retrieves pending topics in the review queue with metadata and source counts."""
    return service.list_pending_topics()

@mcp.tool()
def get_topic_sources(topic: str) -> str:
    """Retrieves verified sources, headlines, and platform URLs for a specific topic."""
    return service.get_topic_sources(topic)

@mcp.tool()
def write_article(topic: str, skip_research: bool = False, extra_research: str = "") -> str:
    """Executes the full generation pipeline for an article."""
    return service.write_article(topic, skip_research, extra_research)

@mcp.tool()
def list_drafts() -> str:
    """Lists all generated drafts with file size, modified date, and word count."""
    return service.list_drafts()

@mcp.tool()
def get_draft(filename: str) -> str:
    """Returns the raw markdown content of a draft."""
    return service.get_draft(filename)

@mcp.tool()
def run_style_check(filename: str) -> str:
    """Audits a draft against Wayzyy's 40-point brand style guide."""
    return service.run_style_check(filename)

@mcp.tool()
def suggest_next_article() -> str:
    """Suggests the highest priority topic based on search volume and seasonal relevance."""
    return service.suggest_next_article()

@mcp.tool()
def push_to_github(filename: str) -> str:
    """Stages publication branch and creates pull request on GitHub."""
    return service.push_to_github(filename)

if __name__ == "__main__":
    mcp.run()
