# Decision Packet Storage & Analysis Guide

**Question**: Can I perform analysis on decision packet storage content with JSON schema structure in DynamoDB?

**Short Answer**: **Yes, but with some considerations**. The JSON structure is analysis-friendly, but DynamoDB has limitations for complex queries. Multiple analysis strategies are available.

---

## 📊 Current DecisionPacket Schema Structure

The DecisionPacket is a Pydantic model that serializes to JSON:

```python
class DecisionPacket(BaseModel):
    incident_id: str
    event_type: EventType
    what_happened: str
    root_cause: dict[str, Any]  # Contains: classification, confidence, hypothesis
    recommended_actions: list[RecommendedAction]
    actions_allowed: list[dict[str, Any]]
    actions_blocked: list[dict[str, Any]]
    safe_to_autofix: bool
    needs_human: list[dict[str, Any]]
    evidence_refs: list[str]
    created_at: datetime
```

**JSON Structure** (when serialized):
```json
{
  "incident_id": "incident_xxx",
  "event_type": "PIPELINE_FAILURE",
  "what_happened": "Pipeline execution timed out...",
  "root_cause": {
    "classification": "INFRASTRUCTURE_ISSUE",
    "confidence": 0.85,
    "hypothesis": "The pipeline execution exceeded timeout..."
  },
  "recommended_actions": [
    {
      "action_type": "retry_execution",
      "description": "Retry the failed pipeline",
      "parameters": {...}
    }
  ],
  "actions_allowed": [...],
  "actions_blocked": [...],
  "safe_to_autofix": true,
  "needs_human": [],
  "evidence_refs": ["s3://..."],
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## 🔍 Analysis Capabilities by Storage Type

### 1. Local File Storage (Development)

**Storage**: `./evidence/{incident_id}_decision.json`

**Analysis Options**:
- ✅ **Direct JSON parsing** - Read files, parse JSON, analyze with Python
- ✅ **Full schema access** - Can query any field, nested or not
- ✅ **Simple tools** - `jq`, `grep`, Python scripts
- ✅ **No limitations** - Full flexibility

**Example Analysis**:
```python
import json
from pathlib import Path

# Load all decision packets
decisions = []
for file in Path("./evidence").glob("*_decision.json"):
    with open(file) as f:
        decisions.append(json.load(f))

# Analyze by classification
code_regressions = [d for d in decisions 
                    if d["root_cause"]["classification"] == "CODE_REGRESSION"]

# Analyze by tier
prod_incidents = [d for d in decisions 
                  if d.get("tier") == "prod"]
