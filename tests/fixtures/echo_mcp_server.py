"""A tiny MCP server for the tests: one harmless tool, one that looks like it sends mail."""
from mcp.server.fastmcp import FastMCP

app = FastMCP("echo")


@app.tool()
def echo(text: str) -> str:
    """Repeat the text back."""
    return f"echo: {text}"


@app.tool()
def send_email(to: str) -> str:
    """Pretend to send an email."""
    return f"sent to {to}"


if __name__ == "__main__":
    app.run()
