# Flight Simulator MCP Server

An enhanced Model Context Protocol (MCP) server for comprehensive airline booking operations, built with FastMCP 2.0 and Python.

## Features

### 🛫 Core Booking Tools (17 total)
- **Flight Search & Booking**: Multi-criteria search, booking creation, modifications
- **Check-in & Services**: Online check-in, seat selection, baggage, meal preferences  
- **Real-time Operations**: Flight tracking, price alerts, disruption handling
- **Loyalty & Groups**: Frequent flyer integration, group bookings, special assistance

### 📊 Information Resources (9 total)
- Airport information with timezones
- Real-time flight status
- Seat maps and availability
- Weather impact data
- Airline policies
- Gate information
- Upgrade availability
- Loyalty benefits

### 🤖 AI-Powered Prompts (6 total)
- Intelligent flight search assistance
- Complete booking workflow guidance
- Multi-city trip planning
- Disruption management
- Loyalty optimization
- Accessibility support

## Installation

### Prerequisites
- Python 3.10 or higher
- UV package manager (recommended) or pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd flight-sim-mcp
```

2. Install dependencies using UV (recommended):
```bash
uv pip install -r requirements.txt
```

Or using pip:
```bash
pip install -r requirements.txt
```

3. Copy environment configuration:
```bash
cp .env.example .env
```

4. Configure your `.env` file with appropriate values.

## Usage

### Running the Server

Start the MCP server:
```bash
python src/server.py
```

The server will start in stdio mode by default, suitable for integration with Claude Desktop or other MCP clients.

### Integration with Claude Desktop

1. Open your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the flight simulator server:
```json
{
  "mcpServers": {
    "flight-simulator": {
      "command": "python",
      "args": ["/path/to/flight-sim-mcp/src/server.py"],
      "env": {}
    }
  }
}
```

3. Restart Claude Desktop

### Example Interactions

**Flight Search:**
```
"Find me a flight from San Francisco to New York next Friday"
```

**Group Booking:**
```
"I need to book flights for 8 people from SFO to JFK on March 15th"
```

**Check-in:**
```
"Check me in for booking BK12345ABC"
```

**Flight Tracking:**
```
"Track flight UA123"
```

**Loyalty Optimization:**
```
"How can I maximize my miles on upcoming trips?"
```

## Available Tools

### Flight Search & Booking
- `search_flights` - Search with multiple criteria
- `get_flight_details` - Detailed flight information
- `create_booking` - Book flights
- `get_booking` - Retrieve booking details
- `cancel_booking` - Cancel with refund calculation
- `modify_booking` - Change flights or dates

### Check-in & Services  
- `check_in` - Online check-in with boarding passes
- `select_seats` - Choose specific seats
- `add_baggage` - Add checked bags
- `add_services` - Meals, WiFi, priority boarding
- `travel_insurance` - Trip protection options
- `special_assistance` - Accessibility services

### Real-time & Loyalty
- `track_flight` - Live flight status
- `price_alert` - Monitor price changes
- `loyalty_account` - Link frequent flyer accounts
- `group_booking` - 5+ passenger bookings
- `upgrade_seat` - Request upgrades

## Testing

### Using MCP Inspector

1. Install MCP Inspector:
```bash
npm install -g @modelcontextprotocol/inspector
```

2. Run the inspector:
```bash
npx mcp-inspector python src/server.py
```

3. Access the web UI at `http://localhost:5173`

### Running Unit Tests

```bash
pytest tests/
```

## Development

### Project Structure
```
flight-sim-mcp/
├── src/
│   ├── server.py           # Main MCP server
│   ├── tools/             # Tool implementations
│   ├── resources/         # Resource endpoints
│   ├── models/           # Pydantic data models
│   ├── data/             # Mock database
│   └── prompts/          # AI prompt templates
├── tests/                # Test files
├── pyproject.toml       # Project configuration
└── README.md           # This file
```

### Adding New Tools

1. Create a new file in `src/tools/`
2. Import the MCP instance: `from ..server import mcp`
3. Define tools using the `@mcp.tool()` decorator
4. Import the module in `server.py`

### Mock Data

The server uses a mock database that generates realistic flight data for demonstrations. In production, this would connect to real airline APIs.

## Security Considerations

- API tokens should be stored in environment variables
- Payment tokens are mocked - implement real payment integration for production
- Personal data handling follows privacy best practices
- Rate limiting is recommended for production deployments

## Deployment

### Local Development
The default stdio transport is perfect for local development and testing with Claude Desktop.

### Remote Deployment
For remote access, configure SSE transport:
```python
# In server.py or via environment variables
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT=8080
```

Deploy options:
- Docker container (Dockerfile included)
- Railway/Render (one-click deploy)
- AWS Lambda (serverless)
- Any Python-capable hosting platform

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review MCP protocol specs at modelcontextprotocol.io