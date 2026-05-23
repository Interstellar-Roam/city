# Route Search Spec

## Requirements

### REQ-1: Multi-field text search
The system SHALL support keyword search across the following route fields: name, description, tags, city, district, POI names, and POI tags.

#### Scenario: Search by city name
- GIVEN routes exist in "杭州"
- WHEN user searches "杭州"
- THEN return all routes whose city field contains "杭州"

#### Scenario: Search by tag keyword
- GIVEN routes tagged with "咖啡"
- WHEN user searches "咖啡"
- THEN return all routes with "咖啡" in their tags

#### Scenario: Search by route name
- GIVEN a route named "北京胡同漫步"
- WHEN user searches "胡同"
- THEN return that route (and others with matching name)

#### Scenario: Fallback to fuzzy regex
- GIVEN no $text index matches for keyword "abc"
- WHEN search is executed
- THEN fall back to case-insensitive $regex search with same priority

### REQ-2: Search suggestions (auto-complete)
The system SHALL provide prefix-based search suggestions for cities, tags, and route names.

#### Scenario: Prefix match for city
- GIVEN routes in "杭州" exist
- WHEN user types "杭" in suggest endpoint
- THEN return {"type": "city", "value": "杭州"} with count

#### Scenario: Prefix match for tag
- GIVEN routes tagged "咖啡" exist
- WHEN user types "咖" in suggest endpoint
- THEN return {"type": "tag", "value": "咖啡"} with count

#### Scenario: Prefix match for route name
- GIVEN route "杭州西湖漫步" exists
- WHEN user types "西湖" in suggest endpoint
- THEN return {"type": "route", "value": "杭州西湖漫步"} with count

### REQ-3: iOS search debounce
The iOS search SHALL debounce user input by 300ms before sending API request.

#### Scenario: Debounce prevents rapid requests
- GIVEN user types 5 characters quickly
- WHEN each keystroke occurs within 300ms
- THEN only one API request is sent (after the last keystroke)
