import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import AuthMiddleware
from config import settings
from rag_mcp_server import mcp as rag_mcp_server

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, specify your actual origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# MCP well-known endpoints (RFC 9728)
# VS Code tries both path variants depending on the MCP endpoint URL
@app.get("/.well-known/oauth-protected-resource/mcp")
@app.get("/.well-known/oauth-protected-resource/mcp/")
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.1 Protected Resource Metadata endpoint for MCP client discovery.
    Required by the MCP specification for authorization server discovery.
    """
    response = json.loads(settings.METADATA_JSON_RESPONSE)
    return response

# Create and mount the MCP server with authentication
mcp_app = rag_mcp_server.http_app()
app.router.lifespan_context = mcp_app.lifespan
app.add_middleware(AuthMiddleware)
app.mount("/", mcp_app)

def main():
    """Main entry point for the MCP server"""
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="debug")

if __name__ == "__main__":
    main()