```

**Pros**: 
- Full flexibility
- Easy to analyze
- No query limitations

**Cons**:
- Not scalable for large datasets
- Manual file management

---

### 2. DynamoDB Storage (Production)

**Storage**: DynamoDB table `{environment}-ops-autopilot-incidents`

**Current Table Structure**:
```terraform
resource "aws_dynamodb_table" "incidents" {
  name           = "${var.environment}-ops-autopilot-incidents"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "incident_id"  # Partition key
  
  attribute {
    name = "incident_id"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
```

**DecisionPacket Storage Format** (in DynamoDB):
```json
{
  "incident_id": "incident_xxx",  // Partition key
  "decision_packet": {            // JSON document (stored as Map type)
    "incident_id": "...",
    "event_type": "PIPELINE_FAILURE",
    "root_cause": {...},
    ...
  },
  "created_at": "2024-01-15T10:30:00Z",
  "ttl": 1736899200  // For automatic cleanup
}
```

---

## ⚠️ DynamoDB Query Limitations

### What You CAN Query Directly:

1. **Partition Key** (incident_id):
   ```python
   # Get specific incident
   response = table.get_item(Key={"incident_id": "incident_xxx"})
   ```

2. **Top-Level Attributes** (if added as separate attributes):
   ```python
   # If we add GSI on created_at
   response = table.query(
       IndexName="created_at-index",
       KeyConditionExpression="created_at = :date"
   )
   ```

### What You CANNOT Query Directly:

1. **Nested JSON Fields** (without workarounds):
   ```python
   # ❌ This won't work directly
   # Can't query: decision_packet.root_cause.classification
   # Can't query: decision_packet.safe_to_autofix
   ```

2. **Array Fields**:
   ```python
   # ❌ Can't query: decision_packet.actions_allowed[0].action_type
   ```

3. **Complex Filters**:
   ```python
   # ❌ Can't filter by nested conditions easily
   ```

---

## ✅ Analysis Strategies for DynamoDB

### Strategy 1: Flatten Key Fields (Recommended)

**Add top-level attributes for common queries**:

```python
# When storing DecisionPacket in DynamoDB
item = {
    "incident_id": decision.incident_id,  # Partition key
    "created_at": decision.created_at.isoformat(),
    
    # Flatten commonly queried fields
    "event_type": decision.event_type.value,
    "classification": decision.root_cause.get("classification"),
    "confidence": decision.root_cause.get("confidence"),
    "safe_to_autofix": decision.safe_to_autofix,
    "tier": decision.root_cause.get("tier"),  # If available
    
    # Store full DecisionPacket as JSON
    "decision_packet": decision.model_dump(),
    
    "ttl": calculate_ttl()  # For automatic cleanup
}
```

**Add Global Secondary Indexes (GSI)** for common queries:

```terraform
resource "aws_dynamodb_table" "incidents" {
  # ... existing config ...
  
  # GSI for querying by classification
  global_secondary_index {
    name     = "classification-created_at-index"
    hash_key = "classification"
    range_key = "created_at"
  }
  
  # GSI for querying by event type and date
  global_secondary_index {
    name     = "event_type-created_at-index"
    hash_key = "event_type"
    range_key = "created_at"
  }
  
  # GSI for querying by tier
  global_secondary_index {
    name     = "tier-created_at-index"
    hash_key = "tier"
    range_key = "created_at"
  }
}
```

**Analysis Queries**:
```python
# Query by classification
response = table.query(
    IndexName="classification-created_at-index",
    KeyConditionExpression="classification = :cls",
    ExpressionAttributeValues={":cls": "CODE_REGRESSION"}
)

# Query by date range
response = table.query(
    IndexName="event_type-created_at-index",
    KeyConditionExpression="event_type = :type AND created_at BETWEEN :start AND :end",
    ExpressionAttributeValues={
        ":type": "PIPELINE_FAILURE",
        ":start": "2024-01-01T00:00:00Z",
        ":end": "2024-01-31T23:59:59Z"
    }
)
```

**Pros**:
- Fast queries on indexed fields
- Cost-effective (only pay for queries)
- Real-time analysis

**Cons**:
- Need to plan indexes upfront
- Limited to indexed fields
- Still need to scan for complex nested queries

---

### Strategy 2: Export to S3 + Athena (Best for Analytics)

**Use DynamoDB Streams or periodic exports**:

```python
# Export DecisionPackets to S3 (JSON or Parquet)
# Then query with Athena

# Athena table definition
CREATE EXTERNAL TABLE decision_packets (
    incident_id string,
    event_type string,
    classification string,
    confidence double,
    safe_to_autofix boolean,
    created_at timestamp,
    decision_packet struct<...>  # Full nested structure
)
STORED AS PARQUET
LOCATION 's3://ops-autopilot-analytics/decision-packets/'
```

**Analysis Queries** (SQL-like):
```sql
-- Count incidents by classification
SELECT 
    classification,
    COUNT(*) as count
FROM decision_packets
WHERE created_at >= '2024-01-01'
GROUP BY classification;

-- Find incidents that needed human intervention
SELECT 
    incident_id,
    classification,
    created_at
FROM decision_packets
WHERE CARDINALITY(needs_human) > 0;

-- Analyze action success rates
SELECT 
    action_type,
    COUNT(*) as total,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
FROM decision_packets
CROSS JOIN UNNEST(actions_allowed) AS t(action_type, success)
GROUP BY action_type;
```

**Pros**:
- Full SQL query capabilities
- Can query any nested field
- Cost-effective for large datasets
- Standard analytics tools (Tableau, QuickSight, etc.)

**Cons**:
- Not real-time (export delay)
- Additional setup (S3, Athena)
- Slightly more complex architecture

---

### Strategy 3: DynamoDB Streams + Lambda (Real-time Analytics)

**Stream DecisionPackets to analytics pipeline**:

```python
# Lambda function triggered by DynamoDB Streams
def stream_handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            decision_packet = record['dynamodb']['NewImage']
            
            # Send to analytics service
            # - CloudWatch Metrics
            # - Kinesis Data Firehose → S3
            # - Elasticsearch/OpenSearch
            # - Custom analytics database
```

**Pros**:
- Real-time analytics
- Can aggregate metrics immediately
- Flexible destination

**Cons**:
- More complex setup
- Additional costs (Lambda, streams)
- Need to design aggregation logic

---

### Strategy 4: Scan with Filter Expressions (Simple but Limited)

**For ad-hoc analysis**:

```python
# Scan table with filter (expensive, but works)
response = table.scan(
    FilterExpression="contains(decision_packet, :cls)",
    ExpressionAttributeValues={":cls": "CODE_REGRESSION"}
)

# Or use filter on top-level attributes
response = table.scan(
    FilterExpression="classification = :cls AND created_at >= :date",
    ExpressionAttributeValues={
        ":cls": "CODE_REGRESSION",
        ":date": "2024-01-01T00:00:00Z"
    }
)
```

**Pros**:
- Simple to implement
- Works for any field (if flattened)

**Cons**:
- Expensive (scans entire table)
- Slow for large datasets
- Not recommended for production

---

## 📋 Recommended Implementation

### Phase 0 (Current): Local Files
- ✅ Store as JSON files
- ✅ Simple Python scripts for analysis
- ✅ Full flexibility

### Phase 1 (Production): DynamoDB with Flattened Fields + GSI
- ✅ Store DecisionPacket as JSON document
- ✅ Flatten commonly queried fields (classification, event_type, tier, created_at)
- ✅ Add GSI for common query patterns
- ✅ Fast queries on indexed fields

### Phase 2 (Analytics): S3 + Athena
- ✅ Export DecisionPackets to S3 (Parquet format)
- ✅ Create Athena table
- ✅ SQL queries for complex analysis
- ✅ Integration with BI tools

---

## 🎯 Common Analysis Queries & How to Support Them

### 1. "How many CODE_REGRESSION incidents this month?"
**Solution**: GSI on `classification-created_at-index`
```python
table.query(
    IndexName="classification-created_at-index",
    KeyConditionExpression="classification = :cls AND created_at BETWEEN :start AND :end"
)
```

### 2. "What's the success rate of auto-remediation?"
**Solution**: Flatten `safe_to_autofix` + GSI, or use Athena
```sql
SELECT 
    safe_to_autofix,
    COUNT(*) as count
FROM decision_packets
GROUP BY safe_to_autofix
```

### 3. "Which actions are most commonly blocked by policy?"
**Solution**: Export to S3 + Athena, or scan with filter
```sql
SELECT 
    action_type,
    COUNT(*) as blocked_count
FROM decision_packets
CROSS JOIN UNNEST(actions_blocked) AS t(action_type)
GROUP BY action_type
ORDER BY blocked_count DESC
```

### 4. "Show incidents that needed human intervention"
**Solution**: Flatten `needs_human_count` field, or use Athena
```sql
SELECT * FROM decision_packets
WHERE CARDINALITY(needs_human) > 0
```

### 5. "Trend analysis: incidents over time by classification"
**Solution**: Athena with time-series queries
```sql
SELECT 
    DATE_TRUNC('day', created_at) as day,
    classification,
    COUNT(*) as count
FROM decision_packets
WHERE created_at >= '2024-01-01'
GROUP BY day, classification
ORDER BY day
```

---

## ✅ Summary

**Can you perform analysis?** **YES!**

**With JSON structure?** **YES!** - JSON is analysis-friendly

**With DynamoDB?** **YES, with considerations**:
- ✅ Flatten commonly queried fields
- ✅ Add Global Secondary Indexes (GSI)
- ✅ Export to S3 + Athena for complex analytics
- ✅ Use DynamoDB Streams for real-time metrics

**Recommendation**:
1. **Phase 0**: Local JSON files (simple, flexible)
2. **Phase 1**: DynamoDB with flattened fields + GSI (fast queries)
3. **Phase 2**: S3 + Athena (full SQL analytics)

The JSON schema structure is well-suited for analysis - you just need to choose the right storage and query strategy for your use case!
