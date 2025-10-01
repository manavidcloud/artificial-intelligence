# Flight Simulator MCP Server - Test Queries for Claude Desktop

## How to Test in Claude Desktop

1. Open Claude Desktop
2. Make sure the flight-simulator server is running (check the MCP menu)
3. Use these queries to test different functionalities

## 1. Flight Search Tests

### Basic Search
```
Find flights from SFO to JFK for tomorrow
```

### Advanced Search with Options
```
Search for round-trip flights from San Francisco to New York departing June 28, returning July 2, for 2 passengers in business class
```

### Budget Search
```
Show me the cheapest flights from LAX to Chicago under $300
```

### Nonstop Only
```
Find only nonstop flights from SFO to LAX
```

### Airline Preference
```
Search for United Airlines flights from San Francisco to New York next week
```

## 2. Booking Operations

### Create a Booking
```
Book flight UA123 for passenger John Doe, email john.doe@email.com, phone 555-123-4567
```

### Multiple Passengers
```
Book flight AA456 for 2 passengers:
- Jane Smith (jane@email.com, 555-9876)
- Bob Johnson (bob@email.com, 555-5432)
```

### Retrieve Booking
```
Show me booking details for PNR ABC123
```

### Cancel Booking
```
Cancel my booking BK-12345 due to schedule change
```

## 3. Check-in Process

### Basic Check-in
```
Check me in for booking ABC123
```

### Check-in with Seat Selection
```
Check in for booking XYZ789 and select seat 12A
```

## 4. Flight Information

### Flight Details
```
Get details for flight UA789
```

### Seat Map
```
Show me the seat map for flight AA123
```

### Flight Status
```
What's the current status of flight DL456?
```

## 5. Resource Information Queries

### Baggage Policies
```
What are the baggage policies for United Airlines?
```

### Loyalty Programs
```
Tell me about airline loyalty programs
```

### COVID Policies
```
What are the current COVID-19 travel requirements?
```

### General Policies
```
What are the check-in times and boarding procedures?
```

### Airport Information
```
Get information about SFO airport
```

### Travel Tips
```
Give me travel tips for NYC
```

### Weather
```
What's the weather forecast at JFK airport?
```

## 6. Special Services

### Meal Requests
```
Add vegetarian meal request to booking ABC123
```

### Assistance Requests
```
Request wheelchair assistance for booking XYZ789
```

### Extra Baggage
```
Add 2 extra checked bags to my booking
```

### Upgrade Request
```
Request upgrade to business class for booking DEF456
```

## 7. Group Bookings

### Create Group
```
Create a group booking for 8 people from SFO to LAX on July 15
```

### Add to Group
```
Add passenger Sarah Lee (sarah@email.com) to group booking GRP-12345
```

### Remove from Group
```
Remove John Doe from group booking GRP-12345
```

## 8. Real-time Tracking

### Track Flight
```
Track flight UA123 in real-time
```

### Gate Information
```
What gate is flight AA789 departing from?
```

### Airport Status
```
Show me current delays at San Francisco airport
```

## 9. Complex Scenarios

### Family Trip Planning
```
I need to book flights for my family of 4 from San Francisco to Orlando for spring break. We prefer morning flights and need 2 child meals.
```

### Business Travel
```
Find me business class flights from New York to London next Monday, returning Friday. I need lounge access and prefer aisle seats.
```

### Multi-city Journey
```
Plan a trip from SFO to Paris with a 3-day stopover in New York
```

### Disruption Handling
```
My flight UA789 was cancelled. What are my rebooking options?
```

## 10. Error Testing

### Invalid Airport Code
```
Find flights from INVALID to JFK
```

### Past Date
```
Book a flight for yesterday
```

### Invalid Booking Reference
```
Show me booking INVALID123
```

## Expected Behaviors

- The MCP server should respond to natural language queries
- It should use the appropriate tools based on the request
- Resources should provide static information (policies, tips, etc.)
- Tools should handle dynamic operations (search, book, cancel, etc.)
- Error cases should return helpful error messages

## Troubleshooting

If queries aren't working:
1. Check if the flight-simulator server is running in the MCP menu
2. Look at the logs: `~/Library/Logs/Claude/mcp-server-flight-simulator.log`
3. Restart Claude Desktop if needed
4. Make sure the server has all required dependencies installed